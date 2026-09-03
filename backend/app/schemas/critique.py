"""Pydantic schemas for Critique / Red-Team auditing reports."""
import uuid
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class CritiqueSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WeakEvidenceReason(str, Enum):
    SINGLE_SOURCE = "SINGLE_SOURCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTORY = "CONTRADICTORY"
    OUTDATED = "OUTDATED"


class WeakEvidenceItem(BaseModel):
    claim_id: str
    reason: str
    severity: str
    details: str
    remediation: str


class MissingVariableItem(BaseModel):
    variable: str
    impact: str
    category: str
    suggested_action: str


class CritiqueReportResponse(BaseModel):
    id: uuid.UUID
    query_id: uuid.UUID
    synthesis_snapshot: str = ""
    findings: List[str] = Field(default_factory=list)
    weak_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    missing_variables: List[Dict[str, Any]] = Field(default_factory=list)
    overall_severity: str = "LOW"
    recommendations: List[str] = Field(default_factory=list)
    replan_triggered: bool = False
    iteration: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CritiqueReportListResponse(BaseModel):
    reports: List[CritiqueReportResponse] = Field(default_factory=list)
    total: int = 0
