"""Tests for the ``GET /api/v1/jobs/{id}/wait`` long-poll endpoint (BL-277).

Covers the three acceptance criteria:

- FR-001: the endpoint exists, accepts an optional ``timeout`` query param,
  and returns a :class:`JobStatusResponse` body on success.
- FR-002 / INV-LP-2: already-terminal jobs return immediately and the
  handler never allocates an :class:`asyncio.Event` for them.
- FR-003 / INV-LP-3: the endpoint returns HTTP 408 on timeout and the
  timeout is surfaced by catching :class:`asyncio.TimeoutError` (not
  :class:`builtins.TimeoutError`, which is a distinct type on Python 3.10).

Also covers the ordering invariant (INV-LP-1): the queue calls
:func:`notify_job_terminal` *after* the registry write, so waiters always
observe the final status on refetch.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _pending_job(job_queue: InMemoryJobQueue) -> str:
    """Insert a non-terminal job directly into the queue.

    ``InMemoryJobQueue.submit`` runs the handler synchronously and always
    ends in a terminal state, so the long-poll wait path cannot be
    exercised through the normal submit path. The cancel tests use the
    same back-door pattern (see ``test_jobs.py::test_cancel_pending_job``).
    """
    job_id = "long-poll-pending-job"
    entry = _JobEntry(job_id=job_id, job_type="scan", payload={})
    entry.result = JobResult(job_id=job_id, status=JobStatus.PENDING)
    job_queue._jobs[job_id] = entry
    return job_id


@pytest.fixture(autouse=True)
def _clear_terminal_events() -> Iterator[None]:
    """Ensure the module-level event dict starts empty for each test."""
    job_completion._terminal_events.clear()
    yield
    job_completion._terminal_events.clear()


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Async HTTP client bound to the test app via :class:`ASGITransport`.

    Required because the long-poll contract exercises concurrent tasks
    (waiter + notifier) in the same event loop, which
    :class:`fastapi.testclient.TestClient` cannot express.
    """
    # TestClient context drives the lifespan; reuse it to keep the DI-wired
    # state consistent across both client styles.
    with TestClient(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client


# ---------------------------------------------------------------------------
# FR-002 / INV-LP-2: already-terminal short-circuits without creating an Event
# ---------------------------------------------------------------------------


async def test_wait_returns_immediately_for_completed_job(
    async_client: httpx.AsyncClient,
    tmp_path: object,
) -> None:
    """A synchronous scan job is terminal by submit-return; /wait returns 200 at once."""
    submit = await async_client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    assert submit.status_code == 202
    job_id = submit.json()["job_id"]

    response = await async_client.get(f"/api/v1/jobs/{job_id}/wait?timeout=5")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "complete"
    # INV-LP-2: no Event was created because the job was already terminal.
    assert job_id not in job_completion._terminal_events


async def test_wait_default_timeout_applies_when_unspecified(
    async_client: httpx.AsyncClient,
    tmp_path: object,
) -> None:
    """The ``timeout`` query param is optional and defaults to 30 seconds."""
    submit = await async_client.post(
        "/api/v1/videos/scan",
        json={"path": str(tmp_path)},
    )
    job_id = submit.json()["job_id"]

    # Terminal jobs short-circuit; absence of the query param must not 422.
    response = await async_client.get(f"/api/v1/jobs/{job_id}/wait")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# FR-001 / FR-003: 404 + 408 + bounds on the timeout query param
# ---------------------------------------------------------------------------


async def test_wait_returns_404_for_unknown_job(async_client: httpx.AsyncClient) -> None:
    """Unknown job ids produce a 404 with the shared error envelope."""
    response = await async_client.get("/api/v1/jobs/does-not-exist/wait?timeout=1")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


async def test_wait_times_out_with_408_when_job_is_pending(
    async_client: httpx.AsyncClient,
    _pending_job: str,
) -> None:
    """A job stuck in ``PENDING`` yields HTTP 408 after ``timeout`` seconds."""
    start = asyncio.get_running_loop().time()
    response = await async_client.get(f"/api/v1/jobs/{_pending_job}/wait?timeout=1")
    elapsed = asyncio.get_running_loop().time() - start

    assert response.status_code == 408
    assert response.json()["detail"]["code"] == "JOB_WAIT_TIMEOUT"
    # Timeout should be close to the requested value — generous upper bound
    # so CI noise does not flake the test.
    assert 0.9 <= elapsed < 4.0
    # INV-LP-2 cleanup: the finally clause removes the dict entry even on
    # timeout so pending waiters do not leak memory.
    assert _pending_job not in job_completion._terminal_events


@pytest.mark.parametrize("value", [0, 0.5, 3601])
async def test_wait_rejects_out_of_range_timeout(
    async_client: httpx.AsyncClient,
    _pending_job: str,
    value: float,
) -> None:
    """FastAPI enforces the ``ge=1, le=3600`` bounds on the query param."""
    response = await async_client.get(f"/api/v1/jobs/{_pending_job}/wait?timeout={value}")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# FR-002: concurrent notification wakes the waiter and returns 200
# ---------------------------------------------------------------------------


async def test_wait_returns_when_notification_fires(
    async_client: httpx.AsyncClient,
    job_queue: InMemoryJobQueue,
    _pending_job: str,
) -> None:
    """Firing ``notify_job_terminal`` wakes the awaiting request and returns 200."""

    async def _complete_after_delay() -> None:
        await asyncio.sleep(0.2)
        # INV-LP-1: registry write BEFORE notification. The handler should
        # observe the final status on refetch.
        entry = job_queue._jobs[_pending_job]
        entry.result = JobResult(
            job_id=_pending_job,
            status=JobStatus.COMPLETE,
            result={"status": "ok"},
        )
        notify_job_terminal(_pending_job)

    notifier = asyncio.create_task(_complete_after_delay())
    try:
        response = await async_client.get(f"/api/v1/jobs/{_pending_job}/wait?timeout=5")
    finally:
        await notifier

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == _pending_job
    assert body["status"] == "complete"
    assert body["result"] == {"status": "ok"}
    # Cleanup: event dict is emptied after the waiter returns.
    assert _pending_job not in job_completion._terminal_events


# ---------------------------------------------------------------------------
# Service-layer unit tests — easier to assert ordering + cleanup directly
# ---------------------------------------------------------------------------


async def test_wait_for_job_terminal_short_circuits_on_terminal_status(
    job_queue: InMemoryJobQueue,
) -> None:
    """Already-terminal jobs return without creating a dict entry."""
    job_id = "already-done"
    entry = _JobEntry(job_id=job_id, job_type="scan", payload={})
    entry.result = JobResult(job_id=job_id, status=JobStatus.COMPLETE, result={"x": 1})
    job_queue._jobs[job_id] = entry

    result = await wait_for_job_terminal(job_queue, job_id, timeout_seconds=5.0)
    assert result.status is JobStatus.COMPLETE
    assert result.result == {"x": 1}
    assert job_id not in job_completion._terminal_events


async def test_notify_without_waiter_is_noop() -> None:
    """``notify_job_terminal`` is safe when no waiter has registered."""
    notify_job_terminal("nobody-is-listening")
    assert "nobody-is-listening" not in job_completion._terminal_events


async def test_ordering_invariant_registry_write_precedes_notification(
    job_queue: InMemoryJobQueue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-LP-1: when the queue notifies, the registry already holds the final status."""
    observed: list[JobStatus] = []

    # Handler that takes a tick so we can verify the status observed at
    # notification time is the terminal one, not the transitional PENDING.
    async def _handler(job_type: str, payload: dict[str, object]) -> dict[str, str]:
        await asyncio.sleep(0)
        return {"status": "ok"}

    captured_job_id: dict[str, str] = {}

    def _spy(job_id: str) -> None:
        captured_job_id["id"] = job_id
        entry = job_queue._jobs.get(job_id)
        assert entry is not None, "notify_job_terminal fired before registry write"
        observed.append(entry.result.status)

    monkeypatch.setattr(
        "stoat_ferret.jobs.queue.notify_job_terminal",
        _spy,
    )

    job_queue.register_handler("ordering-probe", _handler)
    job_id = await job_queue.submit("ordering-probe", {})

    assert captured_job_id["id"] == job_id
    # The only observation must be terminal — never PENDING/RUNNING.
    assert observed == [JobStatus.COMPLETE]


async def test_concurrent_waiters_share_event_and_both_return(
    job_queue: InMemoryJobQueue,
) -> None:
    """Two concurrent ``/wait`` callers on the same job both observe the terminal result."""
    job_id = "shared-wait"
    entry = _JobEntry(job_id=job_id, job_type="scan", payload={})
    entry.result = JobResult(job_id=job_id, status=JobStatus.PENDING)
    job_queue._jobs[job_id] = entry

    async def _complete() -> None:
        await asyncio.sleep(0.1)
        entry.result = JobResult(
            job_id=job_id,
            status=JobStatus.COMPLETE,
            result={"status": "ok"},
        )
        notify_job_terminal(job_id)

    waiter_a = asyncio.create_task(wait_for_job_terminal(job_queue, job_id, 5.0))
    waiter_b = asyncio.create_task(wait_for_job_terminal(job_queue, job_id, 5.0))
    completer = asyncio.create_task(_complete())

    result_a, result_b, _ = await asyncio.gather(waiter_a, waiter_b, completer)

    assert result_a.status is JobStatus.COMPLETE
    assert result_b.status is JobStatus.COMPLETE
    assert job_id not in job_completion._terminal_events
