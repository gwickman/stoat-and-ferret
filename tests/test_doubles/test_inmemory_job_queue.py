"""Tests for InMemoryJobQueue.

Verifies submit, status, completion, failure, and configurable outcomes.
"""

from __future__ import annotations

import pytest

from stoat_ferret.jobs.queue import InMemoryJobQueue, JobOutcome, JobStatus


class TestSubmitAndStatus:
    """Tests for submit() and get_status()."""

    async def test_submit_returns_job_id(self) -> None:
        """Submit returns a unique job ID string."""
        queue = InMemoryJobQueue()
        job_id = await queue.submit("render", {"project_id": "p1"})
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    async def test_submit_generates_unique_ids(self) -> None:
        """Each submit call generates a different job ID."""
        queue = InMemoryJobQueue()
        id1 = await queue.submit("render", {})
        id2 = await queue.submit("render", {})
        assert id1 != id2

    async def test_default_outcome_is_complete(self) -> None:
        """Jobs complete successfully by default."""
        queue = InMemoryJobQueue()
        job_id = await queue.submit("render", {})
        status = await queue.get_status(job_id)
        assert status == JobStatus.COMPLETE


class TestGetResult:
    """Tests for get_result()."""

    async def test_successful_result(self) -> None:
        """Successful job has COMPLETE status and a result."""
        queue = InMemoryJobQueue()
        job_id = await queue.submit("render", {"project_id": "p1"})
        result = await queue.get_result(job_id)

        assert result.job_id == job_id
        assert result.status == JobStatus.COMPLETE
        assert result.result is not None
        assert result.error is None

    async def test_custom_success_result(self) -> None:
        """Configured success result is returned."""
        queue = InMemoryJobQueue()
        queue.configure_outcome("render", JobOutcome.SUCCESS, result={"output": "/tmp/out.mp4"})
        job_id = await queue.submit("render", {})
        result = await queue.get_result(job_id)

        assert result.status == JobStatus.COMPLETE
        assert result.result == {"output": "/tmp/out.mp4"}

    async def test_get_result_unknown_job_raises(self) -> None:
        """Getting result for unknown job raises KeyError."""
        queue = InMemoryJobQueue()
        with pytest.raises(KeyError):
            await queue.get_result("nonexistent")

    async def test_get_status_unknown_job_raises(self) -> None:
        """Getting status for unknown job raises KeyError."""
        queue = InMemoryJobQueue()
        with pytest.raises(KeyError):
            await queue.get_status("nonexistent")


class TestConfigurableOutcomes:
    """Tests for configurable job outcomes."""

    async def test_failure_outcome(self) -> None:
        """Configured failure produces FAILED status with error message."""
        queue = InMemoryJobQueue()
        queue.configure_outcome("render", JobOutcome.FAILURE, error="out of disk space")
        job_id = await queue.submit("render", {})
        result = await queue.get_result(job_id)

        assert result.status == JobStatus.FAILED
        assert result.error == "out of disk space"
        assert result.result is None

    async def test_timeout_outcome(self) -> None:
        """Configured timeout produces TIMEOUT status with error message."""
        queue = InMemoryJobQueue()
        queue.configure_outcome("render", JobOutcome.TIMEOUT, error="exceeded 30s")
        job_id = await queue.submit("render", {})
        result = await queue.get_result(job_id)

        assert result.status == JobStatus.TIMEOUT
        assert result.error == "exceeded 30s"
        assert result.result is None

    async def test_different_types_different_outcomes(self) -> None:
        """Different job types can have different configured outcomes."""
        queue = InMemoryJobQueue()
        queue.configure_outcome("render", JobOutcome.SUCCESS, result="ok")
        queue.configure_outcome("export", JobOutcome.FAILURE, error="not supported")

        render_id = await queue.submit("render", {})
        export_id = await queue.submit("export", {})

        render_result = await queue.get_result(render_id)
        export_result = await queue.get_result(export_id)

        assert render_result.status == JobStatus.COMPLETE
        assert export_result.status == JobStatus.FAILED

    async def test_default_outcome_can_be_changed(self) -> None:
        """set_default_outcome changes behavior for unconfigured types."""
        queue = InMemoryJobQueue()
        queue.set_default_outcome(JobOutcome.FAILURE)

        job_id = await queue.submit("unknown_type", {})
        result = await queue.get_result(job_id)

        assert result.status == JobStatus.FAILED


class TestSetProgress:
    """Tests for set_progress() no-op."""

    async def test_set_progress_is_noop(self) -> None:
        """set_progress does not raise and has no effect."""
        queue = InMemoryJobQueue()
        job_id = await queue.submit("render", {})
        # Should not raise
        queue.set_progress(job_id, 0.5)

    async def test_set_progress_unknown_job_is_noop(self) -> None:
        """set_progress with unknown job_id does not raise."""
        queue = InMemoryJobQueue()
        queue.set_progress("nonexistent", 0.5)


class TestCancel:
    """Tests for cancel() no-op."""

    async def test_cancel_is_noop(self) -> None:
        """cancel does not raise and has no effect."""
        queue = InMemoryJobQueue()
        job_id = await queue.submit("render", {})
        # Should not raise
        queue.cancel(job_id)

    async def test_cancel_unknown_job_is_noop(self) -> None:
        """cancel with unknown job_id does not raise."""
        queue = InMemoryJobQueue()
        queue.cancel("nonexistent")
