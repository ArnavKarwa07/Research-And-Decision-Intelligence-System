"""Document and DocumentChunk schemas."""
from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response."""
    
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    content_hash: str
    token_count: int
    page_number: int | None = None
    section_heading: str | None = None
    start_offset: int = 0
    end_offset: int = 0
    parent_chunk_id: UUID | None = None
    embedding_id: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    """Schema for document response."""
    
    id: UUID
    session_id: UUID
    filename: str
    mime_type: str
    file_path: str
    file_size: int
    file_hash: str
    status: str
    error_message: str | None = None
    chunk_count: int
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
