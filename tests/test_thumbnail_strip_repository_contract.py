"""Contract tests for async ThumbnailStripRepository implementations.

These tests run against both SQLiteThumbnailStripRepository and
InMemoryThumbnailStripRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import ThumbnailStrip, ThumbnailStripStatus
from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.db.thumbnail_strip_repository import (
    AsyncThumbnailStripRepository,
    InMemoryThumbnailStripRepository,
    SQLiteThumbnailStripRepository,
)

AsyncThumbnailStripRepositoryType = (
    SQLiteThumbnailStripRepository | InMemoryThumbnailStripRepository
)


def _make_strip(
    *,
    strip_id: str = "strip-1",
    video_id: str = "video-1",
    status: ThumbnailStripStatus = ThumbnailStripStatus.PENDING,
) -> ThumbnailStrip:
    """Create a ThumbnailStrip instance for testing."""
    return ThumbnailStrip(
        id=strip_id,
        video_id=video_id,
        status=status,
        created_at=datetime.now(timezone.utc),
        file_path=None,
        frame_count=0,
        frame_width=160,
        frame_height=90,
        interval_seconds=5.0,
        columns=10,
        rows=0,
    )


@pytest.fixture(params=["sqlite", "memory"])
async def strip_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncThumbnailStripRepositoryType, None]:
    """Provide both async thumbnail strip repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield SQLiteThumbnailStripRepository(conn)
        await conn.close()
    else:
        yield InMemoryThumbnailStripRepository()


@pytest.mark.contract
class TestThumbnailStripAdd:
    """Tests for add() method."""

    async def test_add_returns_strip_with_all_fields(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Added strip retains all field values."""
        strip = _make_strip()
        result = await strip_repository.add(strip)

        assert result.id == "strip-1"
        assert result.video_id == "video-1"
        assert result.status == ThumbnailStripStatus.PENDING
        assert result.file_path is None
        assert result.frame_count == 0
        assert result.frame_width == 160
        assert result.frame_height == 90
        assert result.interval_seconds == 5.0
        assert result.columns == 10
        assert result.rows == 0

    async def test_add_duplicate_id_raises(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Inserting duplicate ID raises ValueError."""
        await strip_repository.add(_make_strip(strip_id="s1"))

        with pytest.raises(ValueError):
            await strip_repository.add(_make_strip(strip_id="s1"))

    async def test_add_different_strips_same_video_ok(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Multiple strips for the same video are allowed (no UNIQUE constraint on video_id)."""
        await strip_repository.add(_make_strip(strip_id="s1"))
        result = await strip_repository.add(_make_strip(strip_id="s2"))

        assert result.id == "s2"


@pytest.mark.contract
class TestThumbnailStripGet:
    """Tests for get() method."""

    async def test_get_existing(self, strip_repository: AsyncThumbnailStripRepositoryType) -> None:
        """get returns the correct strip by ID."""
        await strip_repository.add(_make_strip())

        result = await strip_repository.get("strip-1")
        assert result is not None
        assert result.id == "strip-1"
        assert result.video_id == "video-1"

    async def test_get_nonexistent_returns_none(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """get returns None for nonexistent ID."""
        result = await strip_repository.get("nonexistent")
        assert result is None


@pytest.mark.contract
class TestThumbnailStripGetByVideo:
    """Tests for get_by_video() method."""

    async def test_get_existing_strip(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Finds strip by video ID."""
        await strip_repository.add(_make_strip())

        result = await strip_repository.get_by_video("video-1")
        assert result is not None
        assert result.id == "strip-1"

    async def test_get_nonexistent_video_returns_none(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Returns None for nonexistent video."""
        result = await strip_repository.get_by_video("nonexistent")
        assert result is None

    async def test_returns_most_recent_strip(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """When multiple strips exist for a video, returns the most recent."""
        import asyncio

        await strip_repository.add(_make_strip(strip_id="older"))
        await asyncio.sleep(0.001)  # ensure created_at differs
        await strip_repository.add(_make_strip(strip_id="newer"))

        result = await strip_repository.get_by_video("video-1")
        assert result is not None
        assert result.id == "newer"


@pytest.mark.contract
class TestThumbnailStripUpdateStatus:
    """Tests for update_status() method."""

    async def test_valid_transition_pending_to_generating(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """pending -> generating is a valid transition."""
        await strip_repository.add(_make_strip())

        await strip_repository.update_status("strip-1", ThumbnailStripStatus.GENERATING)

        strip = await strip_repository.get("strip-1")
        assert strip is not None
        assert strip.status == ThumbnailStripStatus.GENERATING

    async def test_valid_transition_generating_to_ready_sets_file_path(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """generating -> ready sets file_path, frame_count, rows."""
        await strip_repository.add(_make_strip())
        await strip_repository.update_status("strip-1", ThumbnailStripStatus.GENERATING)

        await strip_repository.update_status(
            "strip-1",
            ThumbnailStripStatus.READY,
            file_path="/data/strips/strip-1.jpg",
            frame_count=20,
            rows=2,
        )

        strip = await strip_repository.get("strip-1")
        assert strip is not None
        assert strip.status == ThumbnailStripStatus.READY
        assert strip.file_path == "/data/strips/strip-1.jpg"
        assert strip.frame_count == 20
        assert strip.rows == 2

    async def test_valid_transition_generating_to_error(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """generating -> error is a valid transition."""
        await strip_repository.add(_make_strip())
        await strip_repository.update_status("strip-1", ThumbnailStripStatus.GENERATING)

        await strip_repository.update_status("strip-1", ThumbnailStripStatus.ERROR)

        strip = await strip_repository.get("strip-1")
        assert strip is not None
        assert strip.status == ThumbnailStripStatus.ERROR

    async def test_invalid_transition_pending_to_ready_raises(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """pending -> ready is not allowed."""
        await strip_repository.add(_make_strip())

        with pytest.raises(ValueError, match="Invalid status transition"):
            await strip_repository.update_status("strip-1", ThumbnailStripStatus.READY)

    async def test_invalid_transition_error_to_ready_raises(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """error is a terminal state."""
        await strip_repository.add(_make_strip())
        await strip_repository.update_status("strip-1", ThumbnailStripStatus.GENERATING)
        await strip_repository.update_status("strip-1", ThumbnailStripStatus.ERROR)

        with pytest.raises(ValueError, match="Invalid status transition"):
            await strip_repository.update_status("strip-1", ThumbnailStripStatus.READY)

    async def test_update_nonexistent_raises(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Updating nonexistent strip raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await strip_repository.update_status("nonexistent", ThumbnailStripStatus.GENERATING)


@pytest.mark.contract
class TestThumbnailStripDelete:
    """Tests for delete() method."""

    async def test_delete_existing_returns_true(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Deleting an existing strip returns True."""
        await strip_repository.add(_make_strip())

        assert await strip_repository.delete("strip-1") is True
        assert await strip_repository.get("strip-1") is None

    async def test_delete_nonexistent_returns_false(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """Deleting a nonexistent strip returns False."""
        assert await strip_repository.delete("nonexistent") is False


@pytest.mark.contract
class TestThumbnailStripProtocolCompliance:
    """Tests for protocol compliance."""

    def test_sqlite_implements_protocol(self) -> None:
        """SQLiteThumbnailStripRepository is a runtime_checkable Protocol impl."""
        assert issubclass(SQLiteThumbnailStripRepository, AsyncThumbnailStripRepository)

    def test_inmemory_implements_protocol(self) -> None:
        """InMemoryThumbnailStripRepository is a runtime_checkable Protocol impl."""
        assert issubclass(InMemoryThumbnailStripRepository, AsyncThumbnailStripRepository)


@pytest.mark.contract
class TestThumbnailStripRoundTrip:
    """Tests for data round-trip integrity."""

    async def test_all_fields_round_trip(
        self, strip_repository: AsyncThumbnailStripRepositoryType
    ) -> None:
        """All fields survive create -> get without data loss."""
        now = datetime.now(timezone.utc)
        strip = ThumbnailStrip(
            id="rt-1",
            video_id="vid-42",
            status=ThumbnailStripStatus.PENDING,
            created_at=now,
            file_path=None,
            frame_count=0,
            frame_width=200,
            frame_height=112,
            interval_seconds=2.5,
            columns=8,
            rows=0,
        )

        await strip_repository.add(strip)
        result = await strip_repository.get("rt-1")

        assert result is not None
        assert result.id == "rt-1"
        assert result.video_id == "vid-42"
        assert result.status == ThumbnailStripStatus.PENDING
        assert result.file_path is None
        assert result.frame_count == 0
        assert result.frame_width == 200
        assert result.frame_height == 112
        assert result.interval_seconds == 2.5
        assert result.columns == 8
        assert result.rows == 0
        assert abs((result.created_at - now).total_seconds()) < 1


@pytest.mark.contract
class TestThumbnailStripDeepCopyIsolation:
    """Tests for deepcopy isolation in InMemory implementation."""

    async def test_returned_strip_is_isolated(self) -> None:
        """Mutating a returned strip does not affect stored state."""
        repo = InMemoryThumbnailStripRepository()
        strip = _make_strip()
        await repo.add(strip)

        fetched = await repo.get("strip-1")
        assert fetched is not None
        fetched.file_path = "/MUTATED"

        refetched = await repo.get("strip-1")
        assert refetched is not None
        assert refetched.file_path is None
