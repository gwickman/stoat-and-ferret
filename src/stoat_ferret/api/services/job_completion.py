"""Per-job terminal-state notifications for the ``/wait`` long-poll endpoint.

This module owns the in-process registry of :class:`asyncio.Event` objects
used by ``GET /api/v1/jobs/{id}/wait`` (BL-277) to block callers until a
job reaches a terminal state. The design is intentionally minimal:

- A single module-level ``_terminal_events`` dict maps ``job_id`` to a
  lazily created :class:`asyncio.Event`.
- :func:`notify_job_terminal` is called by the queue implementations in
  :mod:`stoat_ferret.jobs.queue` **after** a terminal-state write so that
  a waiter never observes a stale ``pending``/``running`` status
  (INV-LP-1).
- :func:`wait_for_job_terminal` is the handler helper: it short-circuits
  when the job is already terminal (INV-LP-2), otherwise awaits the event
  under :func:`asyncio.wait_for` and surfaces timeouts as
  :class:`fastapi.HTTPException` with HTTP 408 (INV-LP-3). The
  timeout catch uses :class:`asyncio.TimeoutError` — distinct from
  :class:`builtins.TimeoutError` on Python 3.10.

The dict is discarded when the process exits; pending clients are
expected to reconnect and re-query after a restart.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from stoat_ferret.jobs.queue import AsyncJobQueue, JobResult

_TERMINAL_STATUS_VALUES = frozenset({"complete", "failed", "timeout", "cancelled"})

_terminal_events: dict[str, asyncio.Event] = {}


def notify_job_terminal(job_id: str) -> None:
    """Signal any waiter that ``job_id`` has reached a terminal state.

    MUST be invoked **after** the job registry has been updated with the
    terminal status so that the subsequent ``get_result`` call from the
    waiter observes the final state (INV-LP-1). A no-op when no waiter is
    registered for the job — the dict entry is only created by
    :func:`wait_for_job_terminal`.

    Args:
        job_id: The job identifier whose terminal state was just written.
    """
    event = _terminal_events.get(job_id)
    if event is not None:
        event.set()


async def wait_for_job_terminal(
    job_queue: AsyncJobQueue,
    job_id: str,
    timeout_seconds: float,
) -> JobResult:
    """Block until ``job_id`` reaches a terminal state or the timeout expires.

    Returns immediately when the job is already terminal at call time so
    no persistent :class:`asyncio.Event` is created for already-completed
    jobs (INV-LP-2). Otherwise creates the event lazily, awaits it under
    :func:`asyncio.wait_for`, then refetches the result so the caller
    always sees the final state written by the queue worker.

    Args:
        job_queue: The queue that owns the job.
        job_id: The job identifier to wait on.
        timeout_seconds: Maximum number of seconds to wait.

    Returns:
        The final :class:`~stoat_ferret.jobs.queue.JobResult`.

    Raises:
        HTTPException: 404 when ``job_id`` is unknown. 408 when the job
            does not reach a terminal state within ``timeout_seconds``.
    """
    try:
        result = await job_queue.get_result(job_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Job {job_id} not found"},
        ) from None

    if result.status.value in _TERMINAL_STATUS_VALUES:
        return result

    event = _terminal_events.setdefault(job_id, asyncio.Event())

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={
                "code": "JOB_WAIT_TIMEOUT",
                "message": (
                    f"Job {job_id} did not reach a terminal state within {timeout_seconds}s"
                ),
            },
        ) from None
    finally:
        _terminal_events.pop(job_id, None)

    return await job_queue.get_result(job_id)
