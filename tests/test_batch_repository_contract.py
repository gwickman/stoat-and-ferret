"""Contract tests for async BatchRepository implementations.

These tests run against both AsyncSQLiteBatchRepository and
InMemoryBatchRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import aiosqlite
import pytest

from stoat_ferret.db.batch_repository import (
    AsyncBatchRepository,
    AsyncSQLiteBatchRepository,
    InMemoryBatchRepository,
)
from stoat_ferret.db.schema import create_tables_async

AsyncBatchRepositoryType = AsyncSQLiteBatchRepository | InMemoryBatchRepository


@pytest.fixture(params=["sqlite", "memory"])
async def batch_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncBatchRepositoryType, None]:
    """Provide both async batch repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield AsyncSQLiteBatchRepository(conn)
        await conn.close()
    else:
        yield InMemoryBatchRepository()


@pytest.mark.contract
class TestBatchCreate:
    """Tests for create_batch_job() method."""

    async def test_create_returns_record_with_queued_status(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """New batch job starts with queued status and 0.0 progress."""
        record = await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-1",
            project_id="proj-1",
            output_path="/out/1.mp4",
            quality="high",
        )

        assert record.batch_id == "batch-1"
        assert record.job_id == "job-1"
        assert record.project_id == "proj-1"
        assert record.output_path == "/out/1.mp4"
        assert record.quality == "high"
        assert record.status == "queued"
        assert record.progress == 0.0
        assert record.error is None
        assert record.id is not None
        assert record.created_at is not None
        assert record.updated_at is not None

    async def test_create_assigns_unique_ids(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """Each created record gets a unique database ID."""
        r1 = await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-1",
            project_id="p",
            output_path="/o",
            quality="m",
        )
        r2 = await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-2",
            project_id="p",
            output_path="/o",
            quality="m",
        )

        assert r1.id != r2.id


@pytest.mark.contract
class TestBatchGetByBatchId:
    """Tests for get_by_batch_id() method."""

    async def test_empty_batch_returns_empty_list(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """Querying nonexistent batch returns empty list."""
        result = await batch_repository.get_by_batch_id("nonexistent")
        assert result == []

    async def test_returns_all_jobs_in_batch(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """get_by_batch_id returns all jobs sharing a batch_id."""
        await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-1",
            project_id="p1",
            output_path="/o1",
            quality="m",
        )
        await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-2",
            project_id="p2",
            output_path="/o2",
            quality="m",
        )
        await batch_repository.create_batch_job(
            batch_id="batch-2",
            job_id="job-3",
            project_id="p3",
            output_path="/o3",
            quality="m",
        )

        batch1_jobs = await batch_repository.get_by_batch_id("batch-1")
        batch2_jobs = await batch_repository.get_by_batch_id("batch-2")

        assert len(batch1_jobs) == 2
        assert len(batch2_jobs) == 1
        assert {j.job_id for j in batch1_jobs} == {"job-1", "job-2"}

    async def test_returns_records_ordered_by_id(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """Jobs are returned in insertion order (by id)."""
        await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-a",
            project_id="p",
            output_path="/o",
            quality="m",
        )
        await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-b",
            project_id="p",
            output_path="/o",
            quality="m",
        )

        jobs = await batch_repository.get_by_batch_id("batch-1")
        assert jobs[0].job_id == "job-a"
        assert jobs[1].job_id == "job-b"


@pytest.mark.contract
class TestBatchGetByJobId:
    """Tests for get_by_job_id() method."""

    async def test_get_existing_job(self, batch_repository: AsyncBatchRepositoryType) -> None:
        """get_by_job_id returns the correct job."""
        await batch_repository.create_batch_job(
            batch_id="batch-1",
            job_id="job-1",
            project_id="p1",
            output_path="/o1",
            quality="high",
        )

        result = await batch_repository.get_by_job_id("job-1")
        assert result is not None
        assert result.job_id == "job-1"
        assert result.quality == "high"

    async def test_get_nonexistent_returns_none(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """get_by_job_id returns None for nonexistent job."""
        result = await batch_repository.get_by_job_id("nonexistent")
        assert result is None


@pytest.mark.contract
class TestBatchUpdateStatus:
    """Tests for update_status() method."""

    async def test_valid_transition_queued_to_running(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """queued -> running is a valid transition."""
        await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )

        await batch_repository.update_status("j1", "running")

        job = await batch_repository.get_by_job_id("j1")
        assert job is not None
        assert job.status == "running"

    async def test_valid_transition_running_to_completed(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """running -> completed is a valid transition."""
        await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )
        await batch_repository.update_status("j1", "running")
        await batch_repository.update_status("j1", "completed")

        job = await batch_repository.get_by_job_id("j1")
        assert job is not None
        assert job.status == "completed"

    async def test_valid_transition_running_to_failed_with_error(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """running -> failed sets error message."""
        await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )
        await batch_repository.update_status("j1", "running")
        await batch_repository.update_status("j1", "failed", error="render crashed")

        job = await batch_repository.get_by_job_id("j1")
        assert job is not None
        assert job.status == "failed"
        assert job.error == "render crashed"

    async def test_invalid_transition_queued_to_completed_raises(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """queued -> completed is not allowed."""
        await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )

        with pytest.raises(ValueError, match="Invalid status transition"):
            await batch_repository.update_status("j1", "completed")

    async def test_invalid_transition_completed_to_running_raises(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """completed -> running is not allowed (terminal state)."""
        await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )
        await batch_repository.update_status("j1", "running")
        await batch_repository.update_status("j1", "completed")

        with pytest.raises(ValueError, match="Invalid status transition"):
            await batch_repository.update_status("j1", "running")

    async def test_update_nonexistent_job_raises(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """Updating status of nonexistent job raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await batch_repository.update_status("nonexistent", "running")

    async def test_update_status_updates_timestamp(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """Status update changes updated_at timestamp."""
        record = await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )
        original_updated = record.updated_at

        await batch_repository.update_status("j1", "running")

        job = await batch_repository.get_by_job_id("j1")
        assert job is not None
        assert job.updated_at >= original_updated


@pytest.mark.contract
class TestBatchUpdateProgress:
    """Tests for update_progress() method."""

    async def test_update_progress_value(self, batch_repository: AsyncBatchRepositoryType) -> None:
        """Progress value is correctly updated."""
        await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )

        await batch_repository.update_progress("j1", 0.5)

        job = await batch_repository.get_by_job_id("j1")
        assert job is not None
        assert job.progress == pytest.approx(0.5)

    async def test_update_progress_nonexistent_raises(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """Updating progress of nonexistent job raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await batch_repository.update_progress("nonexistent", 0.5)

    async def test_update_progress_updates_timestamp(
        self, batch_repository: AsyncBatchRepositoryType
    ) -> None:
        """Progress update changes updated_at timestamp."""
        record = await batch_repository.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )
        original_updated = record.updated_at

        await batch_repository.update_progress("j1", 0.75)

        job = await batch_repository.get_by_job_id("j1")
        assert job is not None
        assert job.updated_at >= original_updated


@pytest.mark.contract
class TestBatchProtocolCompliance:
    """Tests for protocol compliance."""

    def test_sqlite_implements_protocol(self) -> None:
        """AsyncSQLiteBatchRepository is a runtime_checkable Protocol impl."""
        assert issubclass(AsyncSQLiteBatchRepository, AsyncBatchRepository)

    def test_inmemory_implements_protocol(self) -> None:
        """InMemoryBatchRepository is a runtime_checkable Protocol impl."""
        assert issubclass(InMemoryBatchRepository, AsyncBatchRepository)


@pytest.mark.contract
class TestBatchDeepCopyIsolation:
    """Tests for deepcopy isolation in InMemory implementation."""

    async def test_returned_record_is_isolated(self) -> None:
        """Mutating a returned record does not affect stored state."""
        repo = InMemoryBatchRepository()
        record = await repo.create_batch_job(
            batch_id="b",
            job_id="j1",
            project_id="p",
            output_path="/o",
            quality="m",
        )

        # Mutate the returned record
        record.status = "MUTATED"

        # Fetch again - should be unchanged
        fetched = await repo.get_by_job_id("j1")
        assert fetched is not None
        assert fetched.status == "queued"
