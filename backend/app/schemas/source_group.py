"""Pydantic schemas for source groups."""
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum
from app.schemas.source import SourceResponse

class SourceGroupType(str, Enum):
    INDEPENDENCE = "INDEPENDENCE"
    THEMATIC = "THEMATIC"
    TEMPORAL = "TEMPORAL"

class SourceGroupMemberResponse(BaseModel):
    id: UUID
    group_id: UUID
    source_id: UUID
    created_at: datetime
    updated_at: datetime
    
    source: Optional[SourceResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

class SourceGroupResponse(BaseModel):
    id: UUID
    query_id: UUID
    name: str
    group_type: SourceGroupType
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    members: List[SourceGroupMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)
