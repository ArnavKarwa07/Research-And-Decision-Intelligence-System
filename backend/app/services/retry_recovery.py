"""Retry Policy and Heartbeat Monitor for RADIS Phase 9 Long-Running Jobs.

Provides exponential backoff retry policies for transient agent/tool errors,
and HeartbeatMonitor to track worker liveness and auto-recover crashed jobs.
"""

import asyncio
from datetime import datetime, timezone
import functools
import logging
import random
import time
from typing import Dict, List, Any, Optional, Callable, Type, Tuple, Union, Awaitable

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Exponential backoff retry policy for transient errors."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.5,
        backoff_factor: float = 2.0,
        max_delay: float = 10.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with optional random jitter."""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        if self.jitter:
            delay += random.uniform(0, 0.1 * delay)
        return min(delay, self.max_delay)

    async def execute_async(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute async function with retry policy."""
        attempt = 0
        while True:
            try:
                return await func(*args, **kwargs)
            except self.retryable_exceptions as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(f"[RetryPolicy] Exceeded max retries ({self.max_retries}). Raising error: {exc}")
                    raise exc

                delay = self.calculate_delay(attempt - 1)
                logger.warning(
                    f"[RetryPolicy] Transient failure: {exc}. Retrying attempt {attempt}/{self.max_retries} in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)

    def execute_sync(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute synchronous function with retry policy."""
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except self.retryable_exceptions as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(f"[RetryPolicy] Exceeded max retries ({self.max_retries}). Raising error: {exc}")
                    raise exc

                delay = self.calculate_delay(attempt - 1)
                logger.warning(
                    f"[RetryPolicy] Transient failure: {exc}. Retrying attempt {attempt}/{self.max_retries} in {delay:.2f}s..."
                )
                time.sleep(delay)


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator applying exponential backoff retry policy to async or sync functions."""
    policy = RetryPolicy(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await policy.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return policy.execute_sync(func, *args, **kwargs)
            return sync_wrapper

    return decorator


class HeartbeatMonitor:
    """Monitors worker liveness and auto-recovers crashed jobs."""

    def __init__(
        self,
        heartbeat_timeout: float = 10.0,
        worker_pool: Optional[Any] = None,
        job_queue: Optional[Any] = None,
    ):
        self.heartbeat_timeout = heartbeat_timeout
        self.worker_pool = worker_pool
        self.job_queue = job_queue
        self._worker_heartbeats: Dict[str, float] = {}  # worker_id -> float timestamp
        self._worker_active_jobs: Dict[str, str] = {}  # worker_id -> job_id
        self._monitor_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        self._lock = asyncio.Lock()

    def record_heartbeat(self, worker_id: str, job_id: Optional[str] = None):
        """Record worker heartbeat timestamp."""
        now = time.time()
        self._worker_heartbeats[worker_id] = now
        if job_id:
            self._worker_active_jobs[worker_id] = job_id

    def get_last_heartbeat(self, worker_id: str) -> Optional[float]:
        """Get timestamp of last recorded heartbeat for a worker."""
        return self._worker_heartbeats.get(worker_id)

    async def check_heartbeats(
        self,
        heartbeat_timeout: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Scan active workers and detect/auto-recover crashed jobs."""
        timeout = heartbeat_timeout or self.heartbeat_timeout
        now = time.time()
        crashed_events = []

        async with self._lock:
            # Check worker pool if available
            jq = self.job_queue or (self.worker_pool.job_queue if self.worker_pool else None)

            # Check recorded worker heartbeats
            for worker_id, last_ts in list(self._worker_heartbeats.items()):
                elapsed = now - last_ts
                if elapsed > timeout:
                    job_id = self._worker_active_jobs.get(worker_id)
                    logger.warning(
                        f"[HeartbeatMonitor] Worker '{worker_id}' heartbeat timed out ({elapsed:.1f}s > {timeout}s). "
                        f"Active job: '{job_id}'"
                    )

                    crashed_info = {
                        "worker_id": worker_id,
                        "job_id": job_id,
                        "elapsed_seconds": elapsed,
                        "recovered": False,
                    }

                    # Trigger job auto-recovery
                    if jq and job_id:
                        job = jq.get_job(job_id)
                        if job and job.status == "running":
                            logger.info(f"[HeartbeatMonitor] Auto-recovering crashed job '{job_id}'")

                            # Check for latest checkpoint
                            from app.services.checkpoint_engine import CheckpointEngine, resume_run_from_checkpoint
                            checkpoint = CheckpointEngine.get_latest_checkpoint(job.run_id)

                            if checkpoint:
                                try:
                                    resumed_state = resume_run_from_checkpoint(job.run_id)
                                    job.payload["resumed_state"] = resumed_state
                                    logger.info(f"[HeartbeatMonitor] Restored job '{job_id}' state from checkpoint '{checkpoint.checkpoint_id}'")
                                except Exception as e:
                                    logger.error(f"[HeartbeatMonitor] Failed state resumption for run '{job.run_id}': {e}")

                            # Update job status to recovering then re-enqueue
                            job.status = "recovering"
                            recovered_success = await jq.resume_job(job_id)
                            crashed_info["recovered"] = recovered_success

                    crashed_events.append(crashed_info)
                    # Clean dead worker tracking
                    self._worker_heartbeats.pop(worker_id, None)
                    self._worker_active_jobs.pop(worker_id, None)

            # Also check running jobs in JobQueueManager directly for stale heartbeat timestamps
            if jq:
                running_jobs = jq.list_jobs(status="running")
                for job in running_jobs:
                    if job.heartbeat_at:
                        try:
                            hb_dt = datetime.fromisoformat(job.heartbeat_at)
                            hb_ts = hb_dt.timestamp()
                            if (now - hb_ts) > timeout:
                                logger.warning(
                                    f"[HeartbeatMonitor] Job '{job.job_id}' stale heartbeat ({now - hb_ts:.1f}s). Auto-recovering."
                                )
                                job.status = "recovering"
                                ok = await jq.resume_job(job.job_id)
                                crashed_events.append({
                                    "worker_id": job.worker_id or "unknown",
                                    "job_id": job.job_id,
                                    "elapsed_seconds": now - hb_ts,
                                    "recovered": ok,
                                })
                        except Exception as e:
                            logger.error(f"[HeartbeatMonitor] Error parsing heartbeat_at for job '{job.job_id}': {e}")

        return crashed_events

    async def start_monitoring(self, interval: float = 2.0):
        """Start continuous heartbeat monitoring loop task."""
        if self.is_monitoring:
            return
        self.is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info(f"[HeartbeatMonitor] Heartbeat monitoring loop started (interval={interval}s)")

    async def stop_monitoring(self):
        """Stop continuous heartbeat monitoring loop task."""
        if not self.is_monitoring:
            return
        self.is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("[HeartbeatMonitor] Heartbeat monitoring loop stopped")

    async def _monitoring_loop(self, interval: float):
        """Background loop executing check_heartbeats periodically."""
        while self.is_monitoring:
            try:
                await self.check_heartbeats()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HeartbeatMonitor] Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
