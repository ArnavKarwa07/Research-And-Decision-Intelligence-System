"""Common Pydantic schemas."""
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    detail: str
    code: str

class PaginatedResponse(BaseModel, Generic[T]):
    """Schema for paginated responses."""
    
    items: list[T]
    total: int
    cursor: str | None
    
    model_config = ConfigDict(from_attributes=True)
