"""PDF document parser using pypdf."""
import os
from typing import Any
from app.rag.parsers.base import BaseDocumentParser, ParsedDocument, ParsedSection


class PDFParser(BaseDocumentParser):
    """Parser for PDF files using pypdf."""

    def parse(self, file_path: str) -> ParsedDocument:
        try:
            import pypdf
        except ImportError as e:
            raise ImportError(
                "pypdf package is required for parsing PDF documents. "
                "Install it using 'pip install pypdf'."
            ) from e

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        reader = pypdf.PdfReader(file_path)
        
        metadata: dict[str, Any] = {
            "num_pages": len(reader.pages),
        }
        
        if reader.metadata:
            if reader.metadata.title:
                metadata["title"] = reader.metadata.title
            if reader.metadata.author:
                metadata["author"] = reader.metadata.author
            if reader.metadata.creation_date:
                metadata["creation_date"] = str(reader.metadata.creation_date)

        sections: list[ParsedSection] = []
        full_text_parts: list[str] = []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            page_text = page.extract_text() or ""
            page_text_clean = page_text.strip()
            
            if page_text_clean:
                full_text_parts.append(page_text_clean)
                sections.append(
                    ParsedSection(
                        heading=f"Page {page_num}",
                        text=page_text_clean,
                        page_number=page_num,
                    )
                )

        full_text = "\n\n".join(full_text_parts)
        filename = os.path.basename(file_path)
        doc_title = metadata.get("title") or filename

        return ParsedDocument(
            title=doc_title,
            text=full_text,
            sections=sections,
            metadata=metadata,
            mime_type="application/pdf",
        )
