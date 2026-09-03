"""Base document parser interface and data structures."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedSection:
    """Represents a section within a parsed document."""
    heading: str | None = None
    text: str = ""
    page_number: int | None = None


@dataclass
class ParsedDocument:
    """Represents the complete parsed content of a document."""
    title: str
    text: str
    sections: list[ParsedSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    mime_type: str = "text/plain"


class BaseDocumentParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a document file and return structured document data.

        Args:
            file_path: Absolute or relative path to the target document.

        Returns:
            ParsedDocument containing text, sections, and metadata.
        """
        pass
