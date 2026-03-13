"""Batch render endpoints.

Provides POST /render/batch for submitting batch render jobs and
GET /render/batch/{batch_id} for tracking aggregated progress.
Concurrency is managed via asyncio.Semaphore since AsyncioJobQueue
is sequential-only.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from stoat_ferret.api.schemas.batch import (
    BatchJobStatusResponse,
    BatchProgressResponse,
    BatchRequest,
    BatchResponse,
)
from stoat_ferret.api.settings import get_settings
from stoat_ferret_core import BatchJobStatus, calculate_batch_progress

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/render", tags=["batch"])

# Type alias for batch render handler: (project_id, output_path, quality) -> None
BatchRenderHandler = Callable[[str, str, str], Awaitable[None]]


@dataclass
class _BatchJob:
    """Internal tracking for a single job in a batch."""

    job_id: str
    project_id: str
    output_path: str
    quality: str
    status: str = "queued"
    progress: float = 0.0
    error: str | None = None


@dataclass
class _BatchState:
    """Internal tracking for a batch of render jobs."""

    batch_id: str
    jobs: list[_BatchJob] = field(default_factory=list)


def _get_batch_store(request: Request) -> dict[str, _BatchState]:
    """Get or lazily create the batch store on app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Dict mapping batch_id to batch state.
    """
    store: dict[str, _BatchState] | None = getattr(request.app.state, "_batch_store", None)
    if store is None:
        store = {}
        request.app.state._batch_store = store
    return store


def _to_rust_status(job: _BatchJob) -> BatchJobStatus:
    """Convert internal job status to Rust BatchJobStatus.

    Args:
        job: Internal batch job with status field.

    Returns:
        Corresponding Rust BatchJobStatus instance.
    """
    if job.status == "running":
        return BatchJobStatus.in_progress(job.progress)
    if job.status == "complete":
        return BatchJobStatus.completed()
    if job.status == "failed":
        return BatchJobStatus.failed()
    return BatchJobStatus.pending()


async def _run_batch_job(
    job: _BatchJob,
    semaphore: asyncio.Semaphore,
    handler: BatchRenderHandler | None,
) -> None:
    """Run a single batch job with semaphore-limited concurrency.

    Args:
        job: The batch job to execute.
        semaphore: Semaphore limiting parallel execution.
        handler: Optional render handler to call for each job.
    """
    async with semaphore:
        job.status = "running"
        logger.info("batch_job_started", job_id=job.job_id, project_id=job.project_id)
        try:
            if handler is not None:
                await handler(job.project_id, job.output_path, job.quality)
            job.status = "complete"
            job.progress = 1.0
            logger.info("batch_job_completed", job_id=job.job_id)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            logger.error("batch_job_failed", job_id=job.job_id, error=str(exc))


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
    batch = _BatchState(batch_id=batch_id)

    for job_config in batch_request.jobs:
        job = _BatchJob(
            job_id=str(uuid.uuid4()),
            project_id=job_config.project_id,
            output_path=job_config.output_path,
            quality=job_config.quality,
        )
        batch.jobs.append(job)

    store = _get_batch_store(request)
    store[batch_id] = batch

    handler: BatchRenderHandler | None = getattr(request.app.state, "batch_render_handler", None)
    semaphore = asyncio.Semaphore(settings.batch_parallel_limit)
    for job in batch.jobs:
        asyncio.create_task(_run_batch_job(job, semaphore, handler))

    logger.info("batch_submitted", batch_id=batch_id, job_count=len(batch.jobs))

    return BatchResponse(
        batch_id=batch_id,
        jobs_queued=len(batch.jobs),
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
    store = _get_batch_store(request)
    batch = store.get(batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Batch {batch_id} not found"},
        )

    rust_statuses = [_to_rust_status(job) for job in batch.jobs]
    progress = calculate_batch_progress(rust_statuses)

    job_statuses = [
        BatchJobStatusResponse(
            job_id=job.job_id,
            project_id=job.project_id,
            status=job.status,
            progress=job.progress,
            error=job.error,
        )
        for job in batch.jobs
    ]

    return BatchProgressResponse(
        batch_id=batch_id,
        overall_progress=progress.overall_progress,
        completed_jobs=progress.completed_jobs,
        failed_jobs=progress.failed_jobs,
        total_jobs=progress.total_jobs,
        jobs=job_statuses,
    )
