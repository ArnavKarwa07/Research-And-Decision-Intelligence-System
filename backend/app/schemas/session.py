"""Session Pydantic schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.schemas.common import PaginatedResponse

class SessionCreate(BaseModel):
    """Schema for creating a session."""
    
    title: str | None = None
    metadata_: dict | None = None

class SessionResponse(BaseModel):
    """Schema for a session response."""
    
    id: uuid.UUID
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

SessionList = PaginatedResponse[SessionResponse]
