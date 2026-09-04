"""Monitoring Scheduler Service for Phase 12 Continuous Intelligence."""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import (
    ExecutionLogStatus,
    MonitoringExecutionLog,
    MonitoringJob,
    MonitoringJobStatus,
    ScheduleType,
)
from app.schemas.monitoring import MonitoringJobCreate, MonitoringJobUpdate
from app.services.baseline_delta_service import BaselineDeltaService
from app.services.decision_alerting_service import DecisionAlertingService
from app.services.materiality_scoring_engine import MaterialityScoringEngine

logger = logging.getLogger(__name__)


def _validate_cron_field(pattern: str, min_bound: int, max_bound: int, field_name: str) -> None:
    """Validate bounds and step sizes for a single cron field pattern."""
    if pattern == "*":
        return

    for part in pattern.split(","):
        if "/" in part:
            sub, step_str = part.split("/", 1)
            try:
                step = int(step_str)
            except ValueError:
                raise ValueError(f"Invalid step '{step_str}' in cron field '{field_name}'.")
            if step <= 0:
                raise ValueError(f"Cron step must be greater than 0, got {step} in field '{field_name}'.")

            if sub != "*":
                if "-" in sub:
                    start, end = map(int, sub.split("-"))
                    if start < min_bound or end > max_bound or start > end:
                        raise ValueError(
                            f"Range {start}-{end} out of bounds [{min_bound}, {max_bound}] in cron field '{field_name}'."
                        )
                elif sub.isdigit():
                    val = int(sub)
                    if val < min_bound or val > max_bound:
                        raise ValueError(
                            f"Value {val} out of bounds [{min_bound}, {max_bound}] in cron field '{field_name}'."
                        )
        elif "-" in part:
            start, end = map(int, part.split("-"))
            if start < min_bound or end > max_bound or start > end:
                raise ValueError(
                    f"Range {start}-{end} out of bounds [{min_bound}, {max_bound}] in cron field '{field_name}'."
                )
        elif part.isdigit():
            val = int(part)
            if val < min_bound or val > max_bound:
                raise ValueError(
                    f"Value {val} out of bounds [{min_bound}, {max_bound}] in cron field '{field_name}'."
                )


def _match_cron_field(value: int, pattern: str, min_val: int) -> bool:
    """Helper to check if integer value matches a cron field pattern (*, */N, A-B, A,B)."""
    if pattern == "*":
        return True
    for part in pattern.split(","):
        if "/" in part:
            sub, step_str = part.split("/", 1)
            step = int(step_str)
            if step <= 0:
                raise ValueError(f"Cron step must be greater than 0, got {step}.")
            if sub == "*":
                if (value - min_val) % step == 0:
                    return True
            elif "-" in sub:
                start, end = map(int, sub.split("-"))
                if start <= value <= end and (value - start) % step == 0:
                    return True
            elif sub.isdigit():
                val = int(sub)
                if value == val:
                    return True
        elif "-" in part:
            start, end = map(int, part.split("-"))
            if start <= value <= end:
                return True
        elif part.isdigit():
            if value == int(part):
                return True
    return False


def calculate_next_cron_time(cron_expr: str, base_time: Optional[datetime] = None) -> datetime:
    """
    Parse standard 5-field cron expression (minute hour day_of_month month day_of_week)
    and calculate next run datetime strictly after base_time.
    """
    if not base_time:
        base_time = datetime.now(timezone.utc)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)

    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression '{cron_expr}'. Must have 5 fields.")

    min_pat, hour_pat, dom_pat, month_pat, dow_pat = parts

    # Validate boundaries (minute 0-59, hour 0-23, day 1-31, month 1-12, dow 0-7)
    _validate_cron_field(min_pat, 0, 59, "minute")
    _validate_cron_field(hour_pat, 0, 23, "hour")
    _validate_cron_field(dom_pat, 1, 31, "day_of_month")
    _validate_cron_field(month_pat, 1, 12, "month")
    _validate_cron_field(dow_pat, 0, 7, "day_of_week")

    # Step minute by minute starting from 1 minute after base_time
    curr = base_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
    max_steps = 525600  # 1 year in minutes

    for _ in range(max_steps):
        # Day of week in cron: 0=Sun or 7=Sun. In python: weekday() 0=Mon...6=Sun.
        python_dow = curr.weekday()
        cron_dow = 0 if python_dow == 6 else python_dow + 1

        if (
            _match_cron_field(curr.minute, min_pat, 0)
            and _match_cron_field(curr.hour, hour_pat, 0)
            and _match_cron_field(curr.day, dom_pat, 1)
            and _match_cron_field(curr.month, month_pat, 1)
            and (
                _match_cron_field(cron_dow, dow_pat, 0)
                or _match_cron_field(0 if cron_dow == 7 else cron_dow, dow_pat, 0)
            )
        ):
            return curr

        curr += timedelta(minutes=1)

    raise ValueError(f"Could not calculate next run for cron expression '{cron_expr}'.")


def calculate_next_run_at(
    schedule_type: str,
    cron_expression: Optional[str] = None,
    interval_seconds: Optional[int] = None,
    base_time: Optional[datetime] = None,
) -> Optional[datetime]:
    """
    Calculate next_run_at datetime based on schedule type (CRON, INTERVAL, EVENT_DRIVEN).
    """
    if not base_time:
        base_time = datetime.now(timezone.utc)
    elif base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)

    if schedule_type == ScheduleType.INTERVAL.value:
        sec = interval_seconds if (interval_seconds and interval_seconds >= 10) else 3600
        return base_time + timedelta(seconds=sec)
    elif schedule_type == ScheduleType.CRON.value:
        if not cron_expression:
            raise ValueError("cron_expression is required for CRON schedule_type.")
        return calculate_next_cron_time(cron_expression, base_time)
    elif schedule_type == ScheduleType.EVENT_DRIVEN.value:
        return None
    else:
        sec = interval_seconds if (interval_seconds and interval_seconds >= 10) else 3600
        return base_time + timedelta(seconds=sec)


class MonitoringSchedulerService:
    """
    Service managing recurring research monitoring jobs, cron/interval schedule calculations,
    pause/resume status transitions, manual job triggers, and async worker executions.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.delta_service = BaselineDeltaService(db)
        self.alert_service = DecisionAlertingService(db)

    async def create_job(self, job_in: MonitoringJobCreate) -> MonitoringJob:
        """Create and schedule a new MonitoringJob."""
        next_run = calculate_next_run_at(
            schedule_type=job_in.schedule_type,
            cron_expression=job_in.cron_expression,
            interval_seconds=job_in.interval_seconds,
        )

        job = MonitoringJob(
            project_id=job_in.project_id,
            session_id=job_in.session_id,
            query_id=job_in.query_id,
            baseline_snapshot_id=job_in.baseline_snapshot_id,
            name=job_in.name,
            schedule_type=job_in.schedule_type,
            cron_expression=job_in.cron_expression,
            interval_seconds=job_in.interval_seconds,
            status=MonitoringJobStatus.ACTIVE.value,
            alert_threshold=job_in.alert_threshold,
            webhook_url=job_in.webhook_url,
            next_run_at=next_run,
            metadata_=job_in.metadata or {},
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: UUID) -> Optional[MonitoringJob]:
        """Fetch job by ID."""
        result = await self.db.execute(select(MonitoringJob).where(MonitoringJob.id == job_id))
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        project_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        status: Optional[str] = None,
    ) -> List[MonitoringJob]:
        """List monitoring jobs with optional filtering."""
        stmt = select(MonitoringJob)
        if project_id:
            stmt = stmt.where(MonitoringJob.project_id == project_id)
        if session_id:
            stmt = stmt.where(MonitoringJob.session_id == session_id)
        if status:
            stmt = stmt.where(MonitoringJob.status == status)

        stmt = stmt.order_by(MonitoringJob.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_job(self, job_id: UUID, job_in: MonitoringJobUpdate) -> Optional[MonitoringJob]:
        """Update an existing monitoring job and recalculate next_run_at if schedule changed."""
        job = await self.get_job(job_id)
        if not job:
            return None

        if job_in.name is not None:
            job.name = job_in.name
        if job_in.alert_threshold is not None:
            job.alert_threshold = job_in.alert_threshold
        if job_in.webhook_url is not None:
            job.webhook_url = job_in.webhook_url
        if job_in.metadata is not None:
            job.metadata_ = job_in.metadata

        schedule_changed = False
        if job_in.schedule_type is not None and job_in.schedule_type != job.schedule_type:
            job.schedule_type = job_in.schedule_type
            schedule_changed = True
        if job_in.cron_expression is not None:
            job.cron_expression = job_in.cron_expression
            schedule_changed = True
        if job_in.interval_seconds is not None:
            job.interval_seconds = job_in.interval_seconds
            schedule_changed = True

        if job_in.status is not None:
            job.status = job_in.status
            if job.status == MonitoringJobStatus.PAUSED.value:
                job.next_run_at = None

        if schedule_changed and job.status == MonitoringJobStatus.ACTIVE.value:
            job.next_run_at = calculate_next_run_at(
                schedule_type=job.schedule_type,
                cron_expression=job.cron_expression,
                interval_seconds=job.interval_seconds,
            )

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def pause_job(self, job_id: UUID) -> Optional[MonitoringJob]:
        """Pause a monitoring job."""
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = MonitoringJobStatus.PAUSED.value
        job.next_run_at = None
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def resume_job(self, job_id: UUID) -> Optional[MonitoringJob]:
        """Resume a paused monitoring job and recalculate next_run_at."""
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = MonitoringJobStatus.ACTIVE.value
        job.next_run_at = calculate_next_run_at(
            schedule_type=job.schedule_type,
            cron_expression=job.cron_expression,
            interval_seconds=job.interval_seconds,
        )
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def delete_job(self, job_id: UUID) -> bool:
        """Delete a monitoring job."""
        job = await self.get_job(job_id)
        if not job:
            return False

        await self.db.delete(job)
        await self.db.commit()
        return True

    async def trigger_job_now(
        self, job_id: UUID, current_state: Optional[Dict[str, Any]] = None
    ) -> MonitoringExecutionLog:
        """Manually trigger immediate execution of a monitoring job."""
        return await self.execute_job(job_id=job_id, current_state=current_state)

    async def execute_job(
        self, job_id: UUID, current_state: Optional[Dict[str, Any]] = None
    ) -> MonitoringExecutionLog:
        """
        Execute worker logic for a monitoring job:
        1. Compares baseline snapshot against current_state.
        2. Computes materiality score M via MaterialityScoringEngine.
        3. Generates DecisionAlert if M >= job.alert_threshold.
        4. Logs execution and updates job timestamps.
        """
        start_time = datetime.now(timezone.utc)
        start_ticks = time.perf_counter()

        job = await self.get_job(job_id)
        if not job:
            raise ValueError(f"MonitoringJob '{job_id}' not found.")

        snapshot = None
        if job.baseline_snapshot_id:
            snapshot = await self.delta_service.get_baseline_snapshot(job.baseline_snapshot_id)

        try:
            if not current_state:
                current_state = {}

            if snapshot:
                delta_res = self.delta_service.compute_delta(baseline=snapshot, current_state=current_state)
            else:
                # Fallback if no baseline snapshot exists
                delta_res = {
                    "sub_scores": current_state.get("sub_scores", {"s_assumption": 0.0, "s_contradiction": 0.0, "s_matrix": 0.0, "s_source": 0.0}),
                    "diffs": current_state.get("diffs", {}),
                    "recommendation_flipped": current_state.get("recommendation_flipped", False),
                    "summary": "No baseline snapshot attached.",
                }

            breakdown = MaterialityScoringEngine.score_delta_result(delta_res)
            alert_triggered = breakdown.total_score >= job.alert_threshold

            log_status = (
                ExecutionLogStatus.ALERT_TRIGGERED.value
                if alert_triggered
                else (
                    ExecutionLogStatus.SUCCESS.value
                    if breakdown.total_score > 0
                    else ExecutionLogStatus.NO_CHANGE.value
                )
            )

            duration = round(time.perf_counter() - start_ticks, 4)

            execution_log = MonitoringExecutionLog(
                job_id=job.id,
                new_query_id=current_state.get("new_query_id"),
                status=log_status,
                materiality_score=breakdown.total_score,
                materiality_level=breakdown.materiality_level,
                delta_summary={
                    "breakdown": breakdown.model_dump(),
                    "delta_result": delta_res,
                },
                alert_triggered=alert_triggered,
                execution_duration_seconds=duration,
            )
            self.db.add(execution_log)
            await self.db.commit()
            await self.db.refresh(execution_log)

            if alert_triggered:
                await self.alert_service.evaluate_and_create_alert(
                    job_id=job.id,
                    execution_log_id=execution_log.id,
                    materiality_score=breakdown.total_score,
                    threshold=job.alert_threshold,
                    delta_summary=delta_res,
                    project_id=job.project_id,
                    session_id=job.session_id,
                    webhook_url=job.webhook_url,
                )

            job.last_run_at = start_time
            job.run_count += 1
            if job.status == MonitoringJobStatus.ACTIVE.value and job.schedule_type != ScheduleType.EVENT_DRIVEN.value:
                job.next_run_at = calculate_next_run_at(
                    schedule_type=job.schedule_type,
                    cron_expression=job.cron_expression,
                    interval_seconds=job.interval_seconds,
                    base_time=start_time,
                )

            await self.db.commit()
            await self.db.refresh(execution_log)
            return execution_log

        except Exception as exc:
            duration = round(time.perf_counter() - start_ticks, 4)
            err_log = MonitoringExecutionLog(
                job_id=job.id,
                status=ExecutionLogStatus.FAILED.value,
                materiality_score=0.0,
                materiality_level="NEGLIGIBLE",
                delta_summary={"error": str(exc)},
                alert_triggered=False,
                execution_duration_seconds=duration,
                error_message=str(exc),
            )
            self.db.add(err_log)
            job.last_run_at = start_time
            await self.db.commit()
            await self.db.refresh(err_log)
            return err_log

    async def run_due_jobs(self) -> List[MonitoringExecutionLog]:
        """Query all ACTIVE jobs with next_run_at <= current_time and execute them."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(MonitoringJob)
            .where(MonitoringJob.status == MonitoringJobStatus.ACTIVE.value)
            .where(MonitoringJob.next_run_at <= now)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        due_jobs = result.scalars().all()

        logs: List[MonitoringExecutionLog] = []
        for j in due_jobs:
            log_item = await self.execute_job(j.id)
            logs.append(log_item)

        return logs
