from __future__ import annotations
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.agents.agent_contracts import DocumentChunk

logger = logging.getLogger(__name__)


class CitationMetadata(BaseModel):
    """Detailed provenance citation metadata model for document chunks."""
    document_id: str
    filename: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    source_type: str = "INTERNAL_VERIFIED"  # INTERNAL_VERIFIED, EXTERNAL_VERIFIED, UNVERIFIED
    formatted_citation: str = ""


class CitationMapper:
    """Utility class for extracting chunk provenance and generating standardized citation strings."""

    @staticmethod
    def extract_provenance(chunk: DocumentChunk) -> CitationMetadata:
        """Extract provenance metadata from a DocumentChunk."""
        if chunk is None:
            return CitationMetadata(
                document_id="doc-ref",
                filename="Doc-doc-ref",
                formatted_citation="[Doc-doc-ref]"
            )

        meta: Dict[str, Any] = (getattr(chunk, "metadata", None) or {}) if not isinstance(chunk, dict) else (chunk.get("metadata") or {})
        doc_id = getattr(chunk, "document_id", None) or (chunk.get("document_id") if isinstance(chunk, dict) else None) or "doc-ref"

        filename = (
            meta.get("filename")
            or meta.get("doc_title")
            or meta.get("source_name")
            or f"Doc-{str(doc_id)[:8]}"
        )

        page_number = meta.get("page_number")
        if page_number is None:
            page_number = meta.get("page")

        if page_number is not None:
            try:
                page_number = int(page_number)
            except (ValueError, TypeError):
                page_number = None

        section_heading = meta.get("section_heading") or meta.get("section")
        start_offset = meta.get("start_offset")
        end_offset = meta.get("end_offset")
        source_type = meta.get("source_type", "INTERNAL_VERIFIED")

        citation_meta = CitationMetadata(
            document_id=str(doc_id),
            filename=str(filename),
            page_number=page_number,
            section_heading=str(section_heading) if section_heading else None,
            start_offset=start_offset,
            end_offset=end_offset,
            source_type=str(source_type)
        )
        citation_meta.formatted_citation = CitationMapper.format_citation(citation_meta)
        return citation_meta

    @staticmethod
    def format_citation(meta: CitationMetadata) -> str:
        """Format citation string according to RADIS contract: [Filename, p.X, §Section]."""
        parts = [meta.filename]
        if meta.page_number is not None:
            parts.append(f"p.{meta.page_number}")
        if meta.section_heading:
            parts.append(f"§{meta.section_heading}")

        return f"[{', '.join(parts)}]"

    @staticmethod
    def format_chunk_citation(chunk: DocumentChunk) -> str:
        """Convenience helper to extract and format citation string directly from a DocumentChunk."""
        meta = CitationMapper.extract_provenance(chunk)
        return meta.formatted_citation

