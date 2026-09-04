"""Pydantic schemas for Data Agent and Data Visualization (Phase 7)."""
from uuid import UUID
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- SQL Query & Schema Schemas ---
class SQLQueryRequest(BaseModel):
    sql: str = Field(..., description="Read-only SQL query string to execute")
    dataset_id: Optional[UUID] = Field(None, description="Optional uploaded dataset ID")
    table_name: Optional[str] = Field(None, description="Optional target table name")
    limit: int = Field(100, ge=1, le=5000, description="Max rows to return")


class SQLQueryResponse(BaseModel):
    query_id: Optional[UUID] = None
    sql: str
    is_success: bool
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None


class TableColumnInfo(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False


class DatasetProfileResponse(BaseModel):
    dataset_id: UUID
    filename: str
    file_type: str
    table_name: str
    row_count: int
    column_count: int
    columns: List[TableColumnInfo] = Field(default_factory=list)
    summary_stats: Dict[str, Any] = Field(default_factory=dict)
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list)


# --- Python Sandbox Schemas ---
class StatisticalSummary(BaseModel):
    metric_name: str
    count: int = 0
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    median: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None
    correlations: Dict[str, float] = Field(default_factory=dict)
    trend_direction: Optional[str] = None  # increasing, decreasing, stable, volatile


class PythonAnalysisRequest(BaseModel):
    python_code: str = Field(..., description="Python pandas/numpy script to execute")
    dataset_id: Optional[UUID] = Field(None, description="Optional dataset ID to provide as 'df'")
    input_data: Optional[List[Dict[str, Any]]] = Field(None, description="Optional inline dictionary data")


class PythonAnalysisResponse(BaseModel):
    is_success: bool
    stdout: str = ""
    stderr: str = ""
    result_data: List[Dict[str, Any]] = Field(default_factory=list)
    statistical_summary: Optional[StatisticalSummary] = None
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None


# --- Visualization Specs Schemas ---
class ChartSpecRequest(BaseModel):
    title: str
    chart_type: str = Field("bar", description="bar, line, scatter, pie, summary_table")
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    data: List[Dict[str, Any]] = Field(default_factory=list)
    description: Optional[str] = None


class ChartSpecResponse(BaseModel):
    id: UUID
    query_id: Optional[UUID] = None
    title: str
    chart_type: str
    description: Optional[str] = None
    spec_json: Dict[str, Any] = Field(default_factory=dict)
    table_data: List[Dict[str, Any]] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


# --- Reproducible Artifact Schemas ---
class ReproducibleArtifactResponse(BaseModel):
    id: UUID
    query_id: Optional[UUID] = None
    title: str
    sql_queries: List[str] = Field(default_factory=list)
    python_scripts: List[str] = Field(default_factory=list)
    chart_configs: List[Dict[str, Any]] = Field(default_factory=list)
    intermediate_data_summary: Dict[str, Any] = Field(default_factory=dict)
    execution_logs: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
