# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Contract tests for concurrent-waiter correctness in job_completion (BL-700).

Verifies that multiple concurrent callers of :func:`wait_for_job_terminal`
on the same job_id all receive the terminal notification — the fix for the
single-Event registry race where a late-arriving waiter would never be woken.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from stoat_ferret.api.services import job_completion
from stoat_ferret.api.services.job_completion import (
    notify_job_terminal,
    wait_for_job_terminal,
)
from stoat_ferret.jobs.queue import (
    InMemoryJobQueue,
    JobResult,
    JobStatus,
    _JobEntry,
)


@pytest.fixture(autouse=True)
def _clear_terminal_events() -> Iterator[None]:
    """Ensure the module-level event dict starts and ends empty for each test."""
    job_completion._terminal_events.clear()
    yield
    job_completion._terminal_events.clear()


@pytest.fixture
def pending_queue() -> tuple[InMemoryJobQueue, str]:
    """Return a queue with a single pending job inserted directly."""
    queue = InMemoryJobQueue()
    job_id = "concurrent-waiter-test-job"
    entry = _JobEntry(job_id=job_id, job_type="scan", payload={})
    entry.result = JobResult(job_id=job_id, status=JobStatus.PENDING)
    queue._jobs[job_id] = entry
    return queue, job_id


async def test_two_concurrent_waiters_both_receive_completion(
    pending_queue: tuple[InMemoryJobQueue, str],
) -> None:
    """Both concurrent waiters wake up when notify_job_terminal fires (BL-700)."""
    queue, job_id = pending_queue

    async def _complete_after_delay() -> None:
        await asyncio.sleep(0.1)
        entry = queue._jobs[job_id]
        entry.result = JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            result={"status": "ok"},
        )
        notify_job_terminal(job_id)

    result_a, result_b, _ = await asyncio.gather(
        wait_for_job_terminal(queue, job_id, timeout_seconds=5.0),
        wait_for_job_terminal(queue, job_id, timeout_seconds=5.0),
        _complete_after_delay(),
    )

    assert result_a.status is JobStatus.COMPLETED
    assert result_b.status is JobStatus.COMPLETED


async def test_registry_empty_after_concurrent_completion(
    pending_queue: tuple[InMemoryJobQueue, str],
) -> None:
    """The _terminal_events registry holds no entry for the job after both waiters return."""
    queue, job_id = pending_queue

    async def _complete_after_delay() -> None:
        await asyncio.sleep(0.1)
        entry = queue._jobs[job_id]
        entry.result = JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            result={"status": "ok"},
        )
        notify_job_terminal(job_id)

    await asyncio.gather(
        wait_for_job_terminal(queue, job_id, timeout_seconds=5.0),
        wait_for_job_terminal(queue, job_id, timeout_seconds=5.0),
        _complete_after_delay(),
    )

    assert job_id not in job_completion._terminal_events
