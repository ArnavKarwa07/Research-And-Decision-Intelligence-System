"""Query Pydantic schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class QueryCreate(BaseModel):
    """Schema for creating a query."""
    
    text: str = Field(..., min_length=1, max_length=10000)
    mode: str = 'standard'
    budget: dict | None = None

class QueryResponse(BaseModel):
    """Schema for a query response."""
    
    id: uuid.UUID
    session_id: uuid.UUID
    text: str
    status: str
    research_plan: dict | None = None
    summary: str | None = None
    confidence: float | None = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class QueryStatus(BaseModel):
    """Schema for the status of a query."""
    
    id: uuid.UUID
    status: str
    confidence: float | None = None
