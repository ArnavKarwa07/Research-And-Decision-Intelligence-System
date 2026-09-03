"""Pydantic schemas for claims."""
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class ClaimType(str, Enum):
    FACT = "FACT"
    CALCULATION = "CALCULATION"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    PREDICTION = "PREDICTION"
    OPINION = "OPINION"
    UNRESOLVED = "UNRESOLVED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value == value.upper():
                    return member
        return super()._missing_(value)

class ClaimStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"

class SupportType(str, Enum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NEUTRAL = "NEUTRAL"

class ClaimSourceLinkCreate(BaseModel):
    source_id: UUID
    excerpt: str
    excerpt_location: Optional[Dict[str, Any]] = None
    support_type: SupportType
    relevance_score: float = 0.5

class ClaimSourceResponse(BaseModel):
    id: UUID
    claim_id: UUID
    source_id: UUID
    excerpt: str
    excerpt_location: Optional[Dict[str, Any]] = None
    support_type: SupportType
    relevance_score: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClaimCreate(BaseModel):
    content: str
    claim_type: ClaimType
    confidence: float = 0.5
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    created_by_agent_run_id: Optional[UUID] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    sources: List[ClaimSourceLinkCreate] = []

class ClaimResponse(BaseModel):
    id: UUID
    query_id: UUID
    content: str
    claim_type: ClaimType
    confidence: float
    status: ClaimStatus
    created_by_agent_run_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime
    
    claim_sources: List[ClaimSourceResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
