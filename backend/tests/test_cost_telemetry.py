"""Unit and integration tests for CostTelemetry service and real-time SSE telemetry streaming."""

import asyncio
import pytest
from uuid import uuid4

from app.services.cost_telemetry import (
    CostTelemetryTracker,
    estimate_llm_cost,
    estimate_tool_cost,
    emit_budget_exceeded,
    emit_budget_telemetry,
    emit_budget_warning,
    emit_cost_updated,
)
from app.services.stream_service import stream_service


def test_estimate_llm_cost_known_and_unknown_models():
    # gpt-4o: prompt 0.0025/1k, completion 0.01/1k
    # 1000 prompt tokens = $0.0025, 500 completion tokens = $0.005 -> total 0.0075
    cost_gpt4o = estimate_llm_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
    assert cost_gpt4o == 0.0075

    # Unknown model -> fallback default: prompt 0.0020/1k, completion 0.0080/1k
    cost_unknown = estimate_llm_cost("unknown-model", prompt_tokens=1000, completion_tokens=1000)
    assert cost_unknown == 0.0100


def test_estimate_tool_cost():
    # web_search: $0.01 per call
    search_cost = estimate_tool_cost("web_search", call_count=3)
    assert search_cost == 0.03

    # python_interpreter: $0.005 per call
    python_cost = estimate_tool_cost("python_interpreter", call_count=2)
    assert python_cost == 0.01

    # unknown tool -> fallback $0.001
    default_cost = estimate_tool_cost("custom_tool", call_count=5)
    assert default_cost == 0.005


@pytest.mark.asyncio
async def test_cost_telemetry_tracker_and_sse_streaming():
    query_id = uuid4()
    tracker = CostTelemetryTracker()

    # Subscribe to SSE stream for this query_id
    sub_id, generator = await stream_service.subscribe(query_id)

    # Record LLM call
    inc_cost_1 = tracker.record_llm_call(
        query_id=query_id,
        model_name="gpt-4o-mini",
        prompt_tokens=2000,
        completion_tokens=1000,
    )
    assert inc_cost_1 > 0

    # Record Tool call
    inc_cost_2 = tracker.record_tool_call(
        query_id=query_id,
        tool_name="web_search",
        call_count=2,
    )
    assert inc_cost_2 == 0.02

    summary = tracker.get_summary(query_id)
    assert summary["total_tokens"] == 3000
    assert summary["tool_calls"] == 2
    assert summary["total_cost"] == round(inc_cost_1 + inc_cost_2, 6)
    assert "gpt-4o-mini" in summary["cost_by_model"]
    assert "web_search" in summary["cost_by_tool"]

    # Verify event generation from stream
    event1 = await generator.__anext__()
    assert event1.event_type == "telemetry:cost_updated"
    assert event1.data["event"] == "llm_call"

    event2 = await generator.__anext__()
    assert event2.event_type == "telemetry:cost_updated"
    assert event2.data["event"] == "tool_call"

    # Emit telemetry warning and exceeded events
    emit_budget_warning(query_id, {"warning": "80% token limit reached"})
    emit_budget_exceeded(query_id, {"error": "Hard search limit exceeded"})

    event3 = await generator.__anext__()
    assert event3.event_type == "telemetry:budget_warning"

    event4 = await generator.__anext__()
    assert event4.event_type == "telemetry:budget_exceeded"

    # Clean up subscriber
    stream_service.unsubscribe(query_id, sub_id)
