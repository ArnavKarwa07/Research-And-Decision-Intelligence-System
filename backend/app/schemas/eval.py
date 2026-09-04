"""Pydantic schemas for Evaluation Framework, Benchmark Datasets, and Metrics."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class RetrievalMetrics(BaseModel):
    """Metrics for RAG / Vector Retrieval performance."""
    precision_at_k: float = Field(..., ge=0.0, le=1.0, description="Precision@K ratio of relevant retrieved chunks.")
    recall_at_k: float = Field(..., ge=0.0, le=1.0, description="Recall@K ratio of retrieved relevant chunks.")
    mrr: float = Field(..., ge=0.0, le=1.0, description="Mean Reciprocal Rank of first relevant chunk.")
    ndcg: float = Field(..., ge=0.0, le=1.0, description="Normalized Discounted Cumulative Gain.")


class ClaimVerificationMetrics(BaseModel):
    """Metrics for claim extraction, hallucination detection, and faithfulness."""
    hallucination_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of claims lacking evidence support.")
    faithfulness_score: float = Field(..., ge=0.0, le=1.0, description="Degree to which generated claims accurately match source context.")
    evidence_groundedness_score: float = Field(..., ge=0.0, le=1.0, description="Ratio of verified grounded claims to total claims.")


class CitationMetrics(BaseModel):
    """Metrics for citation coverage and precision."""
    citation_coverage: float = Field(..., ge=0.0, le=1.0, description="Ratio of material claims accompanied by explicit citations.")
    citation_precision: float = Field(..., ge=0.0, le=1.0, description="Ratio of citations that actually support the cited claim.")


class TrajectoryMetrics(BaseModel):
    """Metrics for agent execution efficiency and tool calling accuracy."""
    trajectory_efficiency: float = Field(..., ge=0.0, le=1.0, description="Ratio of optimal tool execution path to actual steps taken.")
    tool_call_accuracy: float = Field(..., ge=0.0, le=1.0, description="Precision of chosen tool calls and argument validity.")
    unnecessary_replan_penalty: float = Field(..., ge=0.0, le=1.0, description="Penalty score for redundant graph loopbacks without new evidence.")


class DecisionQualityMetrics(BaseModel):
    """Metrics for multi-criteria decision analysis (MCDA) and sensitivity validity."""
    mcda_criteria_weighting_score: float = Field(..., ge=0.0, le=1.0, description="Alignment of criteria weights with ground-truth preferences.")
    scenario_payoff_alignment: float = Field(..., ge=0.0, le=1.0, description="Consistency of best/base/worst scenario rankings against expected payoffs.")
    sensitivity_tipping_point_validity: float = Field(..., ge=0.0, le=1.0, description="Verification of calculated tipping points against stability bounds.")


class GoldenTestCaseCreate(BaseModel):
    """Request payload to create a single test case in a dataset."""
    query_text: str = Field(..., min_length=5, description="Input query/task for the evaluation case.")
    category: str = Field("general", description="Category tag e.g. market_analysis, technical_feasibility.")
    ground_truth_claims: list[dict[str, Any]] = Field(default_factory=list, description="Ground truth factual claims.")
    required_sources: list[str] = Field(default_factory=list, description="Required source domains or identifiers.")
    expected_decision_matrix: dict[str, Any] = Field(default_factory=dict, description="Expected options, criteria, and weights.")
    expected_rankings: list[str] = Field(default_factory=list, description="Expected top alternative rankings.")


class GoldenTestCaseResponse(GoldenTestCaseCreate):
    """Response model for a golden test case."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    created_at: datetime
    updated_at: datetime


class GoldenDatasetCreate(BaseModel):
    """Request payload to create a new Golden Dataset."""
    name: str = Field(..., min_length=3, description="Dataset name.")
    description: Optional[str] = Field(None, description="Dataset summary/description.")
    version: str = Field("1.0.0", description="Semantic version string.")
    category: str = Field("general", description="Primary category tag.")
    test_cases: list[GoldenTestCaseCreate] = Field(default_factory=list)


class GoldenDatasetResponse(BaseModel):
    """Response model for a Golden Dataset."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    version: str
    category: str
    created_at: datetime
    updated_at: datetime
    test_case_count: int = 0


class EvalRunCreate(BaseModel):
    """Request payload to trigger an evaluation run against a dataset."""
    dataset_id: str = Field(..., description="Target dataset ID to evaluate.")
    model_name: str = Field("default", description="Model name evaluated.")
    prompt_version: str = Field("v1", description="Prompt version string.")


class EvalResultResponse(BaseModel):
    """Detailed evaluation result for a single test case."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    eval_run_id: str
    test_case_id: str
    retrieval_metrics: RetrievalMetrics
    claim_metrics: ClaimVerificationMetrics
    citation_metrics: CitationMetrics
    trajectory_metrics: TrajectoryMetrics
    decision_metrics: DecisionQualityMetrics
    overall_score: float
    pass_status: bool
    cost_usd: float
    latency_ms: float
    created_at: datetime


class EvalRunResponse(BaseModel):
    """Response model for an overall evaluation suite run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    dataset_id: str
    model_name: str
    prompt_version: str
    status: str
    summary_metrics: dict[str, Any]
    total_cost: float
    total_latency_ms: float
    created_at: datetime
    updated_at: datetime
    results: list[EvalResultResponse] = Field(default_factory=list)



class RegressionReport(BaseModel):
    """Report comparing a current evaluation run against a baseline run."""
    run_id: str
    baseline_run_id: str
    overall_score_current: float
    overall_score_baseline: float
    overall_score_delta: float
    cost_usd_current: float
    cost_usd_baseline: float
    cost_delta_usd: float
    max_quality_drop_pct: float
    max_cost_increase_pct: float
    has_regression: bool
    regression_reasons: list[str] = Field(default_factory=list)
    category_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)
