# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Per-job terminal-state notifications for the ``/wait`` long-poll endpoint.

This module owns the in-process registry of :class:`asyncio.Event` objects
used by ``GET /api/v1/jobs/{id}/wait`` (BL-277) to block callers until a
job reaches a terminal state. The design is intentionally minimal:

- A single module-level ``_terminal_events`` dict maps ``job_id`` to a
  *set* of :class:`asyncio.Event` objects, one per concurrent waiter.
  Each waiter registers its own event (BL-700), so any number of callers
  may wait on the same job simultaneously.
- :func:`notify_job_terminal` is called by the queue implementations in
  :mod:`stoat_ferret.jobs.queue` **after** a terminal-state write so that
  a waiter never observes a stale ``pending``/``running`` status
  (INV-LP-1). It pops the entire set and fans out the signal to all waiters.
- :func:`wait_for_job_terminal` is the handler helper: it short-circuits
  when the job is already terminal (INV-LP-2), otherwise creates a private
  event, adds it to the per-job set, awaits it under :func:`asyncio.timeout`
  (3.11+) or :func:`asyncio.wait_for` (3.10), and surfaces timeouts as
  :class:`fastapi.HTTPException` with HTTP 408 (INV-LP-3). The timeout
  catch uses :class:`asyncio.TimeoutError` — distinct from
  :class:`builtins.TimeoutError` on Python 3.10, and unified with it on
  3.11+.

The dict is discarded when the process exits; pending clients are
expected to reconnect and re-query after a restart.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from stoat_ferret.jobs.queue import AsyncJobQueue, JobResult

# Terminal state values are stored as strings (not JobStatus enum members) to
# avoid a module-level import cycle with stoat_ferret.jobs.queue, which imports
# notify_job_terminal from this module.
_TERMINAL_STATUS_VALUES = frozenset({"completed", "failed", "timeout", "cancelled"})

_terminal_events: dict[str, set[asyncio.Event]] = {}


def notify_job_terminal(job_id: str) -> None:
    """Signal all waiters that ``job_id`` has reached a terminal state.

    MUST be invoked **after** the job registry has been updated with the
    terminal status so that the subsequent ``get_result`` call from the
    waiter observes the final state (INV-LP-1). A no-op when no waiter is
    registered for the job — the dict entry is only created by
    :func:`wait_for_job_terminal`.

    Pops the entire set of events for ``job_id`` and sets each one,
    fanning out the terminal signal to every concurrent waiter (BL-700).

    Args:
        job_id: The job identifier whose terminal state was just written.
    """
    events = _terminal_events.pop(job_id, set())
    for event in events:
        event.set()


async def wait_for_job_terminal(
    job_queue: AsyncJobQueue,
    job_id: str,
    timeout_seconds: float,
) -> JobResult:
    """Block until ``job_id`` reaches a terminal state or the timeout expires.

    Returns immediately when the job is already terminal at call time so
    no persistent :class:`asyncio.Event` is created for already-completed
    jobs (INV-LP-2). Otherwise creates a private event, adds it to the
    per-job set (supporting concurrent waiters, BL-700), awaits it under
    :func:`asyncio.timeout` (Python 3.11+) or :func:`asyncio.wait_for`
    (Python 3.10), then refetches the result so the caller always sees the
    final state written by the queue worker.

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

    event = asyncio.Event()
    _terminal_events.setdefault(job_id, set()).add(event)

    try:
        if sys.version_info >= (3, 11):
            async with asyncio.timeout(timeout_seconds):
                await event.wait()
        else:
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
        s = _terminal_events.get(job_id)
        if s is not None:
            s.discard(event)
            if not s:
                _terminal_events.pop(job_id, None)

    return await job_queue.get_result(job_id)
