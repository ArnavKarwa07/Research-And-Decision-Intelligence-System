"""Plain text document parser."""
import os
from app.rag.parsers.base import BaseDocumentParser, ParsedDocument, ParsedSection


class TXTParser(BaseDocumentParser):
    """Parser for plain text (.txt) files."""

    def parse(self, file_path: str) -> ParsedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Text file not found at: {file_path}")

        # Try reading with utf-8 first, fallback to latin-1
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                full_text = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                full_text = f.read()

        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        sections: list[ParsedSection] = [
            ParsedSection(heading=None, text=p) for p in paragraphs
        ]

        filename = os.path.basename(file_path)

        return ParsedDocument(
            title=filename,
            text=full_text,
            sections=sections if sections else [ParsedSection(heading=None, text=full_text)],
            metadata={"char_count": len(full_text), "paragraph_count": len(paragraphs)},
            mime_type="text/plain",
        )
