"""Observability & Telemetry REST API Endpoints."""
from typing import Any
from fastapi import APIRouter, HTTPException

from app.schemas.observability import TraceSummary, AgentTimelineResponse, CostDashboardMetrics
from app.services.open_telemetry_service import open_telemetry_service
from app.services.agent_timeline_service import agent_timeline_service
from app.services.cost_telemetry import cost_telemetry_tracker

router = APIRouter(prefix="/observability", tags=["Observability & Telemetry"])


@router.get("/traces/{run_id}", response_model=TraceSummary)
def get_trace_spans(run_id: str):
    """Retrieve OpenTelemetry trace spans for an agent run graph."""
    summary = open_telemetry_service.get_trace_summary(run_id)
    if not summary:
        # Generate default empty trace if no active spans recorded yet
        trace_id = open_telemetry_service.get_or_create_trace_id(run_id)
        span = open_telemetry_service.start_span(run_id, f"run.{run_id}.root")
        open_telemetry_service.finish_span(span)
        summary = open_telemetry_service.get_trace_summary(run_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"No trace spans found for run '{run_id}'.")
    return summary


@router.get("/timeline/{run_id}", response_model=AgentTimelineResponse)
def get_agent_timeline(run_id: str):
    """Retrieve Gantt execution timeline steps for parallel agent workstreams."""
    return agent_timeline_service.get_timeline(run_id)


@router.get("/metrics/dashboard", response_model=CostDashboardMetrics)
def get_cost_and_latency_dashboard():
    """Retrieve aggregate token usage, financial cost breakdown, and latency percentiles (p50/p90/p99)."""
    data = cost_telemetry_tracker.get_aggregate_dashboard()
    return CostDashboardMetrics(**data)
