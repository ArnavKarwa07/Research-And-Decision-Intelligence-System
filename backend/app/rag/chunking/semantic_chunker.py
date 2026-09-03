"""Hierarchical Semantic Chunker supporting parent-child relationships and token counting."""
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from app.rag.parsers.base import ParsedDocument


@dataclass
class ChunkResult:
    """Represents a generated text chunk."""
    chunk_index: int
    content: str
    content_hash: str
    token_count: int
    page_number: int | None = None
    section_heading: str | None = None
    start_offset: int = 0
    end_offset: int = 0
    parent_chunk_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SemanticChunker:
    """Chunker implementing parent-child hierarchical semantic chunking."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        parent_chunk_size: int = 1024,
        encoding_name: str = "cl100k_base",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parent_chunk_size = parent_chunk_size
        self.encoding_name = encoding_name
        self._tokenizer = None

    def _get_tokenizer(self) -> Any:
        if self._tokenizer is None:
            try:
                import tiktoken
                self._tokenizer = tiktoken.get_encoding(self.encoding_name)
            except Exception:
                self._tokenizer = None
        return self._tokenizer

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken with word count fallback."""
        tokenizer = self._get_tokenizer()
        if tokenizer:
            try:
                return len(tokenizer.encode(text))
            except Exception:
                pass
        # Fallback approximation: 1 token ~ 4 chars or 0.75 words
        return max(1, len(text.split()))

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA-256 hash of chunk content for deduplication."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def chunk_document(self, doc: ParsedDocument) -> list[ChunkResult]:
        """Perform parent-child hierarchical chunking on a ParsedDocument.

        Returns list of ChunkResult objects where children reference parent indices.
        """
        all_chunks: list[ChunkResult] = []
        global_chunk_index = 0
        global_char_offset = 0

        sections = doc.sections if doc.sections else []

        for section in sections:
            section_text = section.text.strip()
            if not section_text:
                continue

            sec_tokens = self.count_tokens(section_text)
            
            # If section is small enough to be a parent
            if sec_tokens <= self.parent_chunk_size:
                parent_idx = global_chunk_index
                parent_hash = self.compute_hash(section_text)
                
                parent_chunk = ChunkResult(
                    chunk_index=parent_idx,
                    content=section_text,
                    content_hash=parent_hash,
                    token_count=sec_tokens,
                    page_number=section.page_number,
                    section_heading=section.heading,
                    start_offset=global_char_offset,
                    end_offset=global_char_offset + len(section_text),
                    parent_chunk_index=None,
                    metadata={"is_parent": True, "title": doc.title},
                )
                all_chunks.append(parent_chunk)
                global_chunk_index += 1

                # Now create child sub-chunks from parent text if it exceeds child chunk size
                if sec_tokens > self.chunk_size:
                    children = self._split_into_children(
                        text=section_text,
                        parent_index=parent_idx,
                        start_index=global_chunk_index,
                        base_offset=global_char_offset,
                        page_number=section.page_number,
                        section_heading=section.heading,
                    )
                    all_chunks.extend(children)
                    global_chunk_index += len(children)
            else:
                # Section is large: first split into multiple parent chunks
                parents = self._split_text_by_tokens(
                    text=section_text,
                    max_tokens=self.parent_chunk_size,
                    overlap_tokens=self.chunk_overlap * 2,
                )
                
                for parent_text, p_start, p_end in parents:
                    p_tokens = self.count_tokens(parent_text)
                    parent_idx = global_chunk_index
                    parent_hash = self.compute_hash(parent_text)

                    parent_chunk = ChunkResult(
                        chunk_index=parent_idx,
                        content=parent_text,
                        content_hash=parent_hash,
                        token_count=p_tokens,
                        page_number=section.page_number,
                        section_heading=section.heading,
                        start_offset=global_char_offset + p_start,
                        end_offset=global_char_offset + p_end,
                        parent_chunk_index=None,
                        metadata={"is_parent": True, "title": doc.title},
                    )
                    all_chunks.append(parent_chunk)
                    global_chunk_index += 1

                    # Child sub-chunks
                    children = self._split_into_children(
                        text=parent_text,
                        parent_index=parent_idx,
                        start_index=global_chunk_index,
                        base_offset=global_char_offset + p_start,
                        page_number=section.page_number,
                        section_heading=section.heading,
                    )
                    all_chunks.extend(children)
                    global_chunk_index += len(children)

            global_char_offset += len(section_text) + 2

        return all_chunks

    def _split_into_children(
        self,
        text: str,
        parent_index: int,
        start_index: int,
        base_offset: int,
        page_number: int | None,
        section_heading: str | None,
    ) -> list[ChunkResult]:
        """Split text into child sub-chunks linked to parent_index."""
        children: list[ChunkResult] = []
        child_slices = self._split_text_by_tokens(
            text=text,
            max_tokens=self.chunk_size,
            overlap_tokens=self.chunk_overlap,
        )

        for i, (child_text, c_start, c_end) in enumerate(child_slices):
            c_tokens = self.count_tokens(child_text)
            c_hash = self.compute_hash(child_text)

            child_chunk = ChunkResult(
                chunk_index=start_index + i,
                content=child_text,
                content_hash=c_hash,
                token_count=c_tokens,
                page_number=page_number,
                section_heading=section_heading,
                start_offset=base_offset + c_start,
                end_offset=base_offset + c_end,
                parent_chunk_index=parent_index,
                metadata={"is_parent": False},
            )
            children.append(child_chunk)

        return children

    def _split_text_by_tokens(
        self,
        text: str,
        max_tokens: int,
        overlap_tokens: int,
    ) -> list[tuple[str, int, int]]:
        """Splits text into windows based on token counts.

        Guarantees forward progress on oversized words and calculates exact character offsets.
        Returns list of tuples (substring, start_char_offset, end_char_offset).
        """
        matches = list(re.finditer(r"\S+", text))
        if not matches:
            return [(text, 0, len(text))] if text else []

        slices: list[tuple[str, int, int]] = []
        i = 0
        n = len(matches)

        while i < n:
            chunk_words: list[str] = []
            j = i
            while j < n:
                word = matches[j].group()
                candidate = chunk_words + [word]
                if chunk_words and self.count_tokens(" ".join(candidate)) > max_tokens:
                    break
                chunk_words.append(word)
                j += 1

            start_char = matches[i].start()
            end_char = matches[j - 1].end()
            sub_text = text[start_char:end_char]
            slices.append((sub_text, start_char, end_char))

            if j >= n:
                break

            # Calculate overlap starting index for next window
            k = j - 1
            overlap_words: list[str] = []
            while k > i:
                word = matches[k].group()
                if self.count_tokens(" ".join([word] + overlap_words)) > overlap_tokens:
                    break
                overlap_words.insert(0, word)
                k -= 1

            next_i = k + 1
            if next_i <= i:
                next_i = i + 1
            i = next_i

        return slices if slices else [(text, 0, len(text))]
