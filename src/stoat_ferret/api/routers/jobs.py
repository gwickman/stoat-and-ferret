"""Job status endpoints.

Job state machine (documented for external AI agents):

- ``pending``    — submitted, not yet picked up by a worker.
- ``running``    — worker is executing the handler.
- ``complete``   — handler returned successfully (**terminal**).
- ``failed``     — handler raised an exception (**terminal**).
- ``timeout``    — handler exceeded the per-job-type timeout (**terminal**).
- ``cancelled``  — caller invoked ``POST /api/v1/jobs/{id}/cancel`` before
  a terminal state was reached (**terminal**).

Valid transitions::

    pending -> running
    running -> complete | failed | timeout | cancelled
    pending -> cancelled   (when cancel is requested before the worker
                            claims the entry)

Terminal states (``complete``, ``failed``, ``timeout``, ``cancelled``) are
final: once a job enters a terminal state its status never changes again.
See :class:`stoat_ferret.jobs.queue.JobStatus` for the authoritative enum.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from stoat_ferret.api.schemas.job import JobStatusResponse
from stoat_ferret.api.services.job_completion import wait_for_job_terminal
from stoat_ferret.jobs.queue import JobStatus

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    request: Request,
) -> JobStatusResponse:
    """Get the current status of a submitted job.

    Returns a point-in-time snapshot of the job's state in the queue.
    The ``status`` field is one of the six ``JobStatus`` values, three
    non-terminal (``pending``, ``running``) and four terminal
    (``complete``, ``failed``, ``timeout``, ``cancelled``). Callers that
    need to block until a terminal state can use
    ``GET /api/v1/jobs/{id}/wait`` instead of polling.

    Valid state transitions are: ``pending -> running -> (complete |
    failed | timeout | cancelled)``. Terminal states never change.

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

    Drives the ``pending -> cancelled`` or ``running -> cancelled`` state
    transition. Cancellation is rejected with 409 when the job is already
    in a terminal state (``complete``, ``failed``, ``timeout``, or
    ``cancelled``) because terminal states are final.

    Args:
        job_id: The unique job identifier.
        request: The FastAPI request object for accessing app state.

    Returns:
        Updated job status after the cancellation signal has been
        recorded. The returned ``status`` may still be ``running`` if
        the worker has not yet observed the cancellation flag; callers
        should poll ``GET /api/v1/jobs/{id}`` or use
        ``GET /api/v1/jobs/{id}/wait`` to observe the final
        ``cancelled`` terminal state.

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


@router.get("/{job_id}/wait", response_model=JobStatusResponse)
async def wait_for_job_completion(
    job_id: str,
    request: Request,
    timeout: float = Query(
        30.0,
        ge=1.0,
        le=3600.0,
        description=(
            "Maximum seconds to wait for the job to reach a terminal state. "
            "Server returns HTTP 408 if the job is still non-terminal when "
            "the deadline expires."
        ),
    ),
) -> JobStatusResponse:
    """Block until the job reaches a terminal state, then return its final status.

    Long-poll helper intended as a deterministic alternative to polling
    ``GET /api/v1/jobs/{id}`` or subscribing to the WebSocket stream at
    ``/ws``. The endpoint waits for the job to enter one of the terminal
    states (``complete``, ``failed``, ``timeout``, ``cancelled``) and
    then returns the same payload as ``GET /api/v1/jobs/{id}``.

    Semantics:

    - If the job is already terminal at call time the handler returns
      immediately without allocating an :class:`asyncio.Event`
      (INV-LP-2).
    - Otherwise it awaits the per-job event that queue workers signal
      after writing the terminal status (INV-LP-1).
    - The endpoint returns HTTP 408 (``code="JOB_WAIT_TIMEOUT"``) when
      the job is still non-terminal after ``timeout`` seconds — the job
      itself continues running; the timeout is client-side only.
    - Not durable: if the server restarts while a waiter is blocked,
      the waiter sees a timeout rather than a replay. Treat a restart
      as equivalent to a timeout.

    Args:
        job_id: The job identifier to wait on.
        request: The FastAPI request (used to resolve the job queue).
        timeout: Maximum seconds to wait. Clamped to ``[1, 3600]``.

    Returns:
        Final :class:`JobStatusResponse` once the job is terminal.

    Raises:
        HTTPException: 404 when ``job_id`` is unknown. 408 when the job
            does not reach a terminal state within ``timeout`` seconds.
    """
    job_queue = request.app.state.job_queue
    result = await wait_for_job_terminal(job_queue, job_id, timeout)
    return JobStatusResponse(
        job_id=result.job_id,
        status=result.status.value,
        progress=result.progress,
        result=result.result,
        error=result.error,
    )
