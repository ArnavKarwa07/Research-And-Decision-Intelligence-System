"""Pydantic schemas for Phase 12 Project Memory & Heuristics."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.project_memory import (
    HumanApprovalStatus,
    MemoryType,
    ValidityStatus,
)


class ProjectMemoryItemCreate(BaseModel):
    """Schema for creating a project memory item."""

    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    memory_type: str = Field(default=MemoryType.FACT.value, description="Type of memory item")
    key: str = Field(..., description="Unique lookup key or concept topic")
    summary: str = Field(..., description="High-level text summary of memory item")
    content: Dict[str, Any] = Field(default_factory=dict, description="Detailed structured payload or text dict")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    source_query_id: Optional[UUID] = None
    validity_status: str = Field(default=ValidityStatus.ACTIVE.value, description="ACTIVE, SUPERSEDED, or INVALIDATED")
    human_approval_status: str = Field(
        default=HumanApprovalStatus.NOT_REQUIRED.value, description="NOT_REQUIRED, PENDING, APPROVED, REJECTED"
    )
    tags: List[str] = Field(default_factory=list, description="Categorization tags")

    @field_validator("key", "summary")
    @classmethod
    def validate_non_empty_str(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace.")
        return s

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        if isinstance(v, MemoryType):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in MemoryType.__members__:
            raise ValueError(f"Invalid memory_type '{v}'. Must be one of {[e.value for e in MemoryType]}.")
        return upper_v

    @field_validator("validity_status")
    @classmethod
    def validate_validity_status(cls, v: str) -> str:
        if isinstance(v, ValidityStatus):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in ValidityStatus.__members__:
            raise ValueError(f"Invalid validity_status '{v}'. Must be one of {[e.value for e in ValidityStatus]}.")
        return upper_v

    @field_validator("human_approval_status")
    @classmethod
    def validate_human_approval_status(cls, v: str) -> str:
        if isinstance(v, HumanApprovalStatus):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in HumanApprovalStatus.__members__:
            raise ValueError(f"Invalid human_approval_status '{v}'. Must be one of {[e.value for e in HumanApprovalStatus]}.")
        return upper_v


class ProjectMemoryItemUpdate(BaseModel):
    """Schema for updating a project memory item."""

    summary: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    validity_status: Optional[str] = None
    human_approval_status: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        if not s:
            raise ValueError("summary cannot be empty or whitespace.")
        return s

    @field_validator("validity_status")
    @classmethod
    def validate_validity_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, ValidityStatus):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in ValidityStatus.__members__:
            raise ValueError(f"Invalid validity_status '{v}'. Must be one of {[e.value for e in ValidityStatus]}.")
        return upper_v

    @field_validator("human_approval_status")
    @classmethod
    def validate_human_approval_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, HumanApprovalStatus):
            return v.value
        upper_v = str(v).upper()
        if upper_v not in HumanApprovalStatus.__members__:
            raise ValueError(f"Invalid human_approval_status '{v}'. Must be one of {[e.value for e in HumanApprovalStatus]}.")
        return upper_v


class ProjectMemoryItemResponse(BaseModel):
    """Schema for returning a project memory item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    memory_type: str
    key: str
    summary: str
    content: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    source_query_id: Optional[UUID] = None
    validity_status: str
    human_approval_status: str
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("content", mode="before")
    @classmethod
    def coerce_none_content(cls, v: Any) -> Any:
        return v if v is not None else {}

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_none_tags(cls, v: Any) -> Any:
        return v if v is not None else []


class ResearchHeuristicCreate(BaseModel):
    """Schema for creating domain-specific research heuristics."""

    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    domain: str = Field(..., description="Target domain, e.g. finance, healthcare, software")
    untrusted_domains: List[str] = Field(default_factory=list, description="List of domain names to avoid or scrutinize")
    effective_query_templates: List[str] = Field(default_factory=list, description="Successful query templates")
    verified_tool_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="High-performing tool call sequences")
    failure_modes: List[Dict[str, Any]] = Field(default_factory=list, description="Recorded failure modes to avoid")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("domain cannot be empty or whitespace.")
        return s


class ResearchHeuristicResponse(BaseModel):
    """Schema for returning domain-specific research heuristics."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    domain: str
    untrusted_domains: List[str] = Field(default_factory=list)
    effective_query_templates: List[str] = Field(default_factory=list)
    verified_tool_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    failure_modes: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator(
        "untrusted_domains",
        "effective_query_templates",
        "verified_tool_patterns",
        "failure_modes",
        mode="before",
    )
    @classmethod
    def coerce_none_lists(cls, v: Any) -> Any:
        return v if v is not None else []


class ProjectMemoryContext(BaseModel):
    """Aggregated project memory context passed into research & decision workflows."""

    project_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    active_facts: List[ProjectMemoryItemResponse] = Field(default_factory=list)
    prior_conclusions: List[ProjectMemoryItemResponse] = Field(default_factory=list)
    reusable_assumptions: List[ProjectMemoryItemResponse] = Field(default_factory=list)
    lessons_learned: List[ProjectMemoryItemResponse] = Field(default_factory=list)
    heuristics: Optional[ResearchHeuristicResponse] = None

