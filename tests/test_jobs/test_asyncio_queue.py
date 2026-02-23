"""Tests for AsyncioJobQueue.

Verifies submit, status polling, completion, failure, and timeout behavior.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from stoat_ferret.jobs.queue import AsyncioJobQueue, JobStatus


async def _success_handler(job_type: str, payload: dict[str, Any]) -> dict[str, str]:
    """Handler that succeeds immediately."""
    return {"status": "done", "type": job_type}


async def _slow_handler(job_type: str, payload: dict[str, Any]) -> str:
    """Handler that sleeps longer than a short timeout."""
    await asyncio.sleep(10)
    return "should not reach"


async def _failing_handler(job_type: str, payload: dict[str, Any]) -> None:
    """Handler that raises an exception."""
    raise RuntimeError("something went wrong")


class TestSubmitAndStatus:
    """Tests for submit() and get_status()."""

    async def test_submit_returns_job_id(self) -> None:
        """Submit returns a unique job ID string."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _success_handler)
        job_id = await queue.submit("render", {})
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    async def test_submit_generates_unique_ids(self) -> None:
        """Each submit call generates a different job ID."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _success_handler)
        id1 = await queue.submit("render", {})
        id2 = await queue.submit("render", {})
        assert id1 != id2

    async def test_initial_status_is_pending(self) -> None:
        """Job starts in PENDING status before worker processes it."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _success_handler)
        job_id = await queue.submit("render", {})
        status = await queue.get_status(job_id)
        assert status == JobStatus.PENDING

    async def test_get_status_unknown_job_raises(self) -> None:
        """Getting status for unknown job raises KeyError."""
        queue = AsyncioJobQueue()
        with pytest.raises(KeyError):
            await queue.get_status("nonexistent")

    async def test_get_result_unknown_job_raises(self) -> None:
        """Getting result for unknown job raises KeyError."""
        queue = AsyncioJobQueue()
        with pytest.raises(KeyError):
            await queue.get_result("nonexistent")


class TestJobCompletion:
    """Tests for successful job completion via worker."""

    async def test_job_completes_successfully(self) -> None:
        """Worker processes job and sets COMPLETE status."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _success_handler)

        job_id = await queue.submit("render", {"file": "test.mp4"})

        worker = asyncio.create_task(queue.process_jobs())
        try:
            # Give worker time to process
            await asyncio.sleep(0.05)

            status = await queue.get_status(job_id)
            assert status == JobStatus.COMPLETE

            result = await queue.get_result(job_id)
            assert result.status == JobStatus.COMPLETE
            assert result.result == {"status": "done", "type": "render"}
            assert result.error is None
        finally:
            worker.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker

    async def test_multiple_jobs_processed_in_order(self) -> None:
        """Worker processes multiple jobs sequentially."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _success_handler)

        id1 = await queue.submit("render", {})
        id2 = await queue.submit("render", {})

        worker = asyncio.create_task(queue.process_jobs())
        try:
            await asyncio.sleep(0.05)

            r1 = await queue.get_result(id1)
            r2 = await queue.get_result(id2)
            assert r1.status == JobStatus.COMPLETE
            assert r2.status == JobStatus.COMPLETE
        finally:
            worker.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker


class TestJobFailure:
    """Tests for job failure scenarios."""

    async def test_handler_exception_sets_failed_status(self) -> None:
        """Handler exception results in FAILED status with error message."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _failing_handler)

        job_id = await queue.submit("render", {})

        worker = asyncio.create_task(queue.process_jobs())
        try:
            await asyncio.sleep(0.05)

            result = await queue.get_result(job_id)
            assert result.status == JobStatus.FAILED
            assert result.error == "something went wrong"
        finally:
            worker.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker

    async def test_no_handler_sets_failed_status(self) -> None:
        """Submitting a job with no registered handler results in FAILED."""
        queue = AsyncioJobQueue()
        # No handler registered for "unknown"

        job_id = await queue.submit("unknown", {})

        worker = asyncio.create_task(queue.process_jobs())
        try:
            await asyncio.sleep(0.05)

            result = await queue.get_result(job_id)
            assert result.status == JobStatus.FAILED
            assert "No handler registered" in (result.error or "")
        finally:
            worker.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker


class TestJobTimeout:
    """Tests for job timeout behavior."""

    async def test_timeout_sets_timeout_status(self) -> None:
        """Job exceeding timeout gets TIMEOUT status."""
        queue = AsyncioJobQueue(timeout=0.05)
        queue.register_handler("slow", _slow_handler)

        job_id = await queue.submit("slow", {})

        worker = asyncio.create_task(queue.process_jobs())
        try:
            await asyncio.sleep(0.2)

            result = await queue.get_result(job_id)
            assert result.status == JobStatus.TIMEOUT
            assert "timed out" in (result.error or "")
        finally:
            worker.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker

    async def test_custom_timeout_is_used(self) -> None:
        """Queue uses the configured timeout value."""
        queue = AsyncioJobQueue(timeout=42.0)
        assert queue._timeout == 42.0

    async def test_default_timeout_is_300(self) -> None:
        """Default timeout is 5 minutes (300 seconds)."""
        queue = AsyncioJobQueue()
        assert queue._timeout == 300.0


class TestProgress:
    """Tests for progress tracking."""

    async def test_entry_initializes_with_progress_none(self) -> None:
        """_AsyncJobEntry initializes with progress = None."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _success_handler)
        job_id = await queue.submit("render", {})
        result = await queue.get_result(job_id)
        assert result.progress is None

    async def test_set_progress_updates_entry(self) -> None:
        """set_progress updates the job's progress field."""
        queue = AsyncioJobQueue()
        queue.register_handler("render", _success_handler)
        job_id = await queue.submit("render", {})
        queue.set_progress(job_id, 0.5)
        result = await queue.get_result(job_id)
        assert result.progress == 0.5

    async def test_set_progress_unknown_job_is_noop(self) -> None:
        """set_progress with invalid job_id is a no-op."""
        queue = AsyncioJobQueue()
        # Should not raise
        queue.set_progress("nonexistent", 0.5)

    async def test_progress_preserved_after_completion(self) -> None:
        """Progress value is preserved in result after job completes."""
        queue = AsyncioJobQueue()
        progress_values: list[float] = []

        async def tracking_handler(job_type: str, payload: dict[str, Any]) -> str:
            """Handler that sets progress via the queue."""
            job_id = payload.get("_job_id", "")
            queue.set_progress(job_id, 0.5)
            progress_values.append(0.5)
            queue.set_progress(job_id, 1.0)
            progress_values.append(1.0)
            return "done"

        queue.register_handler("render", tracking_handler)
        job_id = await queue.submit("render", {})

        worker = asyncio.create_task(queue.process_jobs())
        try:
            await asyncio.sleep(0.05)

            result = await queue.get_result(job_id)
            assert result.status == JobStatus.COMPLETE
            assert result.progress == 1.0
            assert progress_values == [0.5, 1.0]
        finally:
            worker.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker
