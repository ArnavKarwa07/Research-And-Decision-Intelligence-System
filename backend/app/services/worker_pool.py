"""AsyncWorkerPool and JobQueueManager for RADIS background research run execution.

Supports task queuing with priority, maximum concurrency limits, worker lifecycle management,
background execution loops, and status tracking (queued, running, completed, failed, paused, cancelled).
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass(order=True)
class PriorityJobWrapper:
    """Wrapper to enable asyncio.PriorityQueue ordering based on priority and timestamp."""
    priority: int
    created_timestamp: float
    job_id: str = field(compare=False)
    job: Any = field(compare=False)


@dataclass
class Job:
    """Represents a background execution job in the worker pool."""
    job_id: str
    run_id: str
    priority: int = 5  # Lower number = higher priority (1 is highest)
    task_type: str = "research_run"
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "queued"  # queued, running, completed, failed, paused, cancelled, recovering
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    heartbeat_at: Optional[str] = None
    worker_id: Optional[str] = None
    retries: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert job state to dictionary format."""
        return {
            "job_id": self.job_id,
            "run_id": self.run_id,
            "priority": self.priority,
            "task_type": self.task_type,
            "payload": self.payload,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "heartbeat_at": self.heartbeat_at,
            "worker_id": self.worker_id,
            "retries": self.retries,
            "max_retries": self.max_retries,
        }


class JobQueueManager:
    """Manages background task queuing, status tracking, and priority scheduling."""

    def __init__(self):
        self._queue: asyncio.PriorityQueue[PriorityJobWrapper] = asyncio.PriorityQueue()
        self._jobs: Dict[str, Job] = {}
        self._run_to_job: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def enqueue_job(
        self,
        run_id: str,
        task_type: str = "research_run",
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        job_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> Job:
        """Enqueue a new job for background execution."""
        async with self._lock:
            jid = job_id or f"job-{uuid.uuid4().hex[:10]}"
            job = Job(
                job_id=jid,
                run_id=run_id,
                priority=priority,
                task_type=task_type,
                payload=payload or {},
                status="queued",
                max_retries=max_retries,
            )
            self._jobs[jid] = job
            self._run_to_job[run_id] = jid

            created_ts = time.time()
            wrapper = PriorityJobWrapper(
                priority=priority,
                created_timestamp=created_ts,
                job_id=jid,
                job=job,
            )
            await self._queue.put(wrapper)
            logger.info(f"[JobQueueManager] Job {jid} (run {run_id}) enqueued with priority {priority}")
            return job

    async def get_next_job(self, timeout: float = 1.0) -> Optional[Job]:
        """Fetch the next highest priority queued job."""
        try:
            wrapper = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return wrapper.job
        except asyncio.TimeoutError:
            return None

    def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve job by job ID."""
        return self._jobs.get(job_id)

    def get_job_by_run_id(self, run_id: str) -> Optional[Job]:
        """Retrieve job by run ID."""
        jid = self._run_to_job.get(run_id)
        if jid:
            return self._jobs.get(jid)
        return None

    def list_jobs(self, status: Optional[str] = None) -> List[Job]:
        """List all jobs optionally filtered by status."""
        if status:
            return [j for j in self._jobs.values() if j.status == status]
        return list(self._jobs.values())

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        worker_id: Optional[str] = None,
    ) -> Optional[Job]:
        """Update job status and metadata."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            job.status = status
            now_iso = datetime.now(timezone.utc).isoformat()

            if status == "running":
                if not job.started_at:
                    job.started_at = now_iso
                job.worker_id = worker_id or job.worker_id
                job.heartbeat_at = now_iso
            elif status in ["completed", "failed", "cancelled"]:
                job.completed_at = now_iso
                if result is not None:
                    job.result = result
                if error is not None:
                    job.error = error

            logger.info(f"[JobQueueManager] Job {job_id} status updated to '{status}'")
            return job

    async def pause_job(self, job_id: str) -> bool:
        """Mark job as paused."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status in ["queued", "running"]:
                job.status = "paused"
                logger.info(f"[JobQueueManager] Job {job_id} paused")
                return True
            return False

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused or failed job by re-enqueuing."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status in ["paused", "failed", "recovering", "running"]:
                job.status = "queued"
                job.error = None
                created_ts = time.time()
                wrapper = PriorityJobWrapper(
                    priority=job.priority,
                    created_timestamp=created_ts,
                    job_id=job.job_id,
                    job=job,
                )
                await self._queue.put(wrapper)
                logger.info(f"[JobQueueManager] Job {job_id} resumed and re-enqueued")
                return True
            return False

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or running job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status in ["queued", "running", "paused"]:
                job.status = "cancelled"
                job.completed_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"[JobQueueManager] Job {job_id} cancelled")
                return True
            return False

    def clear(self):
        """Clear all jobs in the queue manager."""
        self._jobs.clear()
        self._run_to_job.clear()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class AsyncWorkerPool:
    """Manages background worker loops for executing research jobs concurrently."""

    def __init__(
        self,
        max_concurrency: int = 4,
        job_queue: Optional[JobQueueManager] = None,
    ):
        self.max_concurrency = max_concurrency
        self.job_queue = job_queue or JobQueueManager()
        self.workers: List[asyncio.Task] = []
        self.active_tasks: Dict[str, asyncio.Task] = {}  # job_id -> Task
        self.handlers: Dict[str, Callable[[Job], Awaitable[Any]]] = {}
        self.is_running = False
        self._lock = asyncio.Lock()

    def register_handler(
        self,
        task_type: str,
        handler: Callable[[Job], Awaitable[Any]],
    ):
        """Register a handler function for a specific task type."""
        self.handlers[task_type] = handler

    async def start(self):
        """Start the background worker pool loops."""
        async with self._lock:
            if self.is_running:
                return
            self.is_running = True
            for i in range(self.max_concurrency):
                worker_id = f"worker-{i+1}"
                task = asyncio.create_task(self._worker_loop(worker_id))
                self.workers.append(task)
            logger.info(f"[AsyncWorkerPool] Worker pool started with {self.max_concurrency} workers")

    async def stop(self, timeout: float = 5.0):
        """Gracefully stop all background worker loops and running tasks."""
        async with self._lock:
            if not self.is_running:
                return
            self.is_running = False

            # Cancel worker loops
            for w in self.workers:
                w.cancel()

            # Wait for worker tasks
            if self.workers:
                await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()

            # Cancel any remaining active job tasks
            for jid, task in list(self.active_tasks.items()):
                if not task.done():
                    task.cancel()
            self.active_tasks.clear()

            logger.info("[AsyncWorkerPool] Worker pool stopped cleanly")

    async def _worker_loop(self, worker_id: str):
        """Continuous background loop for pulling and executing jobs."""
        logger.info(f"[AsyncWorkerPool] {worker_id} loop initialized")
        while self.is_running:
            try:
                job = await self.job_queue.get_next_job(timeout=0.5)
                if not job:
                    await asyncio.sleep(0.1)
                    continue

                if job.status in ["cancelled", "paused"]:
                    continue

                # Mark job running
                await self.job_queue.update_job_status(
                    job_id=job.job_id,
                    status="running",
                    worker_id=worker_id,
                )

                current_task = asyncio.current_task()
                if current_task:
                    self.active_tasks[job.job_id] = current_task

                try:
                    handler = self.handlers.get(job.task_type)
                    if not handler:
                        raise ValueError(f"No registered handler for task type '{job.task_type}'")

                    result = await handler(job)

                    # Check status in case it was cancelled or paused mid-execution
                    latest_job = self.job_queue.get_job(job.job_id)
                    if latest_job and latest_job.status in ["cancelled", "paused"]:
                        logger.info(f"Job {job.job_id} finished execution with status {latest_job.status}")
                    else:
                        await self.job_queue.update_job_status(
                            job_id=job.job_id,
                            status="completed",
                            result=result,
                        )

                except asyncio.CancelledError:
                    logger.warning(f"[{worker_id}] Job {job.job_id} task was cancelled")
                    latest_job = self.job_queue.get_job(job.job_id)
                    if latest_job and latest_job.status not in ["paused", "cancelled"]:
                        await self.job_queue.update_job_status(
                            job_id=job.job_id,
                            status="cancelled",
                            error="Task cancelled by worker pool",
                        )
                    raise

                except Exception as exc:
                    logger.error(f"[{worker_id}] Error executing job {job.job_id}: {exc}", exc_info=True)
                    latest_job = self.job_queue.get_job(job.job_id)
                    if latest_job and latest_job.status == "paused":
                        pass
                    elif latest_job and latest_job.retries < latest_job.max_retries:
                        latest_job.retries += 1
                        logger.info(f"[{worker_id}] Retrying job {job.job_id} ({latest_job.retries}/{latest_job.max_retries})")
                        await self.job_queue.resume_job(job.job_id)
                    else:
                        await self.job_queue.update_job_status(
                            job_id=job.job_id,
                            status="failed",
                            error=str(exc),
                        )

                finally:
                    self.active_tasks.pop(job.job_id, None)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{worker_id}] Unexpected worker loop error: {e}")
                await asyncio.sleep(0.2)

        logger.info(f"[AsyncWorkerPool] {worker_id} loop terminated")

    async def submit_job(
        self,
        run_id: str,
        task_type: str = "research_run",
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 5,
    ) -> Job:
        """Helper to enqueue a job into the queue manager."""
        return await self.job_queue.enqueue_job(
            run_id=run_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
        )


# Singleton worker pool instance
global_worker_pool = AsyncWorkerPool()

