"""Factory for instantiating appropriate document parser based on format."""
import os
from typing import Type
from app.rag.parsers.base import BaseDocumentParser
from app.rag.parsers.pdf_parser import PDFParser
from app.rag.parsers.docx_parser import DOCXParser
from app.rag.parsers.txt_parser import TXTParser
from app.rag.parsers.markdown_parser import MarkdownParser


class DocumentParserFactory:
    """Factory for selecting and instantiating document parsers."""

    _MIME_MAP: dict[str, Type[BaseDocumentParser]] = {
        "application/pdf": PDFParser,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXParser,
        "application/msword": DOCXParser,
        "text/plain": TXTParser,
        "text/markdown": MarkdownParser,
        "text/x-markdown": MarkdownParser,
    }

    _EXTENSION_MAP: dict[str, Type[BaseDocumentParser]] = {
        ".pdf": PDFParser,
        ".docx": DOCXParser,
        ".doc": DOCXParser,
        ".txt": TXTParser,
        ".md": MarkdownParser,
        ".markdown": MarkdownParser,
    }

    @classmethod
    def get_parser(
        cls,
        mime_type: str | None = None,
        file_path: str | None = None,
    ) -> BaseDocumentParser:
        """Get appropriate parser instance based on MIME type or file extension.

        Args:
            mime_type: Optional MIME type string.
            file_path: Optional file path string to check extension.

        Returns:
            Instance of BaseDocumentParser subclass.

        Raises:
            ValueError: If no suitable parser is found.
        """
        # Handle positional parameter where file_path is passed as first argument
        if mime_type and not file_path and ("." in mime_type or "/" in mime_type or "\\" in mime_type):
            if "/" not in mime_type or not mime_type.startswith("text/"):
                file_path = mime_type
                mime_type = None

        if mime_type:
            mt_lower = mime_type.lower()
            if mt_lower in cls._MIME_MAP:
                parser_cls = cls._MIME_MAP[mt_lower]
                return parser_cls()

        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in cls._EXTENSION_MAP:
                parser_cls = cls._EXTENSION_MAP[ext]
                return parser_cls()

        # Fallback to TXT parser for generic text or unknown types
        if mime_type and (mime_type.lower().startswith("text/") or mime_type.lower() == "application/octet-stream"):
            return TXTParser()

        supported_exts = ", ".join(sorted(cls._EXTENSION_MAP.keys()))
        supported_mimes = ", ".join(sorted(cls._MIME_MAP.keys()))
        raise ValueError(
            f"Unsupported document format. MIME type: '{mime_type}', file path: '{file_path}'. "
            f"Supported extensions: [{supported_exts}], Supported MIME types: [{supported_mimes}]"
        )
