"""Tests for step-level checkpointing and resumption in checkpoint_engine.py."""

import pytest
from app.services.checkpoint_engine import (
    CheckpointEngine,
    Checkpoint,
    resume_run_from_checkpoint,
)


@pytest.fixture(autouse=True)
def clear_checkpoints():
    CheckpointEngine.clear()
    yield
    CheckpointEngine.clear()


def test_save_and_get_checkpoints():
    run_id = "test-run-101"
    initial_state = {
        "query_id": run_id,
        "text": "Quantum Computing Market Analysis",
        "steps": [{"id": "step-1", "agent_type": "Supervisor", "message": "Planning complete"}],
        "claims": [{"id": "c-1", "content": "Quantum supremacy demonstrated", "confidence": 0.95}],
        "scored_sources": [{"id": "s-1", "url": "https://quantum.org", "credibility_score": 0.9}],
        "decision_matrix": {"recommendation": "Invest in quantum hardware"},
        "summary": "Quantum computing is rapidly advancing.",
        "confidence": 0.92,
        "current_step": 1,
    }

    cp1 = CheckpointEngine.save_checkpoint(run_id=run_id, step_name="supervisor", state=initial_state)

    assert cp1.checkpoint_id is not None
    assert cp1.run_id == run_id
    assert cp1.step_name == "supervisor"
    assert cp1.step_index == 1
    assert len(cp1.claims) == 1
    assert cp1.agent_outputs["summary"] == "Quantum computing is rapidly advancing."

    # Save second checkpoint
    updated_state = {**initial_state, "current_step": 2, "summary": "Updated research summary."}
    cp2 = CheckpointEngine.save_checkpoint(run_id=run_id, step_name="research", state=updated_state)

    all_cps = CheckpointEngine.get_checkpoints(run_id)
    assert len(all_cps) == 2
    assert CheckpointEngine.get_latest_checkpoint(run_id).checkpoint_id == cp2.checkpoint_id
    assert CheckpointEngine.get_checkpoint_by_id(cp1.checkpoint_id).step_name == "supervisor"


def test_checkpoint_json_serialization():
    cp = Checkpoint(
        checkpoint_id="chk-test-001",
        run_id="run-json-test",
        step_name="evidence",
        step_index=3,
        state={"key": "value", "claims": [{"id": "c1"}]},
        claims=[{"id": "c1", "content": "Sample claim"}],
    )

    json_str = cp.to_json()
    assert isinstance(json_str, str)
    assert "chk-test-001" in json_str

    deserialized_cp = Checkpoint.from_json(json_str)
    assert deserialized_cp.checkpoint_id == cp.checkpoint_id
    assert deserialized_cp.run_id == cp.run_id
    assert deserialized_cp.step_name == cp.step_name
    assert deserialized_cp.claims == cp.claims


def test_resume_run_from_checkpoint_latest():
    run_id = "run-resume-001"
    state_step1 = {
        "query_id": run_id,
        "text": "AI Healthcare Diagnostics",
        "mode": "comprehensive",
        "steps": [{"id": "step-1", "message": "Step 1 complete"}],
        "claims": [{"id": "c-1", "content": "FDA approved AI algorithm"}],
        "scored_sources": [],
        "current_step": 1,
    }
    CheckpointEngine.save_checkpoint(run_id=run_id, step_name="supervisor", state=state_step1)

    state_step2 = {
        **state_step1,
        "steps": state_step1["steps"] + [{"id": "step-2", "message": "Step 2 research complete"}],
        "claims": state_step1["claims"] + [{"id": "c-2", "content": "98% diagnostic accuracy"}],
        "scored_sources": [{"id": "src-1", "url": "https://fda.gov"}],
        "current_step": 2,
    }
    cp2 = CheckpointEngine.save_checkpoint(run_id=run_id, step_name="research", state=state_step2)

    # Resume from latest checkpoint
    restored_state = resume_run_from_checkpoint(run_id=run_id)

    assert restored_state["run_id"] == run_id
    assert restored_state["checkpoint_id"] == cp2.checkpoint_id
    assert restored_state["resumed_from_step"] == "research"
    assert len(restored_state["claims"]) == 2
    assert len(restored_state["steps"]) == 2
    assert restored_state["text"] == "AI Healthcare Diagnostics"


def test_resume_run_from_checkpoint_specific_step():
    run_id = "run-resume-002"
    state1 = {"query_id": run_id, "text": "Test Query", "current_step": 1, "claims": []}
    cp1 = CheckpointEngine.save_checkpoint(run_id=run_id, step_name="supervisor", state=state1)

    state2 = {"query_id": run_id, "text": "Test Query", "current_step": 2, "claims": [{"id": "c1"}]}
    cp2 = CheckpointEngine.save_checkpoint(run_id=run_id, step_name="research", state=state2)

    # Resume specifically from step 1 (supervisor)
    restored1 = resume_run_from_checkpoint(run_id=run_id, checkpoint_id=cp1.checkpoint_id)
    assert restored1["checkpoint_id"] == cp1.checkpoint_id
    assert restored1["resumed_from_step"] == "supervisor"
    assert len(restored1["claims"]) == 0

    # Resume by step_name
    restored_by_name = resume_run_from_checkpoint(run_id=run_id, step_name="supervisor")
    assert restored_by_name["checkpoint_id"] == cp1.checkpoint_id


def test_resume_run_invalid_run_id():
    with pytest.raises(ValueError, match="No valid state checkpoint found"):
        resume_run_from_checkpoint(run_id="non-existent-run-id")
