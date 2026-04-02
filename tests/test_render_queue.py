"""Tests for the render queue with concurrency control and persistence."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
import structlog
from structlog.testing import capture_logs

from stoat_ferret.render.models import (
    OutputFormat,
    QualityPreset,
    RenderJob,
    RenderStatus,
)
from stoat_ferret.render.queue import QueueFullError, RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository


def _make_job(project_id: str = "proj-1") -> RenderJob:
    """Create a test render job in queued status."""
    return RenderJob.create(
        project_id=project_id,
        output_path=f"/tmp/{project_id}/output.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan="{}",
    )


@pytest.fixture()
def repo() -> InMemoryRenderRepository:
    """Fresh in-memory render repository."""
    return InMemoryRenderRepository()


@pytest.fixture()
def queue(repo: InMemoryRenderRepository) -> RenderQueue:
    """Queue with small limits for testing (max_concurrent=2, max_depth=3)."""
    return RenderQueue(repo, max_concurrent=2, max_depth=3)


# ---------------------------------------------------------------------------
# Enqueue tests
# ---------------------------------------------------------------------------


class TestEnqueue:
    """Tests for enqueue behavior."""

    async def test_enqueue_persists_job(
        self, queue: RenderQueue, repo: InMemoryRenderRepository
    ) -> None:
        """Enqueued job is persisted via the repository."""
        job = _make_job()
        result = await queue.enqueue(job)
        assert result.id == job.id
        stored = await repo.get(job.id)
        assert stored is not None
        assert stored.status == RenderStatus.QUEUED

    async def test_enqueue_increments_queue_depth(self, queue: RenderQueue) -> None:
        """Each enqueue increases the queue depth."""
        await queue.enqueue(_make_job())
        assert await queue.get_queue_depth() == 1
        await queue.enqueue(_make_job())
        assert await queue.get_queue_depth() == 2

    async def test_enqueue_rejects_when_full(self, queue: RenderQueue) -> None:
        """Enqueue raises QueueFullError when max_depth is reached."""
        for _ in range(3):
            await queue.enqueue(_make_job())

        with pytest.raises(QueueFullError) as exc_info:
            await queue.enqueue(_make_job())
        assert exc_info.value.queue_depth == 3
        assert exc_info.value.max_depth == 3

    async def test_enqueue_structured_error_message(self, queue: RenderQueue) -> None:
        """QueueFullError string contains the depth numbers."""
        for _ in range(3):
            await queue.enqueue(_make_job())

        with pytest.raises(QueueFullError) as exc_info:
            await queue.enqueue(_make_job())
        assert "3/3" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Dequeue tests
# ---------------------------------------------------------------------------


class TestDequeue:
    """Tests for dequeue behavior."""

    async def test_dequeue_returns_none_when_empty(self, queue: RenderQueue) -> None:
        """Dequeue on an empty queue returns None."""
        result = await queue.dequeue()
        assert result is None

    async def test_dequeue_transitions_to_running(self, queue: RenderQueue) -> None:
        """Dequeued job has running status."""
        job = _make_job()
        await queue.enqueue(job)
        result = await queue.dequeue()
        assert result is not None
        assert result.id == job.id
        assert result.status == RenderStatus.RUNNING

    async def test_dequeue_respects_max_concurrent(self, queue: RenderQueue) -> None:
        """Dequeue returns None when max_concurrent running jobs exist."""
        # max_concurrent=2
        for _ in range(3):
            await queue.enqueue(_make_job())

        first = await queue.dequeue()
        assert first is not None
        second = await queue.dequeue()
        assert second is not None
        third = await queue.dequeue()
        assert third is None  # max_concurrent reached
        assert await queue.get_active_count() == 2

    async def test_dequeue_fifo_ordering(self, repo: InMemoryRenderRepository) -> None:
        """Jobs are dequeued in FIFO order by created_at."""
        queue = RenderQueue(repo, max_concurrent=10, max_depth=10)
        jobs = []
        for i in range(3):
            job = _make_job(project_id=f"proj-{i}")
            jobs.append(job)
            await queue.enqueue(job)

        for expected_job in jobs:
            result = await queue.dequeue()
            assert result is not None
            assert result.id == expected_job.id


# ---------------------------------------------------------------------------
# Recovery tests
# ---------------------------------------------------------------------------


class TestRecovery:
    """Tests for restart recovery."""

    async def test_recover_marks_running_as_failed(
        self, queue: RenderQueue, repo: InMemoryRenderRepository
    ) -> None:
        """Recovery marks running jobs as failed with an error message."""
        job = _make_job()
        await queue.enqueue(job)
        await queue.dequeue()  # transitions to running

        recovered = await queue.recover()
        assert len(recovered) == 1
        assert recovered[0].id == job.id

        updated = await repo.get(job.id)
        assert updated is not None
        assert updated.status == RenderStatus.FAILED
        assert "restart" in (updated.error_message or "").lower()

    async def test_recover_leaves_queued_jobs_untouched(
        self, queue: RenderQueue, repo: InMemoryRenderRepository
    ) -> None:
        """Recovery does not affect queued jobs."""
        job = _make_job()
        await queue.enqueue(job)

        recovered = await queue.recover()
        assert len(recovered) == 0

        stored = await repo.get(job.id)
        assert stored is not None
        assert stored.status == RenderStatus.QUEUED

    async def test_recover_handles_multiple_running_jobs(
        self, repo: InMemoryRenderRepository
    ) -> None:
        """Recovery handles all running jobs from a previous run."""
        queue = RenderQueue(repo, max_concurrent=5, max_depth=10)
        for _ in range(3):
            await queue.enqueue(_make_job())
            await queue.dequeue()

        recovered = await queue.recover()
        assert len(recovered) == 3

    async def test_recover_empty_returns_empty_list(self, queue: RenderQueue) -> None:
        """Recovery with no running jobs returns an empty list."""
        recovered = await queue.recover()
        assert recovered == []


# ---------------------------------------------------------------------------
# Structured logging tests
# ---------------------------------------------------------------------------


class TestStructuredLogging:
    """Tests for structured log events."""

    @pytest.fixture(autouse=True)
    def _reset_structlog(self) -> Iterator[None]:
        """Reset structlog so capture_logs() works after other tests configure it.

        Other test modules (test_logging*.py, test_observable.py) call
        configure_logging() or structlog.configure() which replaces the
        processor chain.  capture_logs() only works when structlog uses
        its default lazy-proxy loggers, so we reset AND clear any cached
        bound loggers before each test.
        """
        structlog.reset_defaults()
        structlog.configure(cache_logger_on_first_use=False)
        yield
        structlog.reset_defaults()

    async def test_enqueue_logs_event(self, queue: RenderQueue) -> None:
        """Enqueue emits a render_queue.enqueue log event."""
        with capture_logs() as cap_logs:
            job = _make_job()
            await queue.enqueue(job)

        events = [e for e in cap_logs if e.get("event") == "render_queue.enqueue"]
        assert len(events) == 1
        assert events[0]["job_id"] == job.id

    async def test_dequeue_logs_event(self, queue: RenderQueue) -> None:
        """Dequeue emits a render_queue.dequeue log event."""
        job = _make_job()
        await queue.enqueue(job)
        with capture_logs() as cap_logs:
            await queue.dequeue()

        events = [e for e in cap_logs if e.get("event") == "render_queue.dequeue"]
        assert len(events) == 1
        assert events[0]["job_id"] == job.id

    async def test_capacity_reached_logs_event(self, queue: RenderQueue) -> None:
        """Capacity reached emits a render_queue.capacity_reached log event."""
        for _ in range(3):
            await queue.enqueue(_make_job())

        with capture_logs() as cap_logs, pytest.raises(QueueFullError):
            await queue.enqueue(_make_job())

        events = [e for e in cap_logs if e.get("event") == "render_queue.capacity_reached"]
        assert len(events) == 1

    async def test_recovery_logs_events(self, queue: RenderQueue) -> None:
        """Recovery emits render_queue.recovery log events."""
        await queue.enqueue(_make_job())
        await queue.dequeue()

        with capture_logs() as cap_logs:
            await queue.recover()

        events = [e for e in cap_logs if e.get("event") == "render_queue.recovery"]
        assert len(events) == 1


# ---------------------------------------------------------------------------
# Concurrent operations
# ---------------------------------------------------------------------------


class TestConcurrentOperations:
    """Tests for concurrent enqueue/dequeue safety."""

    async def test_concurrent_dequeue_respects_max_concurrent(
        self, repo: InMemoryRenderRepository
    ) -> None:
        """Concurrent dequeue calls do not exceed max_concurrent."""
        queue = RenderQueue(repo, max_concurrent=2, max_depth=10)
        for _ in range(5):
            await queue.enqueue(_make_job())

        results = await asyncio.gather(
            queue.dequeue(),
            queue.dequeue(),
            queue.dequeue(),
            queue.dequeue(),
        )
        running = [r for r in results if r is not None]
        # Lock serializes dequeue, so exactly 2 should succeed
        assert len(running) == 2
        assert await queue.get_active_count() == 2


# ---------------------------------------------------------------------------
# Simulated restart (persistence)
# ---------------------------------------------------------------------------


class TestSimulatedRestart:
    """Tests for queue state persistence across simulated restarts."""

    async def test_queue_state_persists_across_restart(
        self, repo: InMemoryRenderRepository
    ) -> None:
        """A new RenderQueue on the same repo sees prior state."""
        # Phase 1: enqueue and dequeue some jobs
        queue1 = RenderQueue(repo, max_concurrent=2, max_depth=10)
        job1 = _make_job(project_id="proj-a")
        job2 = _make_job(project_id="proj-b")
        job3 = _make_job(project_id="proj-c")
        await queue1.enqueue(job1)
        await queue1.enqueue(job2)
        await queue1.enqueue(job3)
        await queue1.dequeue()  # job1 -> running

        # Phase 2: simulate restart — new queue instance, same repo
        queue2 = RenderQueue(repo, max_concurrent=2, max_depth=10)

        # Verify state survived
        assert await queue2.get_active_count() == 1  # job1 still "running"
        assert await queue2.get_queue_depth() == 2  # job2, job3 still queued

        # Recover interrupts
        recovered = await queue2.recover()
        assert len(recovered) == 1
        assert recovered[0].id == job1.id

        # After recovery, queue is clean
        assert await queue2.get_active_count() == 0
        assert await queue2.get_queue_depth() == 2
