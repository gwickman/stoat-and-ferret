"""Job status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from stoat_ferret.api.schemas.job import JobStatusResponse
from stoat_ferret.jobs.queue import JobStatus

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    request: Request,
) -> JobStatusResponse:
    """Get the status of a submitted job.

    Args:
        job_id: The unique job identifier.
        request: The FastAPI request object for accessing app state.

    Returns:
        Job status including progress and result when complete.

    Raises:
        HTTPException: 404 if job ID is not found.
    """
    job_queue = request.app.state.job_queue
    try:
        result = await job_queue.get_result(job_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        ) from None

    return JobStatusResponse(
        job_id=result.job_id,
        status=result.status.value,
        progress=result.progress,
        result=result.result,
        error=result.error,
    )


_TERMINAL_STATUSES = {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.TIMEOUT, JobStatus.CANCELLED}


@router.post("/{job_id}/cancel", response_model=JobStatusResponse)
async def cancel_job(
    job_id: str,
    request: Request,
) -> JobStatusResponse:
    """Request cancellation of a job.

    Args:
        job_id: The unique job identifier.
        request: The FastAPI request object for accessing app state.

    Returns:
        Updated job status.

    Raises:
        HTTPException: 404 if job not found, 409 if already in terminal state.
    """
    job_queue = request.app.state.job_queue
    try:
        result = await job_queue.get_result(job_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        ) from None

    if result.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_TERMINAL",
                "message": f"Job {job_id} is already {result.status.value}",
            },
        )

    job_queue.cancel(job_id)

    # Re-fetch to get updated status
    result = await job_queue.get_result(job_id)
    return JobStatusResponse(
        job_id=result.job_id,
        status=result.status.value,
        progress=result.progress,
        result=result.result,
        error=result.error,
    )
