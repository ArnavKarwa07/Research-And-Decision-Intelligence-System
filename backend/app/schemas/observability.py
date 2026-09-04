"""Pydantic schemas for Observability, OpenTelemetry Tracing, and Cost/Latency Monitoring."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class TraceSpan(BaseModel):
    """Represents a single execution span in OpenTelemetry tracing."""
    span_id: str = Field(..., description="Unique 16-hex character span ID.")
    trace_id: str = Field(..., description="Unique 32-hex character trace ID.")
    parent_span_id: Optional[str] = Field(None, description="Parent span ID if nested.")
    name: str = Field(..., description="Name of the operation e.g. supervisor.plan, research.search.")
    span_kind: str = Field("INTERNAL", description="Span kind: INTERNAL, SERVER, CLIENT, PRODUCER.")
    start_time: str = Field(..., description="ISO 8601 start timestamp.")
    end_time: Optional[str] = Field(None, description="ISO 8601 end timestamp.")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds.")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Metadata key-value pairs.")
    status_code: str = Field("OK", description="Span status: OK, ERROR, UNSET.")


class TraceSummary(BaseModel):
    """Aggregate trace summary for a full run execution graph."""
    trace_id: str
    run_id: str
    root_span_name: str
    total_spans: int
    total_duration_ms: float
    spans: list[TraceSpan] = Field(default_factory=list)


class AgentTimelineStep(BaseModel):
    """Single step element in a Gantt execution timeline."""
    agent_name: str = Field(..., description="Name of agent execution workstream.")
    step_name: str = Field(..., description="Sub-task or tool execution step.")
    start_time: str = Field(..., description="ISO 8601 start timestamp.")
    end_time: Optional[str] = Field(None, description="ISO 8601 end timestamp.")
    duration_ms: float = Field(0.0, description="Duration in milliseconds.")
    tool_calls: list[str] = Field(default_factory=list, description="Names of tools called during step.")
    status: str = Field("completed", description="Status: pending, running, completed, failed.")


class AgentTimelineResponse(BaseModel):
    """Full Gantt chart execution timeline response for a run."""
    run_id: str
    total_duration_ms: float
    steps: list[AgentTimelineStep] = Field(default_factory=list)


class LatencyPercentiles(BaseModel):
    """Latency distribution percentiles across runs."""
    p50_ms: float = Field(..., ge=0.0, description="50th percentile (median) latency in ms.")
    p90_ms: float = Field(..., ge=0.0, description="90th percentile latency in ms.")
    p99_ms: float = Field(..., ge=0.0, description="99th percentile latency in ms.")
    avg_ms: float = Field(..., ge=0.0, description="Average latency in ms.")
    min_ms: float = Field(..., ge=0.0, description="Minimum latency in ms.")
    max_ms: float = Field(..., ge=0.0, description="Maximum latency in ms.")


class CostDashboardMetrics(BaseModel):
    """Granular cost, token usage, and latency monitoring dashboard."""
    total_tokens: int = Field(0, ge=0)
    prompt_tokens: int = Field(0, ge=0)
    completion_tokens: int = Field(0, ge=0)
    total_cost_usd: float = Field(0.0, ge=0.0)
    llm_cost_usd: float = Field(0.0, ge=0.0)
    tool_cost_usd: float = Field(0.0, ge=0.0)
    cost_by_agent: dict[str, float] = Field(default_factory=dict)
    cost_by_model: dict[str, float] = Field(default_factory=dict)
    latency_distribution: LatencyPercentiles
