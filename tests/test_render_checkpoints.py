"""Tests for render checkpoint manager.

Covers checkpoint write/read, unique constraint enforcement, recovery
scan, resume logic, full lifecycle, stale cleanup, and structured logging.
"""

from __future__ import annotations

import sqlite3
from collections.abc import AsyncGenerator

import aiosqlite
import pytest
import structlog

from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.models import (
    OutputFormat,
    QualityPreset,
    RenderJob,
)


@pytest.fixture
async def db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide an in-memory SQLite database with schema created."""
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA foreign_keys = ON")
    await create_tables_async(conn)
    yield conn
    await conn.close()


@pytest.fixture
async def manager(db: aiosqlite.Connection) -> RenderCheckpointManager:
    """Provide a RenderCheckpointManager backed by the test database."""
    return RenderCheckpointManager(db)


async def _insert_job(
    db: aiosqlite.Connection,
    job_id: str = "job-1",
    status: str = "running",
    project_id: str = "proj-1",
) -> None:
    """Insert a render job row directly for testing."""
    job = RenderJob.create(
        project_id=project_id,
        output_path="/out/video.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan='{"segments": []}',
    )
    await db.execute(
        """
        INSERT INTO render_jobs
            (id, project_id, status, output_path, output_format,
             quality_preset, render_plan, progress, error_message,
             retry_count, created_at, updated_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            project_id,
            status,
            job.output_path,
            job.output_format.value,
            job.quality_preset.value,
            job.render_plan,
            job.progress,
            job.error_message,
            job.retry_count,
            job.created_at.isoformat(),
            job.updated_at.isoformat(),
            None,
        ),
    )
    await db.commit()


class TestWriteCheckpoint:
    """Tests for write_checkpoint."""

    async def test_write_and_read(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Checkpoint is persisted and can be read back."""
        await _insert_job(db, "job-1")
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-1", 1)
        segments = await manager.get_completed_segments("job-1")
        assert segments == [0, 1]

    async def test_write_stores_completed_at(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Checkpoint row includes a completed_at timestamp."""
        await _insert_job(db, "job-1")
        await manager.write_checkpoint("job-1", 0)
        cursor = await db.execute(
            "SELECT completed_at FROM render_checkpoints WHERE job_id = ?",
            ("job-1",),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] is not None  # ISO 8601 timestamp

    async def test_negative_segment_raises(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Negative segment_index raises ValueError."""
        await _insert_job(db, "job-1")
        with pytest.raises(ValueError, match="non-negative"):
            await manager.write_checkpoint("job-1", -1)


class TestUniqueConstraint:
    """Tests for (job_id, segment_index) unique constraint."""

    async def test_duplicate_raises_integrity_error(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Inserting the same (job_id, segment_index) twice raises IntegrityError."""
        await _insert_job(db, "job-1")
        await manager.write_checkpoint("job-1", 0)
        with pytest.raises(sqlite3.IntegrityError):
            await manager.write_checkpoint("job-1", 0)

    async def test_same_segment_different_jobs(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Same segment_index is allowed for different jobs."""
        await _insert_job(db, "job-1")
        await _insert_job(db, "job-2")
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-2", 0)
        assert await manager.get_completed_segments("job-1") == [0]
        assert await manager.get_completed_segments("job-2") == [0]


class TestGetCompletedSegments:
    """Tests for get_completed_segments."""

    async def test_empty_for_unknown_job(self, manager: RenderCheckpointManager) -> None:
        """Returns empty list for a job with no checkpoints."""
        assert await manager.get_completed_segments("nonexistent") == []

    async def test_returns_sorted(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Segments are returned in ascending order."""
        await _insert_job(db, "job-1")
        await manager.write_checkpoint("job-1", 2)
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-1", 1)
        assert await manager.get_completed_segments("job-1") == [0, 1, 2]


class TestGetNextSegment:
    """Tests for get_next_segment."""

    async def test_no_checkpoints_returns_zero(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """With no checkpoints, next segment is 0."""
        await _insert_job(db, "job-1")
        assert await manager.get_next_segment("job-1", 5) == 0

    async def test_partial_progress(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """With segments 0-2 done, next is 3."""
        await _insert_job(db, "job-1")
        for i in range(3):
            await manager.write_checkpoint("job-1", i)
        assert await manager.get_next_segment("job-1", 5) == 3

    async def test_all_done_returns_none(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Returns None when all segments are complete."""
        await _insert_job(db, "job-1")
        for i in range(3):
            await manager.write_checkpoint("job-1", i)
        assert await manager.get_next_segment("job-1", 3) is None


class TestRecover:
    """Tests for recovery scan."""

    async def test_finds_running_jobs(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Recovery finds jobs with status='running'."""
        await _insert_job(db, "job-1", status="running")
        await _insert_job(db, "job-2", status="queued")
        await _insert_job(db, "job-3", status="running")
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-1", 1)
        results = await manager.recover()
        job_ids = [r[0] for r in results]
        assert "job-1" in job_ids
        assert "job-3" in job_ids
        assert "job-2" not in job_ids

    async def test_recovery_next_segment(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Recovery returns checkpoint count as next segment."""
        await _insert_job(db, "job-1", status="running")
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-1", 1)
        results = await manager.recover()
        assert ("job-1", 2) in results

    async def test_no_running_jobs(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Recovery returns empty when no running jobs exist."""
        await _insert_job(db, "job-1", status="completed")
        assert await manager.recover() == []


class TestCleanupStale:
    """Tests for stale checkpoint cleanup."""

    async def test_cleanup_deletes_checkpoints(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Cleanup removes checkpoints for specified job IDs."""
        await _insert_job(db, "job-1")
        await _insert_job(db, "job-2")
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-1", 1)
        await manager.write_checkpoint("job-2", 0)
        deleted = await manager.cleanup_stale(["job-1"])
        assert deleted == 2
        assert await manager.get_completed_segments("job-1") == []
        assert await manager.get_completed_segments("job-2") == [0]

    async def test_cleanup_multiple_jobs(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Cleanup removes checkpoints for multiple jobs at once."""
        await _insert_job(db, "job-1")
        await _insert_job(db, "job-2")
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-2", 0)
        deleted = await manager.cleanup_stale(["job-1", "job-2"])
        assert deleted == 2

    async def test_cleanup_empty_list(self, manager: RenderCheckpointManager) -> None:
        """Cleanup with empty list is a no-op."""
        assert await manager.cleanup_stale([]) == 0

    async def test_cleanup_nonexistent_job(self, manager: RenderCheckpointManager) -> None:
        """Cleanup for nonexistent jobs returns 0."""
        assert await manager.cleanup_stale(["no-such-job"]) == 0


class TestFullLifecycle:
    """Integration test for the full recovery lifecycle."""

    async def test_create_partial_crash_resume(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Full lifecycle: create job -> complete 2 of 5 -> crash -> resume from 3."""
        # Create a running job
        await _insert_job(db, "job-1", status="running")

        # Complete segments 0 and 1
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-1", 1)

        # Simulate crash -> recovery
        results = await manager.recover()
        assert len(results) == 1
        job_id, next_seg = results[0]
        assert job_id == "job-1"
        assert next_seg == 2  # 2 checkpoints completed

        # Verify get_next_segment agrees
        next_from_method = await manager.get_next_segment("job-1", 5)
        assert next_from_method == 2

        # Resume rendering segments 2, 3, 4
        for i in range(2, 5):
            await manager.write_checkpoint("job-1", i)

        # All segments done
        assert await manager.get_next_segment("job-1", 5) is None
        assert await manager.get_completed_segments("job-1") == [0, 1, 2, 3, 4]

    async def test_orphaned_cleanup_after_cancellation(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """Checkpoints are cleaned up for cancelled jobs."""
        await _insert_job(db, "job-1")
        await manager.write_checkpoint("job-1", 0)
        await manager.write_checkpoint("job-1", 1)

        # Mark job as cancelled (job row still exists)
        await db.execute(
            "UPDATE render_jobs SET status = 'cancelled' WHERE id = ?",
            ("job-1",),
        )
        await db.commit()

        # Cleanup stale checkpoints
        deleted = await manager.cleanup_stale(["job-1"])
        assert deleted == 2
        assert await manager.get_completed_segments("job-1") == []

    async def test_cascade_deletes_checkpoints(
        self, db: aiosqlite.Connection, manager: RenderCheckpointManager
    ) -> None:
        """ON DELETE CASCADE removes checkpoints when job is deleted."""
        await _insert_job(db, "job-1")
        await manager.write_checkpoint("job-1", 0)

        await db.execute("DELETE FROM render_jobs WHERE id = ?", ("job-1",))
        await db.commit()

        assert await manager.get_completed_segments("job-1") == []


class TestStructuredLogging:
    """Tests for structured logging events."""

    @pytest.fixture(autouse=True)
    def _reset_structlog(self) -> None:
        """Reset structlog to defaults before each test.

        When tests that create TestClient run before this class, the
        lifespan's configure_logging() configures structlog with a stdlib
        integration that prevents capture_logs() from intercepting events.
        Resetting ensures capture_logs() works regardless of test ordering.
        """
        structlog.reset_defaults()

    async def test_write_logs_event(
        self,
        db: aiosqlite.Connection,
        manager: RenderCheckpointManager,
    ) -> None:
        """write_checkpoint emits a log event."""
        await _insert_job(db, "job-1")
        with structlog.testing.capture_logs() as logs:
            await manager.write_checkpoint("job-1", 0)
        assert any(log.get("event") == "render_checkpoint.write" for log in logs)

    async def test_recovery_logs_event(
        self,
        db: aiosqlite.Connection,
        manager: RenderCheckpointManager,
    ) -> None:
        """recover() emits a recovery log event."""
        await _insert_job(db, "job-1", status="running")
        with structlog.testing.capture_logs() as logs:
            await manager.recover()
        assert any(log.get("event") == "render_checkpoint.recovery" for log in logs)

    async def test_resume_logs_event(
        self,
        db: aiosqlite.Connection,
        manager: RenderCheckpointManager,
    ) -> None:
        """recover() emits resume log events for each interrupted job."""
        await _insert_job(db, "job-1", status="running")
        with structlog.testing.capture_logs() as logs:
            await manager.recover()
        assert any(log.get("event") == "render_checkpoint.resume" for log in logs)

    async def test_cleanup_logs_event(
        self,
        db: aiosqlite.Connection,
        manager: RenderCheckpointManager,
    ) -> None:
        """cleanup_stale emits a cleanup log event."""
        await _insert_job(db, "job-1")
        await manager.write_checkpoint("job-1", 0)
        with structlog.testing.capture_logs() as logs:
            await manager.cleanup_stale(["job-1"])
        assert any(log.get("event") == "render_checkpoint.cleanup" for log in logs)
