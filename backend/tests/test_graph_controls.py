"""Tests for graph execution controls (pause/resume/cancel) and step checkpoint callbacks in graph.py."""

import pytest

from app.agents.graph import (
    AgentState,
    ExecutionControl,
    JobCancelledError,
    JobPausedError,
    check_execution_and_checkpoint,
)
from app.services.checkpoint_engine import CheckpointEngine, resume_run_from_checkpoint


@pytest.fixture(autouse=True)
def clear_state():
    ExecutionControl.clear()
    CheckpointEngine.clear()
    yield
    ExecutionControl.clear()
    CheckpointEngine.clear()


def test_graph_step_checkpointing():
    run_id = "run-graph-chk-001"
    initial_state: AgentState = {
        "query_id": run_id,
        "text": "Graph Checkpoint Test Query",
        "mode": "comprehensive",
        "plan": ["Analyze topic"],
        "steps": ["Plan created"],
        "snippets": [],
        "chunks": [],
        "claims": [],
        "scored_sources": [],
        "claim_source_links": [],
        "contradictions": [],
        "source_groups": [],
        "stale_source_ids": [],
        "fact_check_results": [],
        "verification_loop_count": 0,
        "decision_matrix": None,
        "data_analysis_results": None,
        "visualization_spec": None,
        "search_queries": [],
        "summary": "Completed research",
        "confidence": 0.9,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 1,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": True,
        "current_step": 1,
        "run_id": run_id,
        "is_paused": None,
        "is_cancelled": None,
        "pause_requested": None,
        "cancel_requested": None,
        "active_checkpoint_id": None,
    }

    # Save a checkpoint directly to test state restoration
    cp = CheckpointEngine.save_checkpoint(
        run_id=run_id,
        step_name="supervisor",
        state=initial_state,
    )
    assert cp is not None

    # Checkpoints were saved
    checkpoints = CheckpointEngine.get_checkpoints(run_id)
    assert len(checkpoints) == 1

    # Resume state from checkpoint
    restored = resume_run_from_checkpoint(run_id)
    assert restored["run_id"] == run_id
    assert restored["text"] == "Graph Checkpoint Test Query"


def test_graph_cancel_control():
    run_id = "run-graph-cancel-001"
    initial_state: AgentState = {
        "query_id": run_id,
        "text": "Cancelled Run Query",
        "mode": "comprehensive",
        "plan": [],
        "steps": [],
        "snippets": [],
        "chunks": [],
        "claims": [],
        "scored_sources": [],
        "claim_source_links": [],
        "contradictions": [],
        "source_groups": [],
        "stale_source_ids": [],
        "fact_check_results": [],
        "verification_loop_count": 0,
        "decision_matrix": None,
        "data_analysis_results": None,
        "visualization_spec": None,
        "search_queries": [],
        "summary": "",
        "confidence": 0.0,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 1,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0,
        "run_id": run_id,
        "is_paused": None,
        "is_cancelled": None,
        "pause_requested": None,
        "cancel_requested": None,
        "active_checkpoint_id": None,
    }

    # Request cancellation before graph node execution
    ExecutionControl.request_cancel(run_id)

    delta = {}
    with pytest.raises(JobCancelledError, match="cancelled"):
        check_execution_and_checkpoint("supervisor", initial_state, delta)


def test_graph_pause_control():
    run_id = "run-graph-pause-001"
    initial_state: AgentState = {
        "query_id": run_id,
        "text": "Paused Run Query",
        "mode": "comprehensive",
        "plan": [],
        "steps": [],
        "snippets": [],
        "chunks": [],
        "claims": [],
        "scored_sources": [],
        "claim_source_links": [],
        "contradictions": [],
        "source_groups": [],
        "stale_source_ids": [],
        "fact_check_results": [],
        "verification_loop_count": 0,
        "decision_matrix": None,
        "data_analysis_results": None,
        "visualization_spec": None,
        "search_queries": [],
        "summary": "",
        "confidence": 0.0,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 1,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0,
        "run_id": run_id,
        "is_paused": None,
        "is_cancelled": None,
        "pause_requested": None,
        "cancel_requested": None,
        "active_checkpoint_id": None,
    }

    # Request pause before graph node execution
    ExecutionControl.request_pause(run_id)

    delta = {}
    with pytest.raises(JobPausedError, match="paused"):
        check_execution_and_checkpoint("supervisor", initial_state, delta)

    # Checkpoint was saved upon pausing
    checkpoints = CheckpointEngine.get_checkpoints(run_id)
    assert len(checkpoints) == 1
    assert checkpoints[0].step_name == "supervisor"
