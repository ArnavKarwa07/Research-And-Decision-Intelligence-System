"""Integration and unit tests for Runtime API endpoints."""

import asyncio
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.worker_pool import global_worker_pool
from app.services.checkpoint_engine import CheckpointEngine
from app.services.budget_service import budget_service


@pytest.fixture(autouse=True)
def cleanup_runtime_state():
    """Ensure clean global state before and after each test."""
    global_worker_pool.job_queue.clear()
    CheckpointEngine.clear()
    yield
    global_worker_pool.job_queue.clear()
    CheckpointEngine.clear()


@pytest.mark.asyncio
async def test_pause_run_success():
    client = TestClient(app)
    run_id = "run-test-pause-123"

    # Enqueue a job into queue manager
    await global_worker_pool.job_queue.enqueue_job(run_id=run_id)

    res = client.post(f"/api/v1/runtime/runs/{run_id}/pause")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run_id
    assert data["status"] == "paused"

    # Check job status in queue manager
    job = global_worker_pool.job_queue.get_job_by_run_id(run_id)
    assert job is not None
    assert job.status == "paused"


def test_pause_run_not_found():
    client = TestClient(app)
    res = client.post("/api/v1/runtime/runs/nonexistent-run-id/pause")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resume_run_success():
    client = TestClient(app)
    run_id = "run-test-resume-456"

    # Enqueue and pause job
    job = await global_worker_pool.job_queue.enqueue_job(run_id=run_id)
    await global_worker_pool.job_queue.pause_job(job.job_id)

    res = client.post(f"/api/v1/runtime/runs/{run_id}/resume")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run_id
    assert data["status"] == "queued"

    latest_job = global_worker_pool.job_queue.get_job_by_run_id(run_id)
    assert latest_job is not None
    assert latest_job.status == "queued"


def test_resume_run_not_found():
    client = TestClient(app)
    res = client.post("/api/v1/runtime/runs/nonexistent-run-id/resume")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_checkpoints():
    client = TestClient(app)
    run_id = "run-test-checkpoints-789"

    CheckpointEngine.save_checkpoint(run_id=run_id, step_name="supervisor_step", state={"text": "query 1"})
    CheckpointEngine.save_checkpoint(run_id=run_id, step_name="research_step", state={"text": "query 1", "snippets": []})

    res = client.get(f"/api/v1/runtime/runs/{run_id}/checkpoints")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run_id
    assert data["count"] == 2
    assert len(data["checkpoints"]) == 2
    assert data["checkpoints"][0]["step_name"] == "supervisor_step"
    assert data["checkpoints"][1]["step_name"] == "research_step"


def test_get_budget():
    client = TestClient(app)
    run_id = "run-test-budget-101"

    budget_service.create_run_budget(run_id=run_id, max_tokens=5000, max_searches=10)
    budget_service.record_usage(run_id=run_id, prompt_tokens=1000, completion_tokens=500, searches=2)

    res = client.get(f"/api/v1/runtime/runs/{run_id}/budget")
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == run_id
    assert data["hard_limit_exceeded"] is False
    assert data["budget_stats"]["tokens"]["total"] == 1500
    assert data["budget_stats"]["searches"]["conducted"] == 2


def test_get_budget_not_found():
    client = TestClient(app)
    res = client.get("/api/v1/runtime/runs/nonexistent-budget-id/budget")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_direct_api_runs_endpoints():
    """Verify alias paths under /api/runs/{id}/... also work."""
    client = TestClient(app)
    run_id = "run-test-direct-999"

    await global_worker_pool.job_queue.enqueue_job(run_id=run_id)
    budget_service.create_run_budget(run_id=run_id, max_tokens=1000)

    # Pause
    res = client.post(f"/api/runs/{run_id}/pause")
    assert res.status_code == 200

    # Resume
    res = client.post(f"/api/runs/{run_id}/resume")
    assert res.status_code == 200

    # Checkpoints
    res = client.get(f"/api/runs/{run_id}/checkpoints")
    assert res.status_code == 200

    # Budget
    res = client.get(f"/api/runs/{run_id}/budget")
    assert res.status_code == 200
