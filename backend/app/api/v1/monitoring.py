"""REST API endpoints for Phase 12 Continuous Intelligence & Decision Monitoring."""
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user_optional
from app.models.monitoring import AlertStatus, MonitoringExecutionLog
from app.schemas.monitoring import (
    BaselineSnapshotCreate,
    BaselineSnapshotResponse,
    DecisionAlertResponse,
    MonitoringExecutionLogResponse,
    MonitoringJobCreate,
    MonitoringJobResponse,
    MonitoringJobUpdate,
)
from app.services.baseline_delta_service import BaselineDeltaService
from app.services.decision_alerting_service import DecisionAlertingService
from app.services.monitoring_scheduler_service import MonitoringSchedulerService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post(
    "/jobs",
    response_model=MonitoringJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a continuous research/decision monitoring job",
)
async def create_monitoring_job(
    job_in: MonitoringJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    scheduler = MonitoringSchedulerService(db)
    try:
        job = await scheduler.create_job(job_in)
        return job
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create monitoring job: {str(e)}",
        )


@router.get(
    "/jobs",
    response_model=List[MonitoringJobResponse],
    summary="List monitoring jobs by session, project, or status",
)
async def list_monitoring_jobs(
    project_id: Optional[UUID] = Query(None, description="Filter by project UUID"),
    session_id: Optional[UUID] = Query(None, description="Filter by session UUID"),
    job_status: Optional[str] = Query(None, alias="status", description="Filter by job status (ACTIVE, PAUSED, etc.)"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    scheduler = MonitoringSchedulerService(db)
    jobs = await scheduler.list_jobs(
        project_id=project_id, session_id=session_id, status=job_status
    )
    return jobs


@router.get(
    "/jobs/{id}",
    response_model=MonitoringJobResponse,
    summary="Get monitoring job details by ID",
)
async def get_monitoring_job(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    scheduler = MonitoringSchedulerService(db)
    job = await scheduler.get_job(id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring job '{id}' not found.",
        )
    return job


@router.patch(
    "/jobs/{id}",
    response_model=MonitoringJobResponse,
    summary="Update, pause, or resume a monitoring job",
)
async def update_monitoring_job(
    id: UUID,
    job_in: MonitoringJobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    scheduler = MonitoringSchedulerService(db)
    try:
        updated = await scheduler.update_job(id, job_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring job '{id}' not found.",
            )
        return updated
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update monitoring job: {str(e)}",
        )


@router.delete(
    "/jobs/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a monitoring job",
)
async def delete_monitoring_job(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    scheduler = MonitoringSchedulerService(db)
    deleted = await scheduler.delete_job(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring job '{id}' not found.",
        )
    return None


@router.post(
    "/jobs/{id}/run",
    response_model=MonitoringExecutionLogResponse,
    summary="Trigger a manual run for a monitoring job",
)
async def trigger_monitoring_job_run(
    id: UUID,
    payload: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    scheduler = MonitoringSchedulerService(db)
    job = await scheduler.get_job(id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring job '{id}' not found.",
        )

    current_state = payload.get("current_state") if payload else payload
    try:
        log = await scheduler.trigger_job_now(id, current_state=current_state)
        return log
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute monitoring job run: {str(e)}",
        )


@router.get(
    "/jobs/{id}/logs",
    response_model=List[MonitoringExecutionLogResponse],
    summary="Get execution logs for a monitoring job",
)
async def get_monitoring_job_logs(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    scheduler = MonitoringSchedulerService(db)
    job = await scheduler.get_job(id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring job '{id}' not found.",
        )

    result = await db.execute(
        select(MonitoringExecutionLog)
        .where(MonitoringExecutionLog.job_id == id)
        .order_by(MonitoringExecutionLog.executed_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/baselines",
    response_model=BaselineSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a research baseline snapshot",
)
async def create_baseline_snapshot(
    snap_in: BaselineSnapshotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = BaselineDeltaService(db)
    try:
        snapshot = await service.create_baseline_snapshot(snap_in)
        return snapshot
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create baseline snapshot: {str(e)}",
        )


@router.get(
    "/baselines/{id}",
    response_model=BaselineSnapshotResponse,
    summary="Get research baseline snapshot by ID",
)
async def get_baseline_snapshot(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = BaselineDeltaService(db)
    snapshot = await service.get_baseline_snapshot(id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline snapshot '{id}' not found.",
        )
    return snapshot


@router.get(
    "/alerts",
    response_model=List[DecisionAlertResponse],
    summary="List decision alerts",
)
async def list_decision_alerts(
    job_id: Optional[UUID] = Query(None, description="Filter by monitoring job UUID"),
    project_id: Optional[UUID] = Query(None, description="Filter by project UUID"),
    session_id: Optional[UUID] = Query(None, description="Filter by session UUID"),
    alert_status: Optional[str] = Query(None, alias="status", description="Filter by alert status (UNREAD, ACKNOWLEDGED, RESOLVED)"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = DecisionAlertingService(db)
    alerts = await service.list_alerts(
        job_id=job_id,
        project_id=project_id,
        session_id=session_id,
        status=alert_status,
        severity=severity,
    )
    return alerts


@router.post(
    "/alerts/{id}/acknowledge",
    response_model=DecisionAlertResponse,
    summary="Acknowledge a decision alert",
)
async def acknowledge_decision_alert(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
):
    service = DecisionAlertingService(db)
    updated = await service.update_alert_status(id, AlertStatus.ACKNOWLEDGED.value)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision alert '{id}' not found.",
        )
    return updated

