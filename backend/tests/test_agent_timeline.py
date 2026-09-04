"""Unit tests for Agent Timeline Service."""
import pytest
from app.services.agent_timeline_service import agent_timeline_service


def test_agent_timeline_recording():
    run_id = "test_run_timeline_456"
    step1 = agent_timeline_service.record_step_start(
        run_id=run_id, agent_name="research", step_name="web_search", tool_calls=["tavily_search"]
    )
    assert step1["agent_name"] == "research"
    assert step1["status"] == "running"

    completed_step = agent_timeline_service.record_step_complete(
        run_id=run_id, agent_name="research", step_name="web_search", status="completed"
    )
    assert completed_step is not None
    assert completed_step["status"] == "completed"
    assert completed_step["duration_ms"] >= 0.0

    timeline = agent_timeline_service.get_timeline(run_id)
    assert timeline.run_id == run_id
    assert len(timeline.steps) == 1
    assert timeline.steps[0].agent_name == "research"
