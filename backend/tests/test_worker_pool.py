"""Tests for AsyncWorkerPool and JobQueueManager in worker_pool.py."""

import asyncio
import pytest
from app.services.worker_pool import JobQueueManager, AsyncWorkerPool, Job


@pytest.mark.asyncio
async def test_job_queue_priority_ordering():
    queue_mgr = JobQueueManager()

    # Enqueue low priority job first, then high priority job
    low_job = await queue_mgr.enqueue_job(run_id="run-low", priority=10, task_type="research_run")
    high_job = await queue_mgr.enqueue_job(run_id="run-high", priority=1, task_type="research_run")
    med_job = await queue_mgr.enqueue_job(run_id="run-med", priority=5, task_type="research_run")

    assert queue_mgr.get_job(low_job.job_id) is not None
    assert queue_mgr.get_job_by_run_id("run-high") == high_job

    # Fetch next job - should be highest priority (priority=1)
    j1 = await queue_mgr.get_next_job(timeout=0.1)
    assert j1.job_id == high_job.job_id

    # Fetch next - priority=5
    j2 = await queue_mgr.get_next_job(timeout=0.1)
    assert j2.job_id == med_job.job_id

    # Fetch next - priority=10
    j3 = await queue_mgr.get_next_job(timeout=0.1)
    assert j3.job_id == low_job.job_id


@pytest.mark.asyncio
async def test_job_queue_status_transitions():
    queue_mgr = JobQueueManager()
    job = await queue_mgr.enqueue_job(run_id="run-status-test", priority=5)

    assert job.status == "queued"
    assert len(queue_mgr.list_jobs(status="queued")) == 1

    # Update to running
    await queue_mgr.update_job_status(job.job_id, status="running", worker_id="worker-1")
    assert job.status == "running"
    assert job.worker_id == "worker-1"
    assert job.started_at is not None

    # Pause job
    paused = await queue_mgr.pause_job(job.job_id)
    assert paused is True
    assert job.status == "paused"

    # Resume job
    resumed = await queue_mgr.resume_job(job.job_id)
    assert resumed is True
    assert job.status == "queued"

    # Fetch job from queue after resume
    next_j = await queue_mgr.get_next_job(timeout=0.1)
    assert next_j.job_id == job.job_id

    # Cancel job
    cancelled = await queue_mgr.cancel_job(job.job_id)
    assert cancelled is True
    assert job.status == "cancelled"
    assert job.completed_at is not None


@pytest.mark.asyncio
async def test_worker_pool_execution():
    queue_mgr = JobQueueManager()
    pool = AsyncWorkerPool(max_concurrency=2, job_queue=queue_mgr)

    executed_jobs = []

    async def mock_research_handler(job: Job):
        await asyncio.sleep(0.05)
        executed_jobs.append(job.job_id)
        return {"summary": f"Completed job {job.job_id}"}

    pool.register_handler("research_run", mock_research_handler)
    await pool.start()

    # Submit 3 jobs
    j1 = await pool.submit_job(run_id="run-1", priority=3)
    j2 = await pool.submit_job(run_id="run-2", priority=1)
    j3 = await pool.submit_job(run_id="run-3", priority=5)

    # Wait for workers to process jobs
    await asyncio.sleep(0.4)

    assert len(executed_jobs) == 3
    # Check completed statuses
    assert queue_mgr.get_job(j1.job_id).status == "completed"
    assert queue_mgr.get_job(j2.job_id).status == "completed"
    assert queue_mgr.get_job(j3.job_id).status == "completed"

    assert queue_mgr.get_job(j1.job_id).result == {"summary": f"Completed job {j1.job_id}"}

    await pool.stop()


@pytest.mark.asyncio
async def test_worker_pool_error_handling():
    queue_mgr = JobQueueManager()
    pool = AsyncWorkerPool(max_concurrency=1, job_queue=queue_mgr)

    async def failing_handler(job: Job):
        raise RuntimeError("Simulated agent failure")

    pool.register_handler("failing_task", failing_handler)
    await pool.start()

    job = await queue_mgr.enqueue_job(run_id="run-err", task_type="failing_task", max_retries=0)

    await asyncio.sleep(0.3)

    assert job.status == "failed"
    assert "Simulated agent failure" in job.error

    await pool.stop()


@pytest.mark.asyncio
async def test_worker_pool_retry_behavior():
    queue_mgr = JobQueueManager()
    pool = AsyncWorkerPool(max_concurrency=1, job_queue=queue_mgr)

    attempts = 0

    async def flaky_handler(job: Job):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("First attempt failure")
        return {"status": "success on retry"}

    pool.register_handler("flaky_task", flaky_handler)
    await pool.start()

    job = await queue_mgr.enqueue_job(run_id="run-retry", task_type="flaky_task", max_retries=1)

    await asyncio.sleep(0.6)

    assert attempts == 2
    assert job.status == "completed"
    assert job.result == {"status": "success on retry"}

    await pool.stop()
