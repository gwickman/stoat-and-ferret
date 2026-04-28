"""Batch render endpoints.

Provides POST /render/batch for submitting batch render jobs and
GET /render/batch/{batch_id} for tracking aggregated progress.
Concurrency is managed via asyncio.Semaphore since AsyncioJobQueue
is sequential-only. Batch state is persisted via AsyncBatchRepository.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from stoat_ferret.api.schemas.batch import (
    BatchJobStatusResponse,
    BatchProgressResponse,
    BatchRequest,
    BatchResponse,
)
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.batch_repository import AsyncBatchRepository, BatchJobRecord
from stoat_ferret_core import BatchJobStatus, calculate_batch_progress

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/render", tags=["batch"])

# Type alias for batch render handler: (project_id, output_path, quality) -> None
BatchRenderHandler = Callable[[str, str, str], Awaitable[None]]


def _get_batch_repository(request: Request) -> AsyncBatchRepository:
    """Get the batch repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        The batch repository instance.
    """
    return request.app.state.batch_repository  # type: ignore[no-any-return]


def _to_rust_status(job: BatchJobRecord) -> BatchJobStatus:
    """Convert a batch job record status to Rust BatchJobStatus.

    Args:
        job: Batch job record with status field.

    Returns:
        Corresponding Rust BatchJobStatus instance.
    """
    if job.status == "running":
        return BatchJobStatus.in_progress(job.progress)
    if job.status == "completed":
        return BatchJobStatus.completed()
    if job.status == "failed":
        return BatchJobStatus.failed()
    return BatchJobStatus.pending()


async def _run_batch_job(
    job_id: str,
    project_id: str,
    output_path: str,
    quality: str,
    semaphore: asyncio.Semaphore,
    handler: BatchRenderHandler | None,
    repository: AsyncBatchRepository,
    task_registry: dict[str, asyncio.Task[None]] | None = None,
) -> None:
    """Run a single batch job with semaphore-limited concurrency.

    Args:
        job_id: The unique job identifier.
        project_id: The project to render.
        output_path: Output file path.
        quality: Render quality preset.
        semaphore: Semaphore limiting parallel execution.
        handler: Optional render handler to call for each job.
        repository: Batch repository for persisting state changes.
        task_registry: Optional dict (job_id -> Task) cleaned up on exit.
    """
    try:
        async with semaphore:
            # If the job was cancelled (or already terminal) while waiting
            # for the semaphore, skip execution. This handles the DELETE-
            # on-queued race where the repo already shows 'cancelled'.
            current = await repository.get_by_job_id(job_id)
            if current is None or current.status != "queued":
                logger.info(
                    "batch_job_skipped",
                    job_id=job_id,
                    status=current.status if current else None,
                )
                return

            await repository.update_status(job_id, "running")
            logger.info("batch_job_started", job_id=job_id, project_id=project_id)
            try:
                if handler is not None:
                    await handler(project_id, output_path, quality)
                await repository.update_status(job_id, "completed")
                await repository.update_progress(job_id, 1.0)
                logger.info("batch_job_completed", job_id=job_id)
            except asyncio.CancelledError:
                # Transition running -> cancelled. Only update if still
                # in 'running' to stay idempotent under concurrent cancels.
                latest = await repository.get_by_job_id(job_id)
                if latest is not None and latest.status == "running":
                    await repository.update_status(job_id, "cancelled")
                logger.info("batch_job_cancelled", job_id=job_id)
                raise
            except Exception as exc:
                await repository.update_status(job_id, "failed", error=str(exc))
                logger.error("batch_job_failed", job_id=job_id, error=str(exc))
    finally:
        if task_registry is not None:
            task_registry.pop(job_id, None)


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED, response_model=BatchResponse)
async def submit_batch(
    batch_request: BatchRequest,
    request: Request,
) -> BatchResponse:
    """Submit a batch of render jobs for parallel execution.

    Jobs are queued and executed with concurrency limited by
    Settings.batch_parallel_limit. Returns immediately with a batch_id.

    Args:
        batch_request: The batch render request with job configurations.
        request: The FastAPI request object for accessing app state.

    Returns:
        BatchResponse with batch_id, queued job count, and status.

    Raises:
        HTTPException: 422 if job count exceeds Settings.batch_max_jobs.
    """
    settings = get_settings()

    if len(batch_request.jobs) > settings.batch_max_jobs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "BATCH_JOB_LIMIT_EXCEEDED",
                "message": f"Maximum {settings.batch_max_jobs} jobs per batch",
            },
        )

    batch_id = str(uuid.uuid4())
    repository = _get_batch_repository(request)

    job_records = []
    for job_config in batch_request.jobs:
        record = await repository.create_batch_job(
            batch_id=batch_id,
            job_id=str(uuid.uuid4()),
            project_id=job_config.project_id,
            output_path=job_config.output_path,
            quality=job_config.quality,
        )
        job_records.append(record)

    handler: BatchRenderHandler | None = getattr(request.app.state, "batch_render_handler", None)
    semaphore = asyncio.Semaphore(settings.batch_parallel_limit)
    task_registry: dict[str, asyncio.Task[None]] = getattr(
        request.app.state, "batch_tasks", {}
    )
    request.app.state.batch_tasks = task_registry
    for record in job_records:
        task = asyncio.create_task(
            _run_batch_job(
                record.job_id,
                record.project_id,
                record.output_path,
                record.quality,
                semaphore,
                handler,
                repository,
                task_registry,
            )
        )
        task_registry[record.job_id] = task

    logger.info("batch_submitted", batch_id=batch_id, job_count=len(job_records))

    return BatchResponse(
        batch_id=batch_id,
        jobs_queued=len(job_records),
        status="accepted",
    )


@router.get("/batch/{batch_id}", response_model=BatchProgressResponse)
async def get_batch_progress(
    batch_id: str,
    request: Request,
) -> BatchProgressResponse:
    """Get aggregated progress for a batch render.

    Uses Rust calculate_batch_progress() for progress aggregation
    across all jobs in the batch.

    Args:
        batch_id: The unique batch identifier.
        request: The FastAPI request object for accessing app state.

    Returns:
        Aggregated batch progress with per-job status details.

    Raises:
        HTTPException: 404 if batch ID is not found.
    """
    repository = _get_batch_repository(request)
    jobs = await repository.get_by_batch_id(batch_id)

    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Batch {batch_id} not found"},
        )

    rust_statuses = [_to_rust_status(job) for job in jobs]
    progress = calculate_batch_progress(rust_statuses)

    job_statuses = [
        BatchJobStatusResponse(
            job_id=job.job_id,
            project_id=job.project_id,
            status=job.status,
            progress=job.progress,
            error=job.error,
        )
        for job in jobs
    ]

    return BatchProgressResponse(
        batch_id=batch_id,
        overall_progress=progress.overall_progress,
        completed_jobs=progress.completed_jobs,
        failed_jobs=progress.failed_jobs,
        total_jobs=progress.total_jobs,
        jobs=job_statuses,
    )


_TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed", "cancelled"})


@router.delete("/batch/{job_id}", response_model=BatchJobStatusResponse)
async def cancel_batch_job(
    job_id: str,
    request: Request,
) -> BatchJobStatusResponse:
    """Cancel a single batch job by job_id.

    Returns the updated job status after cancellation. Queued jobs are
    transitioned directly to ``cancelled``; running jobs are cancelled
    via task cancellation, with the running task's CancelledError
    handler performing the status transition.

    Args:
        job_id: The unique job identifier to cancel.
        request: The FastAPI request object for accessing app state.

    Returns:
        BatchJobStatusResponse reflecting the post-cancel job state.

    Raises:
        HTTPException: 404 if no job with the given ID exists; 409 if
            the job is already in a terminal state.
    """
    repository = _get_batch_repository(request)
    job = await repository.get_by_job_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        )

    if job.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "JOB_ALREADY_TERMINAL",
                "message": f"Job {job_id} already finished with status {job.status!r}",
            },
        )

    task_registry: dict[str, asyncio.Task[None]] = getattr(
        request.app.state, "batch_tasks", {}
    )
    task = task_registry.get(job_id)

    if job.status == "queued":
        await repository.update_status(job_id, "cancelled")
        if task is not None and not task.done():
            task.cancel()
        logger.info("batch_job_cancel_queued", job_id=job_id)
    else:
        # status == "running" — cancel the task; CancelledError handler
        # transitions the repository status to 'cancelled'.
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        else:
            await repository.update_status(job_id, "cancelled")
        logger.info("batch_job_cancel_running", job_id=job_id)

    updated = await repository.get_by_job_id(job_id)
    if updated is None:  # pragma: no cover — record exists, never deleted
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        )
    return BatchJobStatusResponse(
        job_id=updated.job_id,
        project_id=updated.project_id,
        status=updated.status,
        progress=updated.progress,
        error=updated.error,
    )
