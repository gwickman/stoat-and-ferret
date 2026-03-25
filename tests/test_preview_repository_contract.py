"""Contract tests for async PreviewRepository implementations.

These tests run against both SQLitePreviewRepository and
InMemoryPreviewRepository to verify they have identical behavior.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import PreviewQuality, PreviewSession, PreviewStatus
from stoat_ferret.db.preview_repository import (
    AsyncPreviewRepository,
    InMemoryPreviewRepository,
    SQLitePreviewRepository,
)
from stoat_ferret.db.schema import create_tables_async

AsyncPreviewRepositoryType = SQLitePreviewRepository | InMemoryPreviewRepository

_NOW = datetime(2026, 3, 25, 12, 0, 0, tzinfo=timezone.utc)
_EXPIRES = _NOW + timedelta(seconds=3600)


def _make_session(
    *,
    session_id: str = "session-1",
    project_id: str = "project-1",
    status: PreviewStatus = PreviewStatus.INITIALIZING,
    quality: PreviewQuality = PreviewQuality.MEDIUM,
    manifest_path: str | None = None,
    segment_count: int = 0,
    error_message: str | None = None,
    created_at: datetime = _NOW,
    updated_at: datetime = _NOW,
    expires_at: datetime = _EXPIRES,
) -> PreviewSession:
    """Create a PreviewSession instance for testing."""
    return PreviewSession(
        id=session_id,
        project_id=project_id,
        status=status,
        quality_level=quality,
        created_at=created_at,
        updated_at=updated_at,
        expires_at=expires_at,
        manifest_path=manifest_path,
        segment_count=segment_count,
        error_message=error_message,
    )


@pytest.fixture(params=["sqlite", "memory"])
async def preview_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncPreviewRepositoryType, None]:
    """Provide both async preview repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield SQLitePreviewRepository(conn)
        await conn.close()
    else:
        yield InMemoryPreviewRepository()


@pytest.mark.contract
class TestPreviewAdd:
    """Tests for add() method."""

    async def test_add_returns_session_with_all_fields(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Added session retains all field values."""
        session = _make_session()
        result = await preview_repository.add(session)

        assert result.id == "session-1"
        assert result.project_id == "project-1"
        assert result.status == PreviewStatus.INITIALIZING
        assert result.quality_level == PreviewQuality.MEDIUM
        assert result.manifest_path is None
        assert result.segment_count == 0
        assert result.error_message is None

    async def test_add_duplicate_id_raises(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Inserting duplicate session ID raises ValueError."""
        await preview_repository.add(_make_session())

        with pytest.raises(ValueError, match="already exists"):
            await preview_repository.add(_make_session())


@pytest.mark.contract
class TestPreviewGet:
    """Tests for get() method."""

    async def test_get_existing(self, preview_repository: AsyncPreviewRepositoryType) -> None:
        """get returns the correct session by ID."""
        await preview_repository.add(_make_session())

        result = await preview_repository.get("session-1")
        assert result is not None
        assert result.id == "session-1"
        assert result.quality_level == PreviewQuality.MEDIUM

    async def test_get_nonexistent_returns_none(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """get returns None for nonexistent ID."""
        result = await preview_repository.get("nonexistent")
        assert result is None


@pytest.mark.contract
class TestPreviewListByProject:
    """Tests for list_by_project() method."""

    async def test_empty_returns_empty_list(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """No sessions for a project returns empty list."""
        result = await preview_repository.list_by_project("nonexistent")
        assert result == []

    async def test_returns_all_sessions_for_project(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Returns all sessions for the given project."""
        await preview_repository.add(_make_session(session_id="s1"))
        await preview_repository.add(
            _make_session(
                session_id="s2",
                created_at=_NOW + timedelta(seconds=1),
                updated_at=_NOW + timedelta(seconds=1),
            )
        )
        # Different project
        await preview_repository.add(_make_session(session_id="s3", project_id="project-2"))

        result = await preview_repository.list_by_project("project-1")
        assert len(result) == 2
        assert {s.id for s in result} == {"s1", "s2"}

    async def test_does_not_return_other_projects(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Only returns sessions for the requested project."""
        await preview_repository.add(_make_session())
        await preview_repository.add(_make_session(session_id="s2", project_id="project-2"))

        result = await preview_repository.list_by_project("project-2")
        assert len(result) == 1
        assert result[0].project_id == "project-2"


@pytest.mark.contract
class TestPreviewUpdate:
    """Tests for update() method."""

    async def test_valid_transition_initializing_to_generating(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """initializing -> generating is a valid transition."""
        await preview_repository.add(_make_session())
        session = await preview_repository.get("session-1")
        assert session is not None

        session.status = PreviewStatus.GENERATING
        session.updated_at = _NOW + timedelta(seconds=10)
        await preview_repository.update(session)

        result = await preview_repository.get("session-1")
        assert result is not None
        assert result.status == PreviewStatus.GENERATING

    async def test_valid_transition_generating_to_ready(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """generating -> ready sets manifest_path and segment_count."""
        session = _make_session(status=PreviewStatus.GENERATING)
        await preview_repository.add(session)

        updated = await preview_repository.get("session-1")
        assert updated is not None
        updated.status = PreviewStatus.READY
        updated.manifest_path = "/data/previews/session-1/index.m3u8"
        updated.segment_count = 5
        updated.updated_at = _NOW + timedelta(seconds=30)
        await preview_repository.update(updated)

        result = await preview_repository.get("session-1")
        assert result is not None
        assert result.status == PreviewStatus.READY
        assert result.manifest_path == "/data/previews/session-1/index.m3u8"
        assert result.segment_count == 5

    async def test_valid_transition_any_to_error(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Any state can transition to error."""
        await preview_repository.add(_make_session())
        session = await preview_repository.get("session-1")
        assert session is not None

        session.status = PreviewStatus.ERROR
        session.error_message = "FFmpeg failed"
        session.updated_at = _NOW + timedelta(seconds=5)
        await preview_repository.update(session)

        result = await preview_repository.get("session-1")
        assert result is not None
        assert result.status == PreviewStatus.ERROR
        assert result.error_message == "FFmpeg failed"

    async def test_invalid_transition_ready_to_initializing_raises(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """ready -> initializing is not allowed."""
        session = _make_session(status=PreviewStatus.GENERATING)
        await preview_repository.add(session)
        s = await preview_repository.get("session-1")
        assert s is not None
        s.status = PreviewStatus.READY
        s.updated_at = _NOW + timedelta(seconds=10)
        await preview_repository.update(s)

        s2 = await preview_repository.get("session-1")
        assert s2 is not None
        s2.status = PreviewStatus.INITIALIZING
        with pytest.raises(ValueError, match="Invalid preview status transition"):
            await preview_repository.update(s2)

    async def test_update_nonexistent_raises(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Updating nonexistent session raises ValueError."""
        session = _make_session(session_id="nonexistent")
        with pytest.raises(ValueError, match="not found"):
            await preview_repository.update(session)

    async def test_update_without_status_change(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Updating fields without changing status succeeds."""
        await preview_repository.add(_make_session())
        session = await preview_repository.get("session-1")
        assert session is not None

        session.segment_count = 3
        session.updated_at = _NOW + timedelta(seconds=5)
        await preview_repository.update(session)

        result = await preview_repository.get("session-1")
        assert result is not None
        assert result.segment_count == 3


@pytest.mark.contract
class TestPreviewDelete:
    """Tests for delete() method."""

    async def test_delete_existing_returns_true(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Deleting an existing session returns True."""
        await preview_repository.add(_make_session())

        assert await preview_repository.delete("session-1") is True
        assert await preview_repository.get("session-1") is None

    async def test_delete_nonexistent_returns_false(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Deleting a nonexistent session returns False."""
        assert await preview_repository.delete("nonexistent") is False


@pytest.mark.contract
class TestPreviewExpiry:
    """Tests for TTL expiry detection."""

    async def test_get_expired_returns_expired_sessions(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """get_expired returns sessions where expires_at < now."""
        past = _NOW - timedelta(seconds=100)
        future = _NOW + timedelta(seconds=3600)

        await preview_repository.add(_make_session(session_id="expired-1", expires_at=past))
        await preview_repository.add(_make_session(session_id="active-1", expires_at=future))

        expired = await preview_repository.get_expired(now=_NOW)
        assert len(expired) == 1
        assert expired[0].id == "expired-1"

    async def test_get_expired_empty_when_none_expired(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """get_expired returns empty list when no sessions are expired."""
        future = _NOW + timedelta(seconds=3600)
        await preview_repository.add(_make_session(session_id="active-1", expires_at=future))

        expired = await preview_repository.get_expired(now=_NOW)
        assert expired == []


@pytest.mark.contract
class TestPreviewCount:
    """Tests for count() method."""

    async def test_count_empty(self, preview_repository: AsyncPreviewRepositoryType) -> None:
        """Empty repository has count 0."""
        assert await preview_repository.count() == 0

    async def test_count_after_adds(self, preview_repository: AsyncPreviewRepositoryType) -> None:
        """Count reflects number of added sessions."""
        await preview_repository.add(_make_session(session_id="s1"))
        await preview_repository.add(_make_session(session_id="s2"))

        assert await preview_repository.count() == 2

    async def test_count_after_delete(self, preview_repository: AsyncPreviewRepositoryType) -> None:
        """Count decreases after delete."""
        await preview_repository.add(_make_session())

        await preview_repository.delete("session-1")

        assert await preview_repository.count() == 0


@pytest.mark.contract
class TestPreviewRoundTrip:
    """Tests for data round-trip integrity."""

    async def test_all_fields_round_trip(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """All fields survive create -> get without data loss."""
        session = PreviewSession(
            id="rt-1",
            project_id="proj-42",
            status=PreviewStatus.READY,
            quality_level=PreviewQuality.HIGH,
            created_at=_NOW,
            updated_at=_NOW + timedelta(seconds=30),
            expires_at=_NOW + timedelta(seconds=3600),
            manifest_path="/data/previews/rt-1/index.m3u8",
            segment_count=10,
            error_message=None,
        )

        await preview_repository.add(session)
        result = await preview_repository.get("rt-1")

        assert result is not None
        assert result.id == "rt-1"
        assert result.project_id == "proj-42"
        assert result.status == PreviewStatus.READY
        assert result.quality_level == PreviewQuality.HIGH
        assert result.manifest_path == "/data/previews/rt-1/index.m3u8"
        assert result.segment_count == 10
        assert result.error_message is None
        # Timestamp comparison: allow microsecond precision loss in SQLite
        assert abs((result.created_at - _NOW).total_seconds()) < 1
        assert abs((result.updated_at - (_NOW + timedelta(seconds=30))).total_seconds()) < 1
        assert abs((result.expires_at - (_NOW + timedelta(seconds=3600))).total_seconds()) < 1


@pytest.mark.contract
class TestPreviewProtocolCompliance:
    """Tests for protocol compliance."""

    def test_sqlite_implements_protocol(self) -> None:
        """SQLitePreviewRepository is a runtime_checkable Protocol impl."""
        assert issubclass(SQLitePreviewRepository, AsyncPreviewRepository)

    def test_inmemory_implements_protocol(self) -> None:
        """InMemoryPreviewRepository is a runtime_checkable Protocol impl."""
        assert issubclass(InMemoryPreviewRepository, AsyncPreviewRepository)


@pytest.mark.contract
class TestPreviewConcurrentAccess:
    """Tests for concurrent access patterns."""

    async def test_concurrent_adds_different_ids(
        self, preview_repository: AsyncPreviewRepositoryType
    ) -> None:
        """Concurrent adds with different IDs all succeed."""
        sessions = [_make_session(session_id=f"concurrent-{i}") for i in range(5)]

        await asyncio.gather(*[preview_repository.add(s) for s in sessions])

        assert await preview_repository.count() == 5

    async def test_concurrent_reads(self, preview_repository: AsyncPreviewRepositoryType) -> None:
        """Concurrent reads return consistent data."""
        await preview_repository.add(_make_session())

        results = await asyncio.gather(*[preview_repository.get("session-1") for _ in range(5)])

        for r in results:
            assert r is not None
            assert r.id == "session-1"


@pytest.mark.contract
class TestPreviewDeepCopyIsolation:
    """Tests for deepcopy isolation in InMemory implementation."""

    async def test_returned_session_is_isolated(self) -> None:
        """Mutating a returned session does not affect stored state."""
        repo = InMemoryPreviewRepository()
        session = _make_session()
        await repo.add(session)

        fetched = await repo.get("session-1")
        assert fetched is not None
        fetched.manifest_path = "/MUTATED"

        refetched = await repo.get("session-1")
        assert refetched is not None
        assert refetched.manifest_path is None
