"""Contract tests for async WaveformRepository implementations.

These tests run against both SQLiteWaveformRepository and
InMemoryWaveformRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import Waveform, WaveformFormat, WaveformStatus
from stoat_ferret.db.schema import create_tables_async
from stoat_ferret.db.waveform_repository import (
    AsyncWaveformRepository,
    InMemoryWaveformRepository,
    SQLiteWaveformRepository,
)

AsyncWaveformRepositoryType = SQLiteWaveformRepository | InMemoryWaveformRepository


def _make_waveform(
    *,
    waveform_id: str = "waveform-1",
    video_id: str = "video-1",
    fmt: WaveformFormat = WaveformFormat.PNG,
    status: WaveformStatus = WaveformStatus.PENDING,
) -> Waveform:
    """Create a Waveform instance for testing."""
    return Waveform(
        id=waveform_id,
        video_id=video_id,
        format=fmt,
        status=status,
        created_at=datetime.now(timezone.utc),
        file_path=None,
        duration=30.0,
        channels=2,
    )


@pytest.fixture(params=["sqlite", "memory"])
async def waveform_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncWaveformRepositoryType, None]:
    """Provide both async waveform repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield SQLiteWaveformRepository(conn)
        await conn.close()
    else:
        yield InMemoryWaveformRepository()


@pytest.mark.contract
class TestWaveformAdd:
    """Tests for add() method."""

    async def test_add_returns_waveform_with_all_fields(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Added waveform retains all field values."""
        waveform = _make_waveform()
        result = await waveform_repository.add(waveform)

        assert result.id == "waveform-1"
        assert result.video_id == "video-1"
        assert result.format == WaveformFormat.PNG
        assert result.status == WaveformStatus.PENDING
        assert result.file_path is None
        assert result.duration == 30.0
        assert result.channels == 2

    async def test_add_duplicate_id_raises(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Inserting duplicate ID raises ValueError."""
        await waveform_repository.add(_make_waveform(waveform_id="w1"))

        with pytest.raises(ValueError):
            await waveform_repository.add(_make_waveform(waveform_id="w1"))

    async def test_add_different_formats_same_video_ok(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """PNG and JSON waveforms for the same video are allowed."""
        await waveform_repository.add(_make_waveform(waveform_id="w1", fmt=WaveformFormat.PNG))
        result = await waveform_repository.add(
            _make_waveform(waveform_id="w2", fmt=WaveformFormat.JSON)
        )

        assert result.format == WaveformFormat.JSON


@pytest.mark.contract
class TestWaveformGet:
    """Tests for get() method."""

    async def test_get_existing(self, waveform_repository: AsyncWaveformRepositoryType) -> None:
        """get returns the correct waveform by ID."""
        await waveform_repository.add(_make_waveform())

        result = await waveform_repository.get("waveform-1")
        assert result is not None
        assert result.id == "waveform-1"
        assert result.format == WaveformFormat.PNG

    async def test_get_nonexistent_returns_none(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """get returns None for nonexistent ID."""
        result = await waveform_repository.get("nonexistent")
        assert result is None


@pytest.mark.contract
class TestWaveformGetByVideoAndFormat:
    """Tests for get_by_video_and_format() method."""

    async def test_get_existing_png(self, waveform_repository: AsyncWaveformRepositoryType) -> None:
        """Finds PNG waveform by video ID and format."""
        await waveform_repository.add(_make_waveform(fmt=WaveformFormat.PNG))

        result = await waveform_repository.get_by_video_and_format("video-1", WaveformFormat.PNG)
        assert result is not None
        assert result.id == "waveform-1"
        assert result.format == WaveformFormat.PNG

    async def test_get_existing_json(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Finds JSON waveform by video ID and format."""
        await waveform_repository.add(_make_waveform(waveform_id="w2", fmt=WaveformFormat.JSON))

        result = await waveform_repository.get_by_video_and_format("video-1", WaveformFormat.JSON)
        assert result is not None
        assert result.format == WaveformFormat.JSON

    async def test_get_nonexistent_returns_none(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Returns None for nonexistent video+format pair."""
        await waveform_repository.add(_make_waveform(fmt=WaveformFormat.PNG))

        result = await waveform_repository.get_by_video_and_format("video-1", WaveformFormat.JSON)
        assert result is None

    async def test_format_stored_as_enum_value(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Format is stored as string value and correctly round-trips."""
        await waveform_repository.add(_make_waveform(waveform_id="j1", fmt=WaveformFormat.JSON))
        result = await waveform_repository.get("j1")
        assert result is not None
        assert result.format == WaveformFormat.JSON


@pytest.mark.contract
class TestWaveformUpdateStatus:
    """Tests for update_status() method."""

    async def test_valid_transition_pending_to_generating(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """pending -> generating is a valid transition."""
        await waveform_repository.add(_make_waveform())

        await waveform_repository.update_status("waveform-1", WaveformStatus.GENERATING)

        waveform = await waveform_repository.get("waveform-1")
        assert waveform is not None
        assert waveform.status == WaveformStatus.GENERATING

    async def test_valid_transition_generating_to_ready_sets_file_path(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """generating -> ready sets file_path."""
        await waveform_repository.add(_make_waveform())
        await waveform_repository.update_status("waveform-1", WaveformStatus.GENERATING)

        await waveform_repository.update_status(
            "waveform-1",
            WaveformStatus.READY,
            file_path="/data/waveforms/waveform-1.png",
        )

        waveform = await waveform_repository.get("waveform-1")
        assert waveform is not None
        assert waveform.status == WaveformStatus.READY
        assert waveform.file_path == "/data/waveforms/waveform-1.png"

    async def test_valid_transition_generating_to_error(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """generating -> error is a valid transition."""
        await waveform_repository.add(_make_waveform())
        await waveform_repository.update_status("waveform-1", WaveformStatus.GENERATING)

        await waveform_repository.update_status("waveform-1", WaveformStatus.ERROR)

        waveform = await waveform_repository.get("waveform-1")
        assert waveform is not None
        assert waveform.status == WaveformStatus.ERROR

    async def test_invalid_transition_pending_to_ready_raises(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """pending -> ready is not allowed."""
        await waveform_repository.add(_make_waveform())

        with pytest.raises(ValueError, match="Invalid status transition"):
            await waveform_repository.update_status("waveform-1", WaveformStatus.READY)

    async def test_invalid_transition_error_to_ready_raises(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """error is a terminal state."""
        await waveform_repository.add(_make_waveform())
        await waveform_repository.update_status("waveform-1", WaveformStatus.GENERATING)
        await waveform_repository.update_status("waveform-1", WaveformStatus.ERROR)

        with pytest.raises(ValueError, match="Invalid status transition"):
            await waveform_repository.update_status("waveform-1", WaveformStatus.READY)

    async def test_update_nonexistent_raises(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Updating nonexistent waveform raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await waveform_repository.update_status("nonexistent", WaveformStatus.GENERATING)


@pytest.mark.contract
class TestWaveformDelete:
    """Tests for delete() method."""

    async def test_delete_existing_returns_true(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Deleting an existing waveform returns True."""
        await waveform_repository.add(_make_waveform())

        assert await waveform_repository.delete("waveform-1") is True
        assert await waveform_repository.get("waveform-1") is None

    async def test_delete_nonexistent_returns_false(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """Deleting a nonexistent waveform returns False."""
        assert await waveform_repository.delete("nonexistent") is False


@pytest.mark.contract
class TestWaveformProtocolCompliance:
    """Tests for protocol compliance."""

    def test_sqlite_implements_protocol(self) -> None:
        """SQLiteWaveformRepository is a runtime_checkable Protocol impl."""
        assert issubclass(SQLiteWaveformRepository, AsyncWaveformRepository)

    def test_inmemory_implements_protocol(self) -> None:
        """InMemoryWaveformRepository is a runtime_checkable Protocol impl."""
        assert issubclass(InMemoryWaveformRepository, AsyncWaveformRepository)


@pytest.mark.contract
class TestWaveformRoundTrip:
    """Tests for data round-trip integrity."""

    async def test_all_fields_round_trip(
        self, waveform_repository: AsyncWaveformRepositoryType
    ) -> None:
        """All fields survive create -> get without data loss."""
        now = datetime.now(timezone.utc)
        waveform = Waveform(
            id="rt-1",
            video_id="vid-42",
            format=WaveformFormat.JSON,
            status=WaveformStatus.PENDING,
            created_at=now,
            file_path=None,
            duration=120.5,
            channels=1,
        )

        await waveform_repository.add(waveform)
        result = await waveform_repository.get("rt-1")

        assert result is not None
        assert result.id == "rt-1"
        assert result.video_id == "vid-42"
        assert result.format == WaveformFormat.JSON
        assert result.status == WaveformStatus.PENDING
        assert result.file_path is None
        assert result.duration == 120.5
        assert result.channels == 1
        assert abs((result.created_at - now).total_seconds()) < 1


@pytest.mark.contract
class TestWaveformDeepCopyIsolation:
    """Tests for deepcopy isolation in InMemory implementation."""

    async def test_returned_waveform_is_isolated(self) -> None:
        """Mutating a returned waveform does not affect stored state."""
        repo = InMemoryWaveformRepository()
        waveform = _make_waveform()
        await repo.add(waveform)

        fetched = await repo.get("waveform-1")
        assert fetched is not None
        fetched.file_path = "/MUTATED"

        refetched = await repo.get("waveform-1")
        assert refetched is not None
        assert refetched.file_path is None
