"""Render job CRUD API endpoints.

Provides POST/GET/DELETE for render job lifecycle management
with pagination, status filtering, cancel, and retry support.
Follows established router conventions with DI via app.state
and JSON:API-style error responses.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from stoat_ferret.api.schemas.render import (
    CreateRenderRequest,
    RenderJobResponse,
    RenderListResponse,
)
from stoat_ferret.api.settings import get_settings
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.render_repository import (
    AsyncRenderRepository,
    AsyncSQLiteRenderRepository,
)
from stoat_ferret.render.service import PreflightError, RenderService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["render"])

# Lock for concurrent cancel/retry safety (NFR-003)
_state_transition_lock = asyncio.Lock()


# ---------- Dependency injection ----------


async def get_render_repository(request: Request) -> AsyncRenderRepository:
    """Get render repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async render repository instance.
    """
    repo: AsyncRenderRepository | None = getattr(request.app.state, "render_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteRenderRepository(request.app.state.db)


async def get_render_service(request: Request) -> RenderService:
    """Get render service from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        RenderService instance.

    Raises:
        HTTPException: 503 if render service is not available.
    """
    service: RenderService | None = getattr(request.app.state, "render_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "Render service not available"},
        )
    return service


RenderRepoDep = Annotated[AsyncRenderRepository, Depends(get_render_repository)]
RenderServiceDep = Annotated[RenderService, Depends(get_render_service)]


# ---------- Helpers ----------


def _job_to_response(job: RenderJob) -> RenderJobResponse:
    """Convert a RenderJob dataclass to a response model.

    Args:
        job: The render job to convert.

    Returns:
        Pydantic response model.
    """
    return RenderJobResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status.value,
        output_path=job.output_path,
        output_format=job.output_format.value,
        quality_preset=job.quality_preset.value,
        progress=job.progress,
        error_message=job.error_message,
        retry_count=job.retry_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


# ---------- Endpoints ----------


@router.post(
    "/render",
    response_model=RenderJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_render_job(
    body: CreateRenderRequest,
    render_service: RenderServiceDep,
) -> RenderJobResponse:
    """Start a new render job with pre-flight validation.

    Args:
        body: Render job creation request.
        render_service: Render service dependency.

    Returns:
        Created render job with 201 status.

    Raises:
        HTTPException: 400 for invalid format/preset/plan, 422 for pre-flight failure.
    """
    settings = get_settings()

    # Validate output format
    try:
        output_format = OutputFormat(body.output_format)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FORMAT",
                "message": f"Invalid output format: {body.output_format}. "
                f"Valid: {[f.value for f in OutputFormat]}",
            },
        ) from err

    # Validate quality preset
    try:
        quality_preset = QualityPreset(body.quality_preset)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PRESET",
                "message": f"Invalid quality preset: {body.quality_preset}. "
                f"Valid: {[p.value for p in QualityPreset]}",
            },
        ) from err

    output_path = str(Path(settings.render_output_dir) / f"{body.project_id}.{output_format.value}")

    try:
        job = await render_service.submit_job(
            project_id=body.project_id,
            output_path=output_path,
            output_format=output_format,
            quality_preset=quality_preset,
            render_plan_json=body.render_plan,
        )
    except PreflightError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PREFLIGHT_FAILED", "message": str(exc)},
        ) from exc

    logger.info(
        "render_endpoint.job_created",
        job_id=job.id,
        project_id=body.project_id,
        action="start",
    )
    return _job_to_response(job)


@router.get("/render/{job_id}", response_model=RenderJobResponse)
async def get_render_job(
    job_id: str,
    repo: RenderRepoDep,
) -> RenderJobResponse:
    """Get current status, progress, and metadata for a render job.

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.

    Returns:
        Render job details.

    Raises:
        HTTPException: 404 if job not found.
    """
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
        )
    return _job_to_response(job)


@router.get("/render", response_model=RenderListResponse)
async def list_render_jobs(
    repo: RenderRepoDep,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status"),
) -> RenderListResponse:
    """List all render jobs with pagination and optional status filtering.

    Args:
        repo: Render repository dependency.
        limit: Maximum number of results.
        offset: Number of results to skip.
        status_filter: Optional status value to filter by.

    Returns:
        Paginated list of render jobs.

    Raises:
        HTTPException: 400 if invalid status filter.
    """
    render_status: RenderStatus | None = None
    if status_filter is not None:
        try:
            render_status = RenderStatus(status_filter)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STATUS",
                    "message": f"Invalid status: {status_filter}. "
                    f"Valid: {[s.value for s in RenderStatus]}",
                },
            ) from err

    jobs, total = await repo.list_jobs(status=render_status, limit=limit, offset=offset)
    return RenderListResponse(
        items=[_job_to_response(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/render/{job_id}/cancel", response_model=RenderJobResponse)
async def cancel_render_job(
    job_id: str,
    repo: RenderRepoDep,
    render_service: RenderServiceDep,
) -> RenderJobResponse:
    """Cancel a running or queued render job.

    Terminates the active FFmpeg process via stdin 'q' and marks the job cancelled.

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.
        render_service: Render service dependency.

    Returns:
        Updated render job.

    Raises:
        HTTPException: 404 if not found, 409 if not cancellable.
    """
    async with _state_transition_lock:
        job = await repo.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
            )

        if job.status not in (RenderStatus.QUEUED, RenderStatus.RUNNING):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "NOT_CANCELLABLE",
                    "message": f"Cannot cancel job in {job.status.value} state",
                },
            )

        cancelled = await render_service.cancel_job(job_id)
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CANCEL_FAILED",
                    "message": f"Failed to cancel job {job_id}",
                },
            )

    updated = await repo.get(job_id)
    return _job_to_response(updated)  # type: ignore[arg-type]


@router.post("/render/{job_id}/retry", response_model=RenderJobResponse)
async def retry_render_job(
    job_id: str,
    repo: RenderRepoDep,
) -> RenderJobResponse:
    """Retry a failed render job (transient failures only).

    Requeues the job for re-execution. Rejects permanent failures
    (jobs that have exceeded the max retry count).

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.

    Returns:
        Updated render job in QUEUED status.

    Raises:
        HTTPException: 404 if not found, 409 if not retryable.
    """
    settings = get_settings()

    async with _state_transition_lock:
        job = await repo.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
            )

        if job.status != RenderStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "NOT_RETRYABLE",
                    "message": f"Cannot retry job in {job.status.value} state",
                },
            )

        # Check if this is a permanent failure (exceeded max retries)
        if job.retry_count >= settings.render_retry_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "PERMANENT_FAILURE",
                    "message": (
                        f"Job {job_id} has exceeded max retries ({settings.render_retry_count})"
                    ),
                },
            )

        # Transition: failed -> queued (retry)
        await repo.update_status(job_id, RenderStatus.QUEUED)

    updated = await repo.get(job_id)
    logger.info(
        "render_endpoint.job_retried",
        job_id=job_id,
        project_id=updated.project_id if updated else "unknown",
        action="retry",
    )
    return _job_to_response(updated)  # type: ignore[arg-type]


@router.delete("/render/{job_id}", response_model=RenderJobResponse)
async def delete_render_job(
    job_id: str,
    repo: RenderRepoDep,
) -> RenderJobResponse:
    """Delete render job metadata. Output files are preserved on disk.

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.

    Returns:
        The deleted render job.

    Raises:
        HTTPException: 404 if not found.
    """
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
        )

    response = _job_to_response(job)
    deleted = await repo.delete(job_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
        )

    logger.info("render_endpoint.job_deleted", job_id=job_id)
    return response
