"""Persistent render queue with concurrency control.

Provides FIFO job queuing with max_concurrent/max_depth limits
and server restart recovery. Queue state is derived from the
render_jobs table status column via the repository.
"""

from __future__ import annotations

import asyncio

import structlog

from stoat_ferret.render.models import RenderJob, RenderStatus
from stoat_ferret.render.render_repository import AsyncRenderRepository

logger = structlog.get_logger(__name__)


class QueueFullError(Exception):
    """Raised when the render queue has reached its maximum depth.

    Attributes:
        queue_depth: Current number of queued jobs.
        max_depth: Maximum allowed queue depth.
    """

    def __init__(self, *, queue_depth: int, max_depth: int) -> None:
        self.queue_depth = queue_depth
        self.max_depth = max_depth
        super().__init__(f"Render queue is full: {queue_depth}/{max_depth} jobs queued")


class RenderQueue:
    """Persistent render queue with concurrency and depth limits.

    Queue state is derived from the render_jobs table via the repository.
    Uses an asyncio.Lock to serialize dequeue operations and prevent
    over-committing beyond max_concurrent. Jobs are dequeued in FIFO
    order by created_at.

    Args:
        repository: Async render job repository for persistence.
        max_concurrent: Maximum number of simultaneously running jobs.
        max_depth: Maximum number of queued jobs before rejection.
    """

    def __init__(
        self,
        repository: AsyncRenderRepository,
        *,
        max_concurrent: int = 4,
        max_depth: int = 50,
    ) -> None:
        self._repo = repository
        self._max_concurrent = max_concurrent
        self._max_depth = max_depth
        self._dequeue_lock = asyncio.Lock()

    async def enqueue(self, job: RenderJob) -> RenderJob:
        """Add a job to the render queue.

        Args:
            job: The render job to enqueue (must have status=queued).

        Returns:
            The persisted render job.

        Raises:
            QueueFullError: When the queue depth has reached max_depth.
        """
        depth = await self.get_queue_depth()
        if depth >= self._max_depth:
            logger.warning(
                "render_queue.capacity_reached",
                queue_depth=depth,
                max_depth=self._max_depth,
                job_id=job.id,
            )
            raise QueueFullError(queue_depth=depth, max_depth=self._max_depth)

        persisted = await self._repo.create(job)
        logger.info(
            "render_queue.enqueue",
            job_id=job.id,
            project_id=job.project_id,
            queue_depth=depth + 1,
        )
        return persisted

    async def dequeue(self) -> RenderJob | None:
        """Get the next queued job and transition it to running.

        Returns None if no queued jobs exist or if the max_concurrent
        limit has been reached. Uses a lock to prevent concurrent
        dequeue calls from over-committing.

        Returns:
            The next job transitioned to running, or None.
        """
        async with self._dequeue_lock:
            active = await self.get_active_count()
            if active >= self._max_concurrent:
                return None

            queued_jobs = await self._repo.list_by_status(RenderStatus.QUEUED)
            if not queued_jobs:
                return None

            # FIFO: list_by_status returns ordered by created_at
            job = queued_jobs[0]
            await self._repo.update_status(job.id, RenderStatus.RUNNING)
            logger.info(
                "render_queue.dequeue",
                job_id=job.id,
                project_id=job.project_id,
                active_count=active + 1,
            )

            updated = await self._repo.get(job.id)
            return updated

    async def get_active_count(self) -> int:
        """Count jobs with running status.

        Returns:
            Number of currently running jobs.
        """
        running = await self._repo.list_by_status(RenderStatus.RUNNING)
        return len(running)

    async def get_queue_depth(self) -> int:
        """Count jobs with queued status.

        Returns:
            Number of currently queued jobs.
        """
        queued = await self._repo.list_by_status(RenderStatus.QUEUED)
        return len(queued)

    async def recover(self) -> list[RenderJob]:
        """Recover queue state after server restart.

        Finds all jobs with running status (which couldn't still be running
        after a restart) and marks them as failed. No checkpoint data is
        available yet, so interrupted jobs cannot be resumed.

        Returns:
            List of jobs that were marked as failed during recovery.
        """
        running_jobs = await self._repo.list_by_status(RenderStatus.RUNNING)
        recovered: list[RenderJob] = []

        for job in running_jobs:
            await self._repo.update_status(
                job.id,
                RenderStatus.FAILED,
                error_message="Server restart: job interrupted without checkpoint",
            )
            recovered.append(job)
            logger.warning(
                "render_queue.recovery",
                job_id=job.id,
                project_id=job.project_id,
                previous_progress=job.progress,
            )

        if recovered:
            logger.info(
                "render_queue.recovery_complete",
                recovered_count=len(recovered),
            )

        return recovered
