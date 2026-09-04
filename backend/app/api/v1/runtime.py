"""Runtime API Endpoints for execution control (pause/resume), state checkpointing, and budget monitoring."""

from fastapi import APIRouter, HTTPException, status
from typing import Any, Dict, List
import logging

from app.services.worker_pool import global_worker_pool
from app.services.checkpoint_engine import CheckpointEngine
from app.services.budget_service import budget_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime/runs", tags=["runtime"])
direct_runs_router = APIRouter(prefix="/runs", tags=["runtime"])


@router.post("/{run_id}/pause", status_code=status.HTTP_200_OK)
@direct_runs_router.post("/{run_id}/pause", status_code=status.HTTP_200_OK)
async def pause_run(run_id: str) -> Dict[str, Any]:
    """Pause an active research run."""
    job = global_worker_pool.job_queue.get_job_by_run_id(run_id)
    if not job:
        job = global_worker_pool.job_queue.get_job(run_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )

    success = await global_worker_pool.job_queue.pause_job(job.job_id)
    if not success and job.status not in ["paused"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run '{run_id}' cannot be paused (current status: {job.status})."
        )

    return {
        "run_id": run_id,
        "job_id": job.job_id,
        "status": "paused",
        "message": f"Run '{run_id}' successfully paused."
    }


@router.post("/{run_id}/resume", status_code=status.HTTP_200_OK)
@direct_runs_router.post("/{run_id}/resume", status_code=status.HTTP_200_OK)
async def resume_run(run_id: str) -> Dict[str, Any]:
    """Resume a paused research run."""
    job = global_worker_pool.job_queue.get_job_by_run_id(run_id)
    if not job:
        job = global_worker_pool.job_queue.get_job(run_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found."
        )

    success = await global_worker_pool.job_queue.resume_job(job.job_id)
    if not success and job.status not in ["queued", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run '{run_id}' cannot be resumed (current status: {job.status})."
        )

    latest_cp = CheckpointEngine.get_latest_checkpoint(run_id)
    latest_cp_id = latest_cp.checkpoint_id if latest_cp else None

    return {
        "run_id": run_id,
        "job_id": job.job_id,
        "status": "queued",
        "latest_checkpoint_id": latest_cp_id,
        "message": f"Run '{run_id}' successfully resumed."
    }


@router.get("/{run_id}/checkpoints", status_code=status.HTTP_200_OK)
@direct_runs_router.get("/{run_id}/checkpoints", status_code=status.HTTP_200_OK)
async def get_run_checkpoints(run_id: str) -> Dict[str, Any]:
    """Retrieve all step-level execution checkpoints for a research run."""
    checkpoints = CheckpointEngine.get_checkpoints(run_id)
    return {
        "run_id": run_id,
        "count": len(checkpoints),
        "checkpoints": [cp.to_dict() for cp in checkpoints]
    }


@router.get("/{run_id}/budget", status_code=status.HTTP_200_OK)
@direct_runs_router.get("/{run_id}/budget", status_code=status.HTTP_200_OK)
async def get_run_budget(run_id: str) -> Dict[str, Any]:
    """Retrieve multi-dimension budget tracking statistics for a run."""
    budget = budget_service.get_run_budget(run_id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget records not found for run '{run_id}'."
        )

    hard_exceeded, hard_reason, soft_warnings = budget.check_limits()
    return {
        "run_id": run_id,
        "hard_limit_exceeded": hard_exceeded,
        "hard_limit_reason": hard_reason,
        "soft_warnings": soft_warnings,
        "budget_stats": budget.get_summary()
    }
