"""Tests for RetryPolicy, with_retry decorator, and HeartbeatMonitor in retry_recovery.py."""

import asyncio
import time
import pytest
from app.services.retry_recovery import RetryPolicy, with_retry, HeartbeatMonitor
from app.services.worker_pool import JobQueueManager
from app.services.checkpoint_engine import CheckpointEngine


def test_retry_policy_delay_calculation():
    policy = RetryPolicy(initial_delay=1.0, backoff_factor=2.0, max_delay=10.0, jitter=False)
    assert policy.calculate_delay(0) == 1.0
    assert policy.calculate_delay(1) == 2.0
    assert policy.calculate_delay(2) == 4.0
    assert policy.calculate_delay(3) == 8.0
    assert policy.calculate_delay(4) == 10.0  # Capped at max_delay


@pytest.mark.asyncio
async def test_retry_policy_execute_async_success():
    attempts = 0

    async def transient_async_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Network glitch")
        return "Success"

    policy = RetryPolicy(max_retries=3, initial_delay=0.01, jitter=False)
    result = await policy.execute_async(transient_async_func)

    assert result == "Success"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_policy_execute_async_exceeded():
    attempts = 0

    async def failing_async_func():
        nonlocal attempts
        attempts += 1
        raise ValueError("Permanent Failure")

    policy = RetryPolicy(max_retries=2, initial_delay=0.01, jitter=False)

    with pytest.raises(ValueError, match="Permanent Failure"):
        await policy.execute_async(failing_async_func)

    assert attempts == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_with_retry_decorator():
    call_count = 0

    @with_retry(max_retries=2, initial_delay=0.01, jitter=False)
    async def decorated_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("Service timeout")
        return "OK"

    res = await decorated_func()
    assert res == "OK"
    assert call_count == 2


@pytest.mark.asyncio
async def test_heartbeat_monitor_crash_detection_and_recovery():
    queue_mgr = JobQueueManager()
    job = await queue_mgr.enqueue_job(run_id="run-crashed-1", priority=5)

    # Mark job running by worker-1
    await queue_mgr.update_job_status(job.job_id, status="running", worker_id="worker-1")

    # Save a checkpoint for this run
    CheckpointEngine.save_checkpoint(
        run_id="run-crashed-1",
        step_name="evidence",
        state={"query_id": "run-crashed-1", "text": "Crashed Run Recovery Test", "claims": [{"id": "c1"}]},
    )

    monitor = HeartbeatMonitor(heartbeat_timeout=0.1, job_queue=queue_mgr)

    # Record worker heartbeat with backdated timestamp
    monitor.record_heartbeat("worker-1", job.job_id)
    # Manually backdate heartbeat
    monitor._worker_heartbeats["worker-1"] = time.time() - 1.0

    # Run check_heartbeats
    crashed_events = await monitor.check_heartbeats(heartbeat_timeout=0.1)

    assert len(crashed_events) == 1
    assert crashed_events[0]["worker_id"] == "worker-1"
    assert crashed_events[0]["job_id"] == job.job_id
    assert crashed_events[0]["recovered"] is True

    # Verify job status reset to queued after recovery
    updated_job = queue_mgr.get_job(job.job_id)
    assert updated_job.status == "queued"
    assert "resumed_state" in updated_job.payload
    assert updated_job.payload["resumed_state"]["run_id"] == "run-crashed-1"


@pytest.mark.asyncio
async def test_heartbeat_monitor_loop_lifecycle():
    monitor = HeartbeatMonitor(heartbeat_timeout=0.2)
    await monitor.start_monitoring(interval=0.05)

    assert monitor.is_monitoring is True
    assert monitor._monitor_task is not None

    monitor.record_heartbeat("worker-active", "job-1")
    await asyncio.sleep(0.1)

    await monitor.stop_monitoring()
    assert monitor.is_monitoring is False
    assert monitor._monitor_task is None
