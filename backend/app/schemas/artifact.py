"""Pydantic schemas for Phase 11 artifacts and export packages."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict



class DecisionMemoCreateRequest(BaseModel):
    query_id: UUID
    title: Optional[str] = Field(None, description="Optional custom memo title")
    include_scenarios: bool = Field(True, description="Include best/base/worst scenario projections")
    include_citations: bool = Field(True, description="Include footnote citation index")


class DecisionMemoResponse(BaseModel):
    id: UUID
    query_id: UUID
    title: str
    artifact_type: Literal["decision_memo"] = "decision_memo"
    executive_summary: str
    objective_and_constraints: Dict[str, Any]
    mcda_comparison_matrix: Dict[str, Any]
    scenario_projections: List[Dict[str, Any]]
    key_risks_and_assumptions: Dict[str, Any]
    citation_footnotes: List[Dict[str, Any]]
    markdown_content: str
    html_content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ExecutiveReportCreateRequest(BaseModel):
    query_id: UUID
    title: Optional[str] = Field(None, description="Optional custom report title")


class ExecutiveReportResponse(BaseModel):
    id: UUID
    query_id: UUID
    title: str
    artifact_type: Literal["research_report"] = "research_report"
    executive_summary: str
    research_methodology: Dict[str, Any]
    claims_breakdown: Dict[str, Any]
    source_quality_stats: Dict[str, Any]
    decision_matrix: Dict[str, Any]
    markdown_content: str
    html_content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ComparisonTableResponse(BaseModel):
    query_id: UUID
    alternatives: List[Dict[str, Any]]
    criteria: List[Dict[str, Any]]
    weighted_scores: Dict[str, float]
    rankings: List[Dict[str, Any]]
    csv_spec: str
    markdown_table: str


class ExportPackageResponse(BaseModel):
    query_id: UUID
    download_url: str
    filename: str
    file_size_bytes: int
    included_artifacts: List[str]
    created_at: datetime
