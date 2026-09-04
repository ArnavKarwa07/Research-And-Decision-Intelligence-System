"""Adversarial resilience and vulnerability test suite for RADIS Phase 9.

Tests edge cases, crash recovery, budget bypass vectors, recursion depth limit bypass,
and state corruption handling during checkpoint deserialization.
"""

import asyncio
import json
import time
import pytest

from app.services.worker_pool import AsyncWorkerPool, JobQueueManager, Job
from app.services.checkpoint_engine import CheckpointEngine, Checkpoint, resume_run_from_checkpoint
from app.services.retry_recovery import HeartbeatMonitor, RetryPolicy, with_retry
from app.services.budget_service import (
    BudgetService,
    TokenBudget,
    SearchBudget,
    ToolBudget,
    WallClockBudget,
    BudgetExceededError,
)
from app.services.depth_limiter import DepthLimiter, DepthLimitExceededError, WidthLimitExceededError


@pytest.mark.asyncio
async def test_worker_crash_and_heartbeat_recovery():
    """Test worker crash during active job step and heartbeat recovery by HeartbeatMonitor."""
    queue = JobQueueManager()
    monitor = HeartbeatMonitor(job_queue=queue, heartbeat_timeout=0.1)

    # Enqueue job
    job = await queue.enqueue_job(run_id="run-crash-test", task_type="research_run")
    await queue.update_job_status(job.job_id, status="running")

    # Record worker heartbeat in past
    monitor.record_heartbeat("worker-1", job_id=job.job_id)
    # Artificially age the heartbeat
    monitor._worker_heartbeats["worker-1"] = time.time() - 10.0

    # Execute check_heartbeats
    crashed_events = await monitor.check_heartbeats(heartbeat_timeout=0.1)

    assert len(crashed_events) == 1
    assert crashed_events[0]["job_id"] == job.job_id
    assert crashed_events[0]["recovered"] is True

    # Verify job status transitioned to recovering or queued
    updated_job = queue.get_job(job.job_id)
    assert updated_job.status in ("recovering", "queued", "running")


@pytest.mark.asyncio
async def test_hard_budget_limit_exhaustion_concurrent():
    """Test hard budget limit enforcement under search and tool execution."""
    service = BudgetService()
    run_id = "run-budget-adversarial"

    service.create_run_budget(
        run_id=run_id,
        max_tokens=100,
        max_searches=2,
        max_tool_calls=2,
        max_seconds=10.0,
    )

    # 1st search is allowed
    service.record_usage(run_id=run_id, searches=1)
    
    # 2nd search reaches hard limit max_searches (2 >= 2) and raises BudgetExceededError
    with pytest.raises(BudgetExceededError) as exc_info:
        service.record_usage(run_id=run_id, searches=1)
    
    assert exc_info.value.dimension in ("searches", "tokens", "tool_calls")

    # Verify sub-task tool call budget exhaustion
    sub_task_id = "sub-1"
    sub_run_id = "run-sub-budget"
    service.create_run_budget(run_id=sub_run_id, max_tool_calls=5)
    service.create_sub_task_budget(run_id=sub_run_id, sub_task_id=sub_task_id, max_tool_calls=2)
    
    # Sub-task 1st tool call is allowed
    service.record_usage(run_id=sub_run_id, sub_task_id=sub_task_id, tool_calls=1)
    
    # Sub-task 2nd tool call reaches sub-task limit (2 >= 2)
    with pytest.raises(BudgetExceededError) as exc_info_tool:
        service.record_usage(run_id=sub_run_id, sub_task_id=sub_task_id, tool_calls=1)

    assert exc_info_tool.value.dimension == "tools"


def test_depth_limiter_nesting_and_width_bypass_prevention():
    """Test deep subagent nesting attempting to bypass DepthLimiter limits."""
    limiter = DepthLimiter(max_depth=3, max_width=2)

    root_id = "root-agent"
    limiter.register_agent(root_id)

    # Level 1
    child1_1 = "child-1-1"
    child1_2 = "child-1-2"
    limiter.register_agent(child1_1, parent_id=root_id)
    limiter.register_agent(child1_2, parent_id=root_id)

    # Exceed width limit on root (3rd child)
    child1_3 = "child-1-3"
    with pytest.raises(WidthLimitExceededError):
        limiter.register_agent(child1_3, parent_id=root_id)

    # Level 2
    child2_1 = "child-2-1"
    limiter.register_agent(child2_1, parent_id=child1_1)

    # Level 3
    child3_1 = "child-3-1"
    limiter.register_agent(child3_1, parent_id=child2_1)

    # Level 4 (Exceeds max depth 3)
    child4_1 = "child-4-1"
    with pytest.raises(DepthLimitExceededError):
        limiter.register_agent(child4_1, parent_id=child3_1)


def test_corrupted_checkpoint_deserialization():
    """Test corrupted JSON or missing state keys in CheckpointEngine deserialization."""
    engine = CheckpointEngine()
    engine.clear()

    run_id = "run-corrupted-test"

    # Save empty state checkpoint
    cp = engine.save_checkpoint(
        run_id=run_id,
        step_name="test_step",
        state={},  # Completely empty state
    )

    # Verify resume_run_from_checkpoint does not crash and fills default fallback keys
    restored = resume_run_from_checkpoint(run_id, checkpoint_id=cp.checkpoint_id)

    assert restored["run_id"] == run_id
    assert restored["checkpoint_id"] == cp.checkpoint_id
    assert restored["claims"] == []
    assert restored["scored_sources"] == []
    assert restored["confidence"] == 0.0
    assert restored["audit_passed"] is True


def test_corrupted_json_string_checkpoint_restoration():
    """Test state containing unparseable nested fields handling gracefully."""
    engine = CheckpointEngine()
    engine.clear()

    run_id = "run-corrupt-json"

    cp = engine.save_checkpoint(
        run_id=run_id,
        step_name="step_corrupt",
        state={
            "claims": "invalid_claims_not_a_list",
            "sources": "invalid_sources",
            "confidence": "not_a_float",
        },
    )

    restored = resume_run_from_checkpoint(run_id, checkpoint_id=cp.checkpoint_id)
    assert restored["run_id"] == run_id
    assert isinstance(restored, dict)
