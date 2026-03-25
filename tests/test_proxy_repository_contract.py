"""Contract tests for async ProxyRepository implementations.

These tests run against both SQLiteProxyRepository and
InMemoryProxyRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus
from stoat_ferret.db.proxy_repository import (
    AsyncProxyRepository,
    InMemoryProxyRepository,
    SQLiteProxyRepository,
)
from stoat_ferret.db.schema import create_tables_async

AsyncProxyRepositoryType = SQLiteProxyRepository | InMemoryProxyRepository


def _make_proxy(
    *,
    proxy_id: str = "proxy-1",
    source_video_id: str = "video-1",
    quality: ProxyQuality = ProxyQuality.MEDIUM,
    file_path: str = "/data/proxies/video-1_medium.mp4",
    source_checksum: str = "abc123",
) -> ProxyFile:
    """Create a ProxyFile instance for testing."""
    return ProxyFile(
        id=proxy_id,
        source_video_id=source_video_id,
        quality=quality,
        file_path=file_path,
        file_size_bytes=0,
        status=ProxyStatus.PENDING,
        source_checksum=source_checksum,
        generated_at=None,
        last_accessed_at=datetime.now(timezone.utc),
    )


@pytest.fixture(params=["sqlite", "memory"])
async def proxy_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncProxyRepositoryType, None]:
    """Provide both async proxy repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield SQLiteProxyRepository(conn)
        await conn.close()
    else:
        yield InMemoryProxyRepository()


@pytest.mark.contract
class TestProxyAdd:
    """Tests for add() method."""

    async def test_add_returns_proxy_with_all_fields(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Added proxy retains all field values."""
        proxy = _make_proxy()
        result = await proxy_repository.add(proxy)

        assert result.id == "proxy-1"
        assert result.source_video_id == "video-1"
        assert result.quality == ProxyQuality.MEDIUM
        assert result.file_path == "/data/proxies/video-1_medium.mp4"
        assert result.file_size_bytes == 0
        assert result.status == ProxyStatus.PENDING
        assert result.source_checksum == "abc123"
        assert result.generated_at is None
        assert result.last_accessed_at is not None

    async def test_add_duplicate_video_quality_raises(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Inserting duplicate (video_id, quality) pair raises ValueError."""
        await proxy_repository.add(_make_proxy(proxy_id="p1"))

        with pytest.raises(ValueError, match="already exists"):
            await proxy_repository.add(_make_proxy(proxy_id="p2"))

    async def test_add_different_quality_same_video_ok(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Different quality levels for the same video are allowed."""
        await proxy_repository.add(
            _make_proxy(proxy_id="p1", quality=ProxyQuality.LOW, file_path="/low.mp4")
        )
        result = await proxy_repository.add(
            _make_proxy(proxy_id="p2", quality=ProxyQuality.HIGH, file_path="/high.mp4")
        )

        assert result.quality == ProxyQuality.HIGH


@pytest.mark.contract
class TestProxyGet:
    """Tests for get() method."""

    async def test_get_existing(self, proxy_repository: AsyncProxyRepositoryType) -> None:
        """get returns the correct proxy by ID."""
        await proxy_repository.add(_make_proxy())

        result = await proxy_repository.get("proxy-1")
        assert result is not None
        assert result.id == "proxy-1"
        assert result.quality == ProxyQuality.MEDIUM

    async def test_get_nonexistent_returns_none(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """get returns None for nonexistent ID."""
        result = await proxy_repository.get("nonexistent")
        assert result is None


@pytest.mark.contract
class TestProxyGetByVideoAndQuality:
    """Tests for get_by_video_and_quality() method."""

    async def test_get_existing_pair(self, proxy_repository: AsyncProxyRepositoryType) -> None:
        """Finds proxy by video ID and quality."""
        await proxy_repository.add(_make_proxy())

        result = await proxy_repository.get_by_video_and_quality("video-1", ProxyQuality.MEDIUM)
        assert result is not None
        assert result.id == "proxy-1"

    async def test_get_nonexistent_pair_returns_none(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Returns None for nonexistent video+quality pair."""
        await proxy_repository.add(_make_proxy())

        result = await proxy_repository.get_by_video_and_quality("video-1", ProxyQuality.HIGH)
        assert result is None


@pytest.mark.contract
class TestProxyListByVideo:
    """Tests for list_by_video() method."""

    async def test_empty_returns_empty_list(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """No proxies for a video returns empty list."""
        result = await proxy_repository.list_by_video("nonexistent")
        assert result == []

    async def test_returns_all_proxies_for_video(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Returns all proxies for the given video."""
        await proxy_repository.add(
            _make_proxy(proxy_id="p1", quality=ProxyQuality.LOW, file_path="/low.mp4")
        )
        await proxy_repository.add(
            _make_proxy(proxy_id="p2", quality=ProxyQuality.HIGH, file_path="/high.mp4")
        )
        # Different video
        await proxy_repository.add(
            _make_proxy(
                proxy_id="p3",
                source_video_id="video-2",
                file_path="/other.mp4",
            )
        )

        result = await proxy_repository.list_by_video("video-1")
        assert len(result) == 2
        assert {p.quality for p in result} == {ProxyQuality.LOW, ProxyQuality.HIGH}

    async def test_does_not_return_other_videos(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Only returns proxies for the requested video."""
        await proxy_repository.add(_make_proxy())
        await proxy_repository.add(
            _make_proxy(
                proxy_id="p2",
                source_video_id="video-2",
                file_path="/other.mp4",
            )
        )

        result = await proxy_repository.list_by_video("video-2")
        assert len(result) == 1
        assert result[0].source_video_id == "video-2"


@pytest.mark.contract
class TestProxyUpdateStatus:
    """Tests for update_status() method."""

    async def test_valid_transition_pending_to_generating(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """pending -> generating is a valid transition."""
        await proxy_repository.add(_make_proxy())

        await proxy_repository.update_status("proxy-1", ProxyStatus.GENERATING)

        proxy = await proxy_repository.get("proxy-1")
        assert proxy is not None
        assert proxy.status == ProxyStatus.GENERATING

    async def test_valid_transition_generating_to_ready_sets_generated_at(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """generating -> ready sets generated_at timestamp."""
        await proxy_repository.add(_make_proxy())
        await proxy_repository.update_status("proxy-1", ProxyStatus.GENERATING)

        await proxy_repository.update_status("proxy-1", ProxyStatus.READY, file_size_bytes=1024)

        proxy = await proxy_repository.get("proxy-1")
        assert proxy is not None
        assert proxy.status == ProxyStatus.READY
        assert proxy.generated_at is not None
        assert proxy.file_size_bytes == 1024

    async def test_valid_transition_generating_to_failed(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """generating -> failed is a valid transition."""
        await proxy_repository.add(_make_proxy())
        await proxy_repository.update_status("proxy-1", ProxyStatus.GENERATING)

        await proxy_repository.update_status("proxy-1", ProxyStatus.FAILED)

        proxy = await proxy_repository.get("proxy-1")
        assert proxy is not None
        assert proxy.status == ProxyStatus.FAILED

    async def test_valid_transition_ready_to_stale(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """ready -> stale is a valid transition."""
        await proxy_repository.add(_make_proxy())
        await proxy_repository.update_status("proxy-1", ProxyStatus.GENERATING)
        await proxy_repository.update_status("proxy-1", ProxyStatus.READY)

        await proxy_repository.update_status("proxy-1", ProxyStatus.STALE)

        proxy = await proxy_repository.get("proxy-1")
        assert proxy is not None
        assert proxy.status == ProxyStatus.STALE

    async def test_invalid_transition_pending_to_ready_raises(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """pending -> ready is not allowed."""
        await proxy_repository.add(_make_proxy())

        with pytest.raises(ValueError, match="Invalid status transition"):
            await proxy_repository.update_status("proxy-1", ProxyStatus.READY)

    async def test_invalid_transition_failed_to_ready_raises(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """failed is a terminal state."""
        await proxy_repository.add(_make_proxy())
        await proxy_repository.update_status("proxy-1", ProxyStatus.GENERATING)
        await proxy_repository.update_status("proxy-1", ProxyStatus.FAILED)

        with pytest.raises(ValueError, match="Invalid status transition"):
            await proxy_repository.update_status("proxy-1", ProxyStatus.READY)

    async def test_update_nonexistent_raises(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Updating nonexistent proxy raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await proxy_repository.update_status("nonexistent", ProxyStatus.GENERATING)

    async def test_update_status_updates_last_accessed(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Status update changes last_accessed_at timestamp."""
        proxy = _make_proxy()
        original_accessed = proxy.last_accessed_at
        await proxy_repository.add(proxy)

        await proxy_repository.update_status("proxy-1", ProxyStatus.GENERATING)

        updated = await proxy_repository.get("proxy-1")
        assert updated is not None
        assert updated.last_accessed_at >= original_accessed


@pytest.mark.contract
class TestProxyDelete:
    """Tests for delete() method."""

    async def test_delete_existing_returns_true(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Deleting an existing proxy returns True."""
        await proxy_repository.add(_make_proxy())

        assert await proxy_repository.delete("proxy-1") is True
        assert await proxy_repository.get("proxy-1") is None

    async def test_delete_nonexistent_returns_false(
        self, proxy_repository: AsyncProxyRepositoryType
    ) -> None:
        """Deleting a nonexistent proxy returns False."""
        assert await proxy_repository.delete("nonexistent") is False


@pytest.mark.contract
class TestProxyCount:
    """Tests for count() method."""

    async def test_count_empty(self, proxy_repository: AsyncProxyRepositoryType) -> None:
        """Empty repository has count 0."""
        assert await proxy_repository.count() == 0

    async def test_count_after_adds(self, proxy_repository: AsyncProxyRepositoryType) -> None:
        """Count reflects number of added proxies."""
        await proxy_repository.add(
            _make_proxy(proxy_id="p1", quality=ProxyQuality.LOW, file_path="/low.mp4")
        )
        await proxy_repository.add(
            _make_proxy(proxy_id="p2", quality=ProxyQuality.HIGH, file_path="/high.mp4")
        )

        assert await proxy_repository.count() == 2

    async def test_count_after_delete(self, proxy_repository: AsyncProxyRepositoryType) -> None:
        """Count decreases after delete."""
        await proxy_repository.add(_make_proxy())

        await proxy_repository.delete("proxy-1")

        assert await proxy_repository.count() == 0


@pytest.mark.contract
class TestProxyProtocolCompliance:
    """Tests for protocol compliance."""

    def test_sqlite_implements_protocol(self) -> None:
        """SQLiteProxyRepository is a runtime_checkable Protocol impl."""
        assert issubclass(SQLiteProxyRepository, AsyncProxyRepository)

    def test_inmemory_implements_protocol(self) -> None:
        """InMemoryProxyRepository is a runtime_checkable Protocol impl."""
        assert issubclass(InMemoryProxyRepository, AsyncProxyRepository)


@pytest.mark.contract
class TestProxyRoundTrip:
    """Tests for data round-trip integrity."""

    async def test_all_fields_round_trip(self, proxy_repository: AsyncProxyRepositoryType) -> None:
        """All fields survive create -> get without data loss."""
        now = datetime.now(timezone.utc)
        proxy = ProxyFile(
            id="rt-1",
            source_video_id="vid-42",
            quality=ProxyQuality.HIGH,
            file_path="/data/proxies/vid-42_high.mp4",
            file_size_bytes=0,
            status=ProxyStatus.PENDING,
            source_checksum="sha256-deadbeef",
            generated_at=None,
            last_accessed_at=now,
        )

        await proxy_repository.add(proxy)
        result = await proxy_repository.get("rt-1")

        assert result is not None
        assert result.id == "rt-1"
        assert result.source_video_id == "vid-42"
        assert result.quality == ProxyQuality.HIGH
        assert result.file_path == "/data/proxies/vid-42_high.mp4"
        assert result.file_size_bytes == 0
        assert result.status == ProxyStatus.PENDING
        assert result.source_checksum == "sha256-deadbeef"
        assert result.generated_at is None
        # Timestamp comparison: allow microsecond precision loss in SQLite
        assert abs((result.last_accessed_at - now).total_seconds()) < 1


@pytest.mark.contract
class TestProxyDeepCopyIsolation:
    """Tests for deepcopy isolation in InMemory implementation."""

    async def test_returned_proxy_is_isolated(self) -> None:
        """Mutating a returned proxy does not affect stored state."""
        repo = InMemoryProxyRepository()
        proxy = _make_proxy()
        await repo.add(proxy)

        fetched = await repo.get("proxy-1")
        assert fetched is not None
        fetched.file_path = "/MUTATED"

        refetched = await repo.get("proxy-1")
        assert refetched is not None
        assert refetched.file_path == "/data/proxies/video-1_medium.mp4"
