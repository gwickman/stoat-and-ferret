"""Contract tests for async RenderRepository implementations.

These tests run against both AsyncSQLiteRenderRepository and
InMemoryRenderRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.render.models import (
    OutputFormat,
    QualityPreset,
    RenderJob,
    RenderStatus,
)
from stoat_ferret.render.render_repository import (
    AsyncRenderRepository,
    AsyncSQLiteRenderRepository,
    InMemoryRenderRepository,
)

AsyncRenderRepositoryType = AsyncSQLiteRenderRepository | InMemoryRenderRepository


@pytest.fixture(params=["sqlite", "memory"])
async def render_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncRenderRepositoryType, None]:
    """Provide both async render repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield AsyncSQLiteRenderRepository(conn)
        await conn.close()
    else:
        yield InMemoryRenderRepository()


def _make_job(**overrides: object) -> RenderJob:
    """Create a RenderJob with sensible defaults, applying overrides."""
    defaults = {
        "project_id": "proj-1",
        "output_path": "/out/video.mp4",
        "output_format": OutputFormat.MP4,
        "quality_preset": QualityPreset.STANDARD,
        "render_plan": '{"segments": []}',
    }
    defaults.update(overrides)
    return RenderJob.create(**defaults)  # type: ignore[arg-type]


# ============================================================
# Model unit tests (run once, not parametrized by repository)
# ============================================================


class TestRenderJobCreate:
    """Tests for RenderJob.create() factory method."""

    def test_create_sets_queued_status(self) -> None:
        """New render job starts with queued status."""
        job = _make_job()
        assert job.status == RenderStatus.QUEUED

    def test_create_sets_zero_progress(self) -> None:
        """New render job starts with 0.0 progress."""
        job = _make_job()
        assert job.progress == 0.0

    def test_create_sets_null_error(self) -> None:
        """New render job starts with no error message."""
        job = _make_job()
        assert job.error_message is None

    def test_create_sets_zero_retry_count(self) -> None:
        """New render job starts with 0 retry count."""
        job = _make_job()
        assert job.retry_count == 0

    def test_create_sets_null_completed_at(self) -> None:
        """New render job starts with no completed_at."""
        job = _make_job()
        assert job.completed_at is None

    def test_create_sets_timestamps(self) -> None:
        """New render job has created_at and updated_at."""
        job = _make_job()
        assert job.created_at is not None
        assert job.updated_at is not None
        assert job.updated_at >= job.created_at

    def test_create_generates_unique_ids(self) -> None:
        """Each created job gets a unique UUID."""
        j1 = _make_job()
        j2 = _make_job()
        assert j1.id != j2.id

    def test_create_preserves_all_fields(self) -> None:
        """All provided fields are preserved in the created job."""
        job = _make_job(
            project_id="proj-99",
            output_path="/out/test.webm",
            output_format=OutputFormat.WEBM,
            quality_preset=QualityPreset.HIGH,
            render_plan='{"key": "value"}',
        )
        assert job.project_id == "proj-99"
        assert job.output_path == "/out/test.webm"
        assert job.output_format == OutputFormat.WEBM
        assert job.quality_preset == QualityPreset.HIGH
        assert job.render_plan == '{"key": "value"}'


class TestRenderStatusTransitions:
    """Tests for render job status transition validation."""

    def test_queued_to_running(self) -> None:
        """queued -> running is valid."""
        job = _make_job()
        job.status = RenderStatus.RUNNING
        # If we got here without error from validate, transition is allowed
        from stoat_ferret.render.models import validate_render_transition

        validate_render_transition("queued", "running")

    def test_running_to_completed(self) -> None:
        """running -> completed is valid."""
        job = _make_job()
        job.status = RenderStatus.RUNNING
        job.complete()
        assert job.status == RenderStatus.COMPLETED
        assert job.progress == 1.0
        assert job.completed_at is not None

    def test_running_to_failed(self) -> None:
        """running -> failed sets error message."""
        job = _make_job()
        job.status = RenderStatus.RUNNING
        job.fail("render crashed")
        assert job.status == RenderStatus.FAILED
        assert job.error_message == "render crashed"
        assert job.completed_at is not None

    def test_failed_to_queued_retry(self) -> None:
        """failed -> queued (retry) increments retry count."""
        job = _make_job()
        job.status = RenderStatus.RUNNING
        job.fail("error")
        job.retry()
        assert job.status == RenderStatus.QUEUED
        assert job.retry_count == 1
        assert job.progress == 0.0
        assert job.error_message is None
        assert job.completed_at is None

    def test_queued_to_cancelled(self) -> None:
        """queued -> cancelled is valid."""
        job = _make_job()
        job.cancel()
        assert job.status == RenderStatus.CANCELLED
        assert job.completed_at is not None

    def test_running_to_cancelled(self) -> None:
        """running -> cancelled is valid."""
        job = _make_job()
        job.status = RenderStatus.RUNNING
        job.cancel()
        assert job.status == RenderStatus.CANCELLED

    def test_cancelled_is_terminal(self) -> None:
        """cancelled -> anything raises ValueError."""
        job = _make_job()
        job.cancel()
        with pytest.raises(ValueError, match="Invalid status transition"):
            job.retry()

    def test_completed_to_running_raises(self) -> None:
        """completed -> running is not allowed."""
        job = _make_job()
        job.status = RenderStatus.RUNNING
        job.complete()
        from stoat_ferret.render.models import validate_render_transition

        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_render_transition("completed", "running")

    def test_queued_to_completed_raises(self) -> None:
        """queued -> completed is not allowed."""
        from stoat_ferret.render.models import validate_render_transition

        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_render_transition("queued", "completed")


class TestRenderJobProgressValidation:
    """Tests for progress bounds validation."""

    def test_valid_progress(self) -> None:
        """Progress within bounds is accepted."""
        job = _make_job()
        job.update_progress(0.5)
        assert job.progress == pytest.approx(0.5)

    def test_progress_too_high(self) -> None:
        """Progress > 1.0 raises ValueError."""
        job = _make_job()
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            job.update_progress(1.5)

    def test_progress_too_low(self) -> None:
        """Progress < 0.0 raises ValueError."""
        job = _make_job()
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            job.update_progress(-0.1)

    def test_progress_boundary_zero(self) -> None:
        """Progress = 0.0 is accepted."""
        job = _make_job()
        job.update_progress(0.0)
        assert job.progress == 0.0

    def test_progress_boundary_one(self) -> None:
        """Progress = 1.0 is accepted."""
        job = _make_job()
        job.update_progress(1.0)
        assert job.progress == 1.0


class TestEnumValues:
    """Tests for enum completeness."""

    def test_output_format_has_four_values(self) -> None:
        """OutputFormat enum has mp4, webm, mov, mkv."""
        values = {f.value for f in OutputFormat}
        assert values == {"mp4", "webm", "mov", "mkv"}

    def test_quality_preset_has_three_values(self) -> None:
        """QualityPreset enum has draft, standard, high."""
        values = {p.value for p in QualityPreset}
        assert values == {"draft", "standard", "high"}

    def test_render_status_has_five_values(self) -> None:
        """RenderStatus enum has queued, running, completed, failed, cancelled."""
        values = {s.value for s in RenderStatus}
        assert values == {"queued", "running", "completed", "failed", "cancelled"}


# ============================================================
# Repository contract tests (parametrized across both impls)
# ============================================================


@pytest.mark.contract
class TestRenderCreate:
    """Tests for create() method."""

    async def test_create_and_retrieve(self, render_repository: AsyncRenderRepositoryType) -> None:
        """Created job can be retrieved by ID."""
        job = _make_job()
        created = await render_repository.create(job)

        fetched = await render_repository.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.project_id == "proj-1"
        assert fetched.status == RenderStatus.QUEUED
        assert fetched.output_format == OutputFormat.MP4
        assert fetched.quality_preset == QualityPreset.STANDARD
        assert fetched.progress == 0.0
        assert fetched.error_message is None

    async def test_create_preserves_render_plan(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Render plan JSON is preserved through round-trip."""
        plan = '{"segments": [{"start": 0, "end": 100}]}'
        job = _make_job(render_plan=plan)
        created = await render_repository.create(job)

        fetched = await render_repository.get(created.id)
        assert fetched is not None
        assert fetched.render_plan == plan

    async def test_create_preserves_all_formats(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """All OutputFormat values round-trip correctly."""
        for fmt in OutputFormat:
            job = _make_job(output_format=fmt)
            created = await render_repository.create(job)
            fetched = await render_repository.get(created.id)
            assert fetched is not None
            assert fetched.output_format == fmt

    async def test_create_preserves_all_presets(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """All QualityPreset values round-trip correctly."""
        for preset in QualityPreset:
            job = _make_job(quality_preset=preset)
            created = await render_repository.create(job)
            fetched = await render_repository.get(created.id)
            assert fetched is not None
            assert fetched.quality_preset == preset


@pytest.mark.contract
class TestRenderGet:
    """Tests for get() method."""

    async def test_get_nonexistent_returns_none(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """get() returns None for nonexistent job."""
        result = await render_repository.get("nonexistent")
        assert result is None


@pytest.mark.contract
class TestRenderGetByProject:
    """Tests for get_by_project() method."""

    async def test_empty_project_returns_empty(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Querying nonexistent project returns empty list."""
        result = await render_repository.get_by_project("nonexistent")
        assert result == []

    async def test_returns_jobs_for_project(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """get_by_project returns only jobs for the given project."""
        j1 = _make_job(project_id="proj-a")
        j2 = _make_job(project_id="proj-a")
        j3 = _make_job(project_id="proj-b")

        await render_repository.create(j1)
        await render_repository.create(j2)
        await render_repository.create(j3)

        proj_a = await render_repository.get_by_project("proj-a")
        proj_b = await render_repository.get_by_project("proj-b")

        assert len(proj_a) == 2
        assert len(proj_b) == 1
        assert all(j.project_id == "proj-a" for j in proj_a)

    async def test_returns_ordered_by_created_at(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Jobs are returned ordered by created_at."""
        j1 = _make_job(project_id="proj-1")
        j2 = _make_job(project_id="proj-1")
        await render_repository.create(j1)
        await render_repository.create(j2)

        jobs = await render_repository.get_by_project("proj-1")
        assert len(jobs) == 2
        assert jobs[0].created_at <= jobs[1].created_at


@pytest.mark.contract
class TestRenderListByStatus:
    """Tests for list_by_status() method."""

    async def test_empty_status_returns_empty(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Querying status with no matches returns empty list."""
        result = await render_repository.list_by_status(RenderStatus.RUNNING)
        assert result == []

    async def test_filters_by_status(self, render_repository: AsyncRenderRepositoryType) -> None:
        """list_by_status returns only jobs with the given status."""
        j1 = _make_job()
        j2 = _make_job()
        await render_repository.create(j1)
        await render_repository.create(j2)

        # Both are queued initially
        queued = await render_repository.list_by_status(RenderStatus.QUEUED)
        assert len(queued) == 2

        # Transition one to running
        await render_repository.update_status(j1.id, RenderStatus.RUNNING)

        queued = await render_repository.list_by_status(RenderStatus.QUEUED)
        running = await render_repository.list_by_status(RenderStatus.RUNNING)
        assert len(queued) == 1
        assert len(running) == 1


@pytest.mark.contract
class TestRenderUpdateStatus:
    """Tests for update_status() method."""

    async def test_queued_to_running(self, render_repository: AsyncRenderRepositoryType) -> None:
        """queued -> running is a valid transition."""
        job = _make_job()
        await render_repository.create(job)

        await render_repository.update_status(job.id, RenderStatus.RUNNING)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.status == RenderStatus.RUNNING

    async def test_running_to_completed(self, render_repository: AsyncRenderRepositoryType) -> None:
        """running -> completed sets progress to 1.0 and completed_at."""
        job = _make_job()
        await render_repository.create(job)
        await render_repository.update_status(job.id, RenderStatus.RUNNING)
        await render_repository.update_status(job.id, RenderStatus.COMPLETED)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.status == RenderStatus.COMPLETED
        assert fetched.progress == 1.0
        assert fetched.completed_at is not None

    async def test_running_to_failed_with_error(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """running -> failed sets error message and completed_at."""
        job = _make_job()
        await render_repository.create(job)
        await render_repository.update_status(job.id, RenderStatus.RUNNING)
        await render_repository.update_status(
            job.id, RenderStatus.FAILED, error_message="encoder crashed"
        )

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.status == RenderStatus.FAILED
        assert fetched.error_message == "encoder crashed"
        assert fetched.completed_at is not None

    async def test_failed_to_queued_retry(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """failed -> queued (retry) increments retry_count and resets progress."""
        job = _make_job()
        await render_repository.create(job)
        await render_repository.update_status(job.id, RenderStatus.RUNNING)
        await render_repository.update_progress(job.id, 0.5)
        await render_repository.update_status(job.id, RenderStatus.FAILED, error_message="error")
        await render_repository.update_status(job.id, RenderStatus.QUEUED)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.status == RenderStatus.QUEUED
        assert fetched.retry_count == 1
        assert fetched.progress == 0.0
        assert fetched.error_message is None
        assert fetched.completed_at is None

    async def test_queued_to_cancelled(self, render_repository: AsyncRenderRepositoryType) -> None:
        """queued -> cancelled sets completed_at."""
        job = _make_job()
        await render_repository.create(job)
        await render_repository.update_status(job.id, RenderStatus.CANCELLED)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.status == RenderStatus.CANCELLED
        assert fetched.completed_at is not None

    async def test_running_to_cancelled(self, render_repository: AsyncRenderRepositoryType) -> None:
        """running -> cancelled is valid."""
        job = _make_job()
        await render_repository.create(job)
        await render_repository.update_status(job.id, RenderStatus.RUNNING)
        await render_repository.update_status(job.id, RenderStatus.CANCELLED)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.status == RenderStatus.CANCELLED

    async def test_cancelled_is_terminal(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """cancelled -> any raises ValueError."""
        job = _make_job()
        await render_repository.create(job)
        await render_repository.update_status(job.id, RenderStatus.CANCELLED)

        with pytest.raises(ValueError, match="Invalid status transition"):
            await render_repository.update_status(job.id, RenderStatus.QUEUED)

    async def test_completed_to_running_raises(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """completed -> running is not allowed."""
        job = _make_job()
        await render_repository.create(job)
        await render_repository.update_status(job.id, RenderStatus.RUNNING)
        await render_repository.update_status(job.id, RenderStatus.COMPLETED)

        with pytest.raises(ValueError, match="Invalid status transition"):
            await render_repository.update_status(job.id, RenderStatus.RUNNING)

    async def test_queued_to_completed_raises(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """queued -> completed is not allowed."""
        job = _make_job()
        await render_repository.create(job)

        with pytest.raises(ValueError, match="Invalid status transition"):
            await render_repository.update_status(job.id, RenderStatus.COMPLETED)

    async def test_nonexistent_job_raises(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Updating status of nonexistent job raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await render_repository.update_status("nonexistent", RenderStatus.RUNNING)

    async def test_update_status_updates_timestamp(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Status update changes updated_at timestamp."""
        job = _make_job()
        created = await render_repository.create(job)
        original_updated = created.updated_at

        await render_repository.update_status(job.id, RenderStatus.RUNNING)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.updated_at >= original_updated


@pytest.mark.contract
class TestRenderUpdateProgress:
    """Tests for update_progress() method."""

    async def test_update_progress_value(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Progress value is correctly updated."""
        job = _make_job()
        await render_repository.create(job)

        await render_repository.update_progress(job.id, 0.5)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.progress == pytest.approx(0.5)

    async def test_progress_out_of_bounds_raises(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Progress outside [0.0, 1.0] raises ValueError."""
        job = _make_job()
        await render_repository.create(job)

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            await render_repository.update_progress(job.id, 1.5)

    async def test_nonexistent_job_raises(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Updating progress of nonexistent job raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await render_repository.update_progress("nonexistent", 0.5)

    async def test_update_progress_updates_timestamp(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Progress update changes updated_at timestamp."""
        job = _make_job()
        created = await render_repository.create(job)
        original_updated = created.updated_at

        await render_repository.update_progress(job.id, 0.75)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.updated_at >= original_updated


@pytest.mark.contract
class TestRenderDelete:
    """Tests for delete() method."""

    async def test_delete_existing_job(self, render_repository: AsyncRenderRepositoryType) -> None:
        """Deleting an existing job returns True and removes it."""
        job = _make_job()
        await render_repository.create(job)

        result = await render_repository.delete(job.id)
        assert result is True

        fetched = await render_repository.get(job.id)
        assert fetched is None

    async def test_delete_nonexistent_returns_false(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Deleting a nonexistent job returns False."""
        result = await render_repository.delete("nonexistent")
        assert result is False


@pytest.mark.contract
class TestRenderProtocolCompliance:
    """Tests for protocol compliance."""

    def test_sqlite_implements_protocol(self) -> None:
        """AsyncSQLiteRenderRepository is a runtime_checkable Protocol impl."""
        assert issubclass(AsyncSQLiteRenderRepository, AsyncRenderRepository)

    def test_inmemory_implements_protocol(self) -> None:
        """InMemoryRenderRepository is a runtime_checkable Protocol impl."""
        assert issubclass(InMemoryRenderRepository, AsyncRenderRepository)


@pytest.mark.contract
class TestRenderDeepCopyIsolation:
    """Tests for deepcopy isolation in InMemory implementation."""

    async def test_returned_record_is_isolated(self) -> None:
        """Mutating a returned record does not affect stored state."""
        repo = InMemoryRenderRepository()
        job = _make_job()
        created = await repo.create(job)

        # Mutate the returned record
        created.status = RenderStatus.COMPLETED

        # Fetch again - should be unchanged
        fetched = await repo.get(created.id)
        assert fetched is not None
        assert fetched.status == RenderStatus.QUEUED


def _make_job_with_timestamp(project_id: str, job_id: str, ts: datetime) -> RenderJob:
    """Create a RenderJob with a controlled id and created_at for ordering tests."""
    return RenderJob(
        id=job_id,
        project_id=project_id,
        status=RenderStatus.QUEUED,
        output_path="/out/video.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan='{"segments": []}',
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=ts,
        updated_at=ts,
        completed_at=None,
    )


@pytest.mark.contract
class TestRenderDeterministicOrdering:
    """Tests for deterministic ordering when jobs share the same created_at timestamp."""

    async def test_get_by_project_tie_break_by_id(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Jobs with identical created_at are ordered by id ASC tie-break."""
        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        # Use controlled UUIDs so id ASC order is deterministic
        job1 = _make_job_with_timestamp("proj-tie", "00000000-0000-0000-0000-000000000001", ts)
        job2 = _make_job_with_timestamp("proj-tie", "00000000-0000-0000-0000-000000000002", ts)
        await render_repository.create(job1)
        await render_repository.create(job2)

        result1 = await render_repository.get_by_project("proj-tie")
        result2 = await render_repository.get_by_project("proj-tie")

        # id ASC tie-break: job1's id is lexicographically smaller
        assert len(result1) == 2
        assert result1[0].id == job1.id
        assert result1[1].id == job2.id
        # Consistent across multiple calls
        assert result2[0].id == job1.id
        assert result2[1].id == job2.id

    async def test_list_by_status_tie_break_by_id(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """list_by_status with identical created_at also uses id ASC tie-break."""
        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        job1 = _make_job_with_timestamp("proj-tie2", "00000000-0000-0000-0000-000000000001", ts)
        job2 = _make_job_with_timestamp("proj-tie2", "00000000-0000-0000-0000-000000000002", ts)
        await render_repository.create(job1)
        await render_repository.create(job2)

        result = await render_repository.list_by_status(RenderStatus.QUEUED)

        assert len(result) == 2
        assert result[0].id == job1.id
        assert result[1].id == job2.id


@pytest.mark.contract
class TestRenderSerializationRoundTrip:
    """Contract tests for model serialization round-trip."""

    async def test_enum_values_persist_and_recover(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Enum values are correctly persisted and recovered."""
        job = _make_job(
            output_format=OutputFormat.WEBM,
            quality_preset=QualityPreset.HIGH,
        )
        await render_repository.create(job)

        fetched = await render_repository.get(job.id)
        assert fetched is not None
        assert fetched.output_format == OutputFormat.WEBM
        assert fetched.quality_preset == QualityPreset.HIGH
        assert fetched.status == RenderStatus.QUEUED

    async def test_timestamps_survive_round_trip(
        self, render_repository: AsyncRenderRepositoryType
    ) -> None:
        """Timestamps are preserved through persistence."""
        job = _make_job()
        created = await render_repository.create(job)

        fetched = await render_repository.get(created.id)
        assert fetched is not None
        # Allow minor differences from serialization
        assert abs((fetched.created_at - created.created_at).total_seconds()) < 1.0
        assert abs((fetched.updated_at - created.updated_at).total_seconds()) < 1.0
