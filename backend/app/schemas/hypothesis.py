"""Pydantic schemas for hypotheses, critique reports, and self-challenge."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SUPPORTED = "supported"
    FALSIFIED = "falsified"
    INCONCLUSIVE = "inconclusive"

    @classmethod
    def _missing_(cls, value: Any) -> Any:
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return super()._missing_(value)


class EvidenceRelationship(str, Enum):
    SUPPORTS = "supports"
    FALSIFIES = "falsifies"
    NEUTRAL = "neutral"

    @classmethod
    def _missing_(cls, value: Any) -> Any:
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return super()._missing_(value)


class CritiqueSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def _missing_(cls, value: Any) -> Any:
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper():
                    return member
        return super()._missing_(value)


class WeakEvidenceReason(str, Enum):
    SINGLE_SOURCE = "single_source"
    LOW_CONFIDENCE = "low_confidence"
    UNVERIFIED_INFERENCE = "unverified_inference"
    OUTDATED = "outdated"
    CIRCULAR = "circular"

    @classmethod
    def _missing_(cls, value: Any) -> Any:
        if isinstance(value, str):
            val_norm = value.lower().replace(" ", "_")
            for member in cls:
                if member.value.lower() == val_norm:
                    return member
        return super()._missing_(value)


class EvidenceMapItem(BaseModel):
    evidence_id: Optional[str] = None
    hypothesis_id: Optional[str] = None
    relationship: EvidenceRelationship
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    justification: Optional[str] = None


# Alias for backward compatibility
EvidenceMapEntry = EvidenceMapItem


class HypothesisCreate(BaseModel):
    statement: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    falsifying_claim_ids: list[str] = Field(default_factory=list)
    evidence_map: list[EvidenceMapItem] = Field(default_factory=list)
    max_falsification_attempts: int = 5
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


class HypothesisUpdate(BaseModel):
    statement: Optional[str] = None
    status: Optional[HypothesisStatus] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    supporting_claim_ids: Optional[list[str]] = None
    falsifying_claim_ids: Optional[list[str]] = None
    evidence_map: Optional[list[EvidenceMapItem]] = None
    falsification_attempts: Optional[int] = None
    max_falsification_attempts: Optional[int] = None
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


class HypothesisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    query_id: UUID
    statement: str
    status: HypothesisStatus
    confidence: float
    supporting_claim_ids: list[str] = Field(default_factory=list)
    falsifying_claim_ids: list[str] = Field(default_factory=list)
    evidence_map: list[EvidenceMapItem] = Field(default_factory=list)
    falsification_attempts: int = 0
    max_falsification_attempts: int = 5
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")
    created_at: datetime
    updated_at: datetime


class HypothesisListResponse(BaseModel):
    hypotheses: list[HypothesisResponse]
    total: int


class WeakEvidenceItem(BaseModel):
    claim_id: Optional[str] = None
    reason: WeakEvidenceReason
    severity: CritiqueSeverity
    details: str
    remediation: Optional[str] = None


class MissingVariable(BaseModel):
    variable: str
    impact: str
    category: str
    suggested_action: str


# Alias for backward compatibility
MissingVariableItem = MissingVariable


class CritiqueReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    query_id: UUID
    synthesis_snapshot: str
    findings: list[str] = Field(default_factory=list)
    weak_evidence: list[WeakEvidenceItem] = Field(default_factory=list)
    missing_variables: list[MissingVariable] = Field(default_factory=list)
    overall_severity: CritiqueSeverity
    recommendations: list[str] = Field(default_factory=list)
    replan_triggered: bool = False
    iteration: int = 1
    created_at: datetime
    updated_at: datetime


class CritiqueReportListResponse(BaseModel):
    reports: list[CritiqueReportResponse]
    total: int


class SelfChallengeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query_id: UUID
    max_iterations: int = Field(default=3, ge=1, le=10, alias="max_replan_iterations")
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    @property
    def max_replan_iterations(self) -> int:
        return self.max_iterations


class SelfChallengeResponse(BaseModel):
    query_id: UUID
    hypotheses: list[HypothesisResponse] = Field(default_factory=list)
    critique_reports: list[CritiqueReportResponse] = Field(default_factory=list)
    replan_count: int = 0
    final_status: str = "completed"
    finalized_with_caveats: bool = False
