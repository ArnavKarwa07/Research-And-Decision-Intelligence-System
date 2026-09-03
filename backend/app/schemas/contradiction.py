"""Pydantic schemas for contradictions."""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class ContradictionType(str, Enum):
    DIRECT_CONFLICT = "DIRECT_CONFLICT"
    NUMERIC_MISMATCH = "NUMERIC_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    LOGICAL = "LOGICAL"
    METHODOLOGICAL = "METHODOLOGICAL"

class ContradictionSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ResolutionStatus(str, Enum):
    UNRESOLVED = "unresolved"
    RESOLVED_A = "resolved_a"
    RESOLVED_B = "resolved_b"
    RESOLVED_BOTH = "resolved_both"
    ESCALATED = "escalated"

class ContradictionResolveRequest(BaseModel):
    resolution_status: ResolutionStatus
    resolution_notes: Optional[str] = None

    @field_validator("resolution_status")
    @classmethod
    def check_valid_status(cls, v):
        if v.value not in ("resolved_a", "resolved_b", "resolved_both", "escalated"):
            raise ValueError("Invalid resolution status")
        return v

class ContradictionResponse(BaseModel):
    id: UUID
    query_id: UUID
    claim_a_id: UUID
    claim_b_id: UUID
    contradiction_type: ContradictionType
    severity: ContradictionSeverity
    resolution_status: ResolutionStatus
    resolution_notes: Optional[str] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
