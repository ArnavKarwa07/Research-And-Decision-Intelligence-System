"""Unit tests for OpenTelemetry and LangSmith Tracing Service."""
import pytest
from app.services.open_telemetry_service import open_telemetry_service


def test_open_telemetry_tracing_lifecycle():
    run_id = "test_run_otel_123"
    trace_id = open_telemetry_service.get_or_create_trace_id(run_id)
    assert len(trace_id) == 32

    root_span = open_telemetry_service.start_span(
        run_id=run_id, name="root_orchestration", attributes={"environment": "test"}
    )
    assert root_span.span_id is not None
    assert root_span.trace_id == trace_id

    sub_span = open_telemetry_service.start_span(
        run_id=run_id,
        name="research.search",
        parent_span_id=root_span.span_id,
        attributes={"query": "test query"},
    )
    assert sub_span.parent_span_id == root_span.span_id

    open_telemetry_service.finish_span(sub_span, status_code="OK")
    open_telemetry_service.finish_span(root_span, status_code="OK")

    summary = open_telemetry_service.get_trace_summary(run_id)
    assert summary is not None
    assert summary.total_spans == 2
    assert summary.root_span_name == "root_orchestration"
    assert summary.total_duration_ms >= 0.0
