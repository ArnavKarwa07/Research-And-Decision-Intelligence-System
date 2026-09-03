from __future__ import annotations
import math
import re
import logging
from typing import List, Dict, Tuple, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.agent_contracts import DocumentChunk

logger = logging.getLogger(__name__)

# Standard English Stop Words
STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into",
    "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's",
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs",
    "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}


def tokenize_text(text: str, remove_stopwords: bool = True) -> List[str]:
    """Tokenize text into lowercase alphanumeric terms, stripping stop words."""
    if not text:
        return []
    terms = re.findall(r'\b\w+\b', text.lower())
    if remove_stopwords:
        terms = [t for t in terms if t not in STOPWORDS and len(t) > 1]
    return terms


class BM25SessionIndex:
    """In-memory BM25 index for a single session corpus of DocumentChunk objects."""

    def __init__(self, chunks: List[DocumentChunk], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[DocumentChunk] = chunks
        self.chunk_map: Dict[str, DocumentChunk] = {c.chunk_id: c for c in chunks}
        self.num_docs: int = len(chunks)
        
        self.doc_lengths: Dict[str, int] = {}
        self.term_freqs: Dict[str, Dict[str, int]] = {}  # chunk_id -> {term -> freq}
        self.doc_freqs: Dict[str, int] = {}              # term -> num docs containing term
        self.idf: Dict[str, float] = {}
        
        self.avg_doc_length: float = 0.0
        self._build_index()

    def _build_index(self) -> None:
        if not self.chunks:
            return

        total_length = 0
        for chunk in self.chunks:
            tokens = tokenize_text(chunk.content)
            doc_len = len(tokens)
            self.doc_lengths[chunk.chunk_id] = doc_len
            total_length += doc_len

            freqs: Dict[str, int] = {}
            for token in tokens:
                freqs[token] = freqs.get(token, 0) + 1

            self.term_freqs[chunk.chunk_id] = freqs
            for term in freqs.keys():
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avg_doc_length = total_length / float(self.num_docs) if self.num_docs > 0 else 0.0

        # Calculate Robertson-Spärck Jones IDF for each term
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log(1.0 + (self.num_docs - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 10, phrase_boost: float = 1.5) -> List[Tuple[DocumentChunk, float]]:
        """Score all documents against the query using Okapi BM25 with phrase match boosting."""
        if not self.chunks or not query.strip():
            return []

        query_terms = tokenize_text(query, remove_stopwords=True)
        if not query_terms:
            # Fallback to un-filtered tokens if query was purely stop words
            query_terms = tokenize_text(query, remove_stopwords=False)

        scores: Dict[str, float] = {c.chunk_id: 0.0 for c in self.chunks}

        for term in query_terms:
            idf_val = self.idf.get(term, 0.0)
            if idf_val <= 0:
                continue

            for chunk_id, freqs in self.term_freqs.items():
                f = freqs.get(term, 0)
                if f == 0:
                    continue

                doc_len = self.doc_lengths.get(chunk_id, 0)
                length_norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_length) if self.avg_doc_length > 0 else 1.0
                numerator = f * (self.k1 + 1.0)
                denominator = f + self.k1 * length_norm
                
                scores[chunk_id] += idf_val * (numerator / denominator)

        # Exact phrase matching check (minimum 3 characters, not a single stopword, word boundary match)
        query_clean = query.strip().lower().replace('"', '')
        if query_clean and len(query_clean) >= 3 and query_clean not in STOPWORDS:
            pattern = r'\b' + re.escape(query_clean) + r'\b'
            for chunk in self.chunks:
                content_lower = chunk.content.lower()
                if re.search(pattern, content_lower):
                    scores[chunk.chunk_id] += phrase_boost * max(scores[chunk.chunk_id], 1.0)

        # Filter documents with score > 0
        results = [
            (self.chunk_map[cid], round(score, 4))
            for cid, score in scores.items()
            if score > 0.0
        ]

        # Sort descending by BM25 score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]



class BM25Engine:
    """Session-aware BM25 keyword search engine with in-memory caching."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._indices: Dict[str, BM25SessionIndex] = {}

    def index_chunks(self, session_id: str, chunks: List[DocumentChunk]) -> int:
        """Replace and index chunks for a given session."""
        self._indices[session_id] = BM25SessionIndex(chunks, k1=self.k1, b=self.b)
        logger.info(f"[BM25Engine] Indexed {len(chunks)} chunks for session '{session_id}'.")
        return len(chunks)

    def add_chunks(self, session_id: str, chunks: List[DocumentChunk]) -> int:
        """Append chunks to existing session index."""
        existing = self._indices[session_id].chunks if session_id in self._indices else []
        combined = existing + chunks
        self._indices[session_id] = BM25SessionIndex(combined, k1=self.k1, b=self.b)
        logger.info(f"[BM25Engine] Added {len(chunks)} chunks to session '{session_id}' (total {len(combined)}).")
        return len(combined)

    def get_chunks(self, session_id: str) -> List[DocumentChunk]:
        """Get all indexed chunks for a session."""
        if session_id in self._indices:
            return self._indices[session_id].chunks
        return []

    def search(
        self,
        session_id: str,
        query: str,
        top_k: int = 10,
        chunks_override: Optional[List[DocumentChunk]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search BM25 index for a session or ad-hoc chunks override."""
        if chunks_override is not None:
            temp_index = BM25SessionIndex(chunks_override, k1=self.k1, b=self.b)
            return temp_index.search(query, top_k=top_k)

        index = self._indices.get(session_id)
        if not index:
            logger.warning(f"[BM25Engine] No index found for session '{session_id}'.")
            return []

        return index.search(query, top_k=top_k)


# Global singleton instance
bm25_engine = BM25Engine()
