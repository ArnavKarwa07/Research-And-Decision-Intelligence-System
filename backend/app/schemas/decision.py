"""Pydantic schemas for decision modeling and analysis."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, AliasChoices


class DecisionCriterion(BaseModel):
    """Evaluation criterion with normalized weight."""

    id: str
    name: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Criterion weight between 0.0 and 1.0")
    description: Optional[str] = None


class AlternativeOptionInput(BaseModel):
    """Candidate option/alternative input for decision analysis."""

    id: str
    name: str
    description: Optional[str] = None
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional map of criterion_id to score (0.0 - 1.0)"
    )


class AlternativeOptionScored(AlternativeOptionInput):
    """Candidate option with multi-criteria scores and weighted total."""

    scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Map of criterion_id to raw or normalized score (0.0 - 1.0)"
    )
    weighted_score: float = Field(
        default=0.0,
        description="Weighted aggregate score across all criteria"
    )
    risks: List[str] = Field(
        default_factory=list,
        description="Option-specific risks identified"
    )


class ScenarioDefinition(BaseModel):
    """Definition of an uncertain future scenario with probability and optional outcomes map."""

    name: str = Field(..., description="e.g. 'best', 'base', 'worst'")
    probability: float = Field(..., ge=0.0, le=1.0, description="Scenario probability, sum to 1.0 across scenarios")
    description: Optional[str] = None
    outcomes: Optional[Dict[str, float]] = Field(default_factory=dict, description="Map of alternative name/ID to projected value")



class ScenarioOutcome(BaseModel):
    """Projected value or utility for an alternative under a scenario."""

    scenario_name: str
    alternative_id: str
    projected_value: float
    notes: Optional[str] = None


class SensitivitySwitchPoint(BaseModel):
    """Tipping point weight where recommendation flips from one alternative to another."""

    criterion_id: str
    criterion_name: str
    original_weight: float
    threshold_weight: float
    switches_from: str
    switches_to: str
    notes: Optional[str] = None


class DecisionTrigger(BaseModel):
    """Tripwire / condition that triggers re-evaluation or contingency action."""

    condition: str
    threshold: str
    action: str
    severity: str = Field(default="medium", description="Severity level: low, medium, high, critical")


class DecisionCreateRequest(BaseModel):
    """Request payload to initiate or run a decision analysis."""

    query_id: UUID
    alternatives: List[AlternativeOptionInput]
    criteria: List[DecisionCriterion]
    scenarios: Optional[List[ScenarioDefinition]] = None
    assumptions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class SensitivityRequest(BaseModel):
    """Request payload to run sensitivity analysis."""

    weight_delta: float = Field(default=0.05, ge=0.001, le=0.5, description="Step size for perturbation")
    target_criteria: Optional[List[str]] = Field(default=None, description="Optional list of criterion IDs to test")


class ScenarioRequest(BaseModel):
    """Request payload to evaluate scenario analysis."""

    scenarios: List[ScenarioDefinition]


class DecisionResponse(BaseModel):
    """Full decision model response matching Decision ORM model."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    query_id: UUID
    recommendation: str
    confidence: float
    rationale: Optional[str] = None
    alternatives: List[Dict[str, Any] | AlternativeOptionScored | AlternativeOptionInput] = Field(default_factory=list)
    criteria: List[Dict[str, Any] | DecisionCriterion] = Field(default_factory=list)
    weighted_matrix: Dict[str, Any] = Field(default_factory=dict)
    scenarios: Dict[str, Any] = Field(default_factory=dict)
    sensitivity_analysis: Dict[str, Any] = Field(default_factory=dict)
    expected_values: Dict[str, Any] = Field(default_factory=dict)
    key_risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    decision_triggers: List[Dict[str, Any] | DecisionTrigger] = Field(default_factory=list)
    metadata_: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
        serialization_alias="metadata"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.metadata_


class DecisionListResponse(BaseModel):
    """Paginated or grouped list of decisions."""

    decisions: List[DecisionResponse]
    total: int
