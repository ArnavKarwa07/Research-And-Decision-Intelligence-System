"""Source Pydantic schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SourceResponse(BaseModel):
    """Schema for a source response."""
    
    id: uuid.UUID
    url: str
    title: str | None = None
    snippet: str | None = None
    quality_score: float
    reliability_rating: str | None = None
    retrieved_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
