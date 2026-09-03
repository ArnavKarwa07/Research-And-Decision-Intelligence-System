"""Markdown document parser."""
import os
import re
from app.rag.parsers.base import BaseDocumentParser, ParsedDocument, ParsedSection


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")


class MarkdownParser(BaseDocumentParser):
    """Parser for Markdown (.md) files extracting headings and sections."""

    def parse(self, file_path: str) -> ParsedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Markdown file not found at: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                full_text = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                full_text = f.read()

        lines = full_text.splitlines()
        sections: list[ParsedSection] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        for line in lines:
            match = HEADING_PATTERN.match(line)
            if match:
                if current_lines:
                    text_block = "\n".join(current_lines).strip()
                    if text_block:
                        sections.append(
                            ParsedSection(
                                heading=current_heading,
                                text=text_block,
                            )
                        )
                    current_lines = []
                current_heading = match.group(2).strip()
            else:
                current_lines.append(line)

        # Flush remaining section
        if current_lines:
            text_block = "\n".join(current_lines).strip()
            if text_block:
                sections.append(
                    ParsedSection(
                        heading=current_heading,
                        text=text_block,
                    )
                )

        filename = os.path.basename(file_path)

        return ParsedDocument(
            title=filename,
            text=full_text,
            sections=sections if sections else [ParsedSection(heading=None, text=full_text)],
            metadata={"char_count": len(full_text), "section_count": len(sections)},
            mime_type="text/markdown",
        )
