"""Contract tests for async VideoRepository implementations.

These tests run against both AsyncSQLiteVideoRepository and AsyncInMemoryVideoRepository
to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from stoat_ferret.db.async_repository import (
    AsyncInMemoryVideoRepository,
    AsyncSQLiteVideoRepository,
)
from stoat_ferret.db.schema import (
    AUDIT_LOG_INDEX,
    AUDIT_LOG_TABLE,
    VIDEOS_FTS,
    VIDEOS_FTS_DELETE_TRIGGER,
    VIDEOS_FTS_INSERT_TRIGGER,
    VIDEOS_FTS_UPDATE_TRIGGER,
    VIDEOS_PATH_INDEX,
    VIDEOS_TABLE,
)

# Reuse helper from sync tests
from tests.test_repository_contract import make_test_video

AsyncRepositoryType = AsyncSQLiteVideoRepository | AsyncInMemoryVideoRepository


async def create_tables_async(conn: aiosqlite.Connection) -> None:
    """Create all database tables asynchronously."""
    await conn.execute(VIDEOS_TABLE)
    await conn.execute(VIDEOS_PATH_INDEX)
    await conn.execute(VIDEOS_FTS)
    await conn.execute(VIDEOS_FTS_INSERT_TRIGGER)
    await conn.execute(VIDEOS_FTS_DELETE_TRIGGER)
    await conn.execute(VIDEOS_FTS_UPDATE_TRIGGER)
    await conn.execute(AUDIT_LOG_TABLE)
    await conn.execute(AUDIT_LOG_INDEX)
    await conn.commit()


@pytest.fixture(params=["sqlite", "memory"])
async def repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncRepositoryType, None]:
    """Provide both async repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)

        yield AsyncSQLiteVideoRepository(conn)
        await conn.close()
    else:
        yield AsyncInMemoryVideoRepository()


@pytest.mark.contract
class TestAsyncAddAndGet:
    """Tests for async add() and get() methods."""

    async def test_add_and_get(self, repository: AsyncRepositoryType) -> None:
        """Adding a video allows retrieving it by ID."""
        video = make_test_video()
        await repository.add(video)
        retrieved = await repository.get(video.id)

        assert retrieved is not None
        assert retrieved.id == video.id
        assert retrieved.path == video.path
        assert retrieved.filename == video.filename

    async def test_get_nonexistent_returns_none(self, repository: AsyncRepositoryType) -> None:
        """Getting a nonexistent video returns None."""
        result = await repository.get("nonexistent-id")
        assert result is None

    async def test_add_duplicate_id_raises(self, repository: AsyncRepositoryType) -> None:
        """Adding a video with duplicate ID raises ValueError."""
        video = make_test_video()
        await repository.add(video)

        duplicate = make_test_video(id=video.id, path="/videos/different.mp4")
        with pytest.raises(ValueError):
            await repository.add(duplicate)

    async def test_add_duplicate_path_raises(self, repository: AsyncRepositoryType) -> None:
        """Adding a video with duplicate path raises ValueError."""
        video = make_test_video()
        await repository.add(video)

        duplicate = make_test_video(path=video.path)
        with pytest.raises(ValueError):
            await repository.add(duplicate)


@pytest.mark.contract
class TestAsyncGetByPath:
    """Tests for async get_by_path() method."""

    async def test_get_by_path(self, repository: AsyncRepositoryType) -> None:
        """Videos can be retrieved by path."""
        video = make_test_video(path="/videos/unique_path.mp4")
        await repository.add(video)

        retrieved = await repository.get_by_path("/videos/unique_path.mp4")
        assert retrieved is not None
        assert retrieved.id == video.id

    async def test_get_by_path_nonexistent(self, repository: AsyncRepositoryType) -> None:
        """Getting by nonexistent path returns None."""
        result = await repository.get_by_path("/nonexistent/path.mp4")
        assert result is None


@pytest.mark.contract
class TestAsyncListVideos:
    """Tests for async list_videos() method."""

    async def test_list_empty(self, repository: AsyncRepositoryType) -> None:
        """Listing empty repository returns empty list."""
        result = await repository.list_videos()
        assert result == []

    async def test_list_returns_all_videos(self, repository: AsyncRepositoryType) -> None:
        """Listing returns all added videos."""
        video1 = make_test_video()
        video2 = make_test_video()
        await repository.add(video1)
        await repository.add(video2)

        result = await repository.list_videos()
        assert len(result) == 2
        ids = {v.id for v in result}
        assert video1.id in ids
        assert video2.id in ids

    async def test_list_with_limit(self, repository: AsyncRepositoryType) -> None:
        """Limit restricts number of returned videos."""
        for _ in range(5):
            await repository.add(make_test_video())

        result = await repository.list_videos(limit=3)
        assert len(result) == 3

    async def test_list_with_offset(self, repository: AsyncRepositoryType) -> None:
        """Offset skips videos."""
        for _ in range(5):
            await repository.add(make_test_video())

        result = await repository.list_videos(offset=2)
        assert len(result) == 3

    async def test_list_orders_by_created_at_descending(
        self, repository: AsyncRepositoryType
    ) -> None:
        """Videos are returned newest first."""
        now = datetime.now(timezone.utc)
        old_video = make_test_video(created_at=now - timedelta(hours=1))
        new_video = make_test_video(created_at=now)

        await repository.add(old_video)
        await repository.add(new_video)

        result = await repository.list_videos()
        assert result[0].id == new_video.id
        assert result[1].id == old_video.id


@pytest.mark.contract
class TestAsyncSearch:
    """Tests for async search() method."""

    async def test_search_by_filename(self, repository: AsyncRepositoryType) -> None:
        """Search finds videos matching filename."""
        video = make_test_video(filename="my_cool_video.mp4")
        await repository.add(video)

        results = await repository.search("cool")
        assert len(results) == 1
        assert results[0].id == video.id

    async def test_search_by_path(self, repository: AsyncRepositoryType) -> None:
        """Search finds videos matching path."""
        video = make_test_video(path="/videos/vacation/beach_day.mp4")
        await repository.add(video)

        results = await repository.search("beach")
        assert len(results) == 1
        assert results[0].id == video.id

    async def test_search_no_match(self, repository: AsyncRepositoryType) -> None:
        """Search returns empty when nothing matches."""
        video = make_test_video(filename="test.mp4", path="/videos/test.mp4")
        await repository.add(video)

        results = await repository.search("nonexistent")
        assert len(results) == 0

    async def test_search_with_limit(self, repository: AsyncRepositoryType) -> None:
        """Search respects limit parameter."""
        for i in range(5):
            await repository.add(make_test_video(filename=f"video_{i}.mp4"))

        results = await repository.search("video", limit=2)
        assert len(results) == 2

    async def test_search_case_insensitive(self, repository: AsyncRepositoryType) -> None:
        """Search is case-insensitive."""
        video = make_test_video(filename="MyVideo.mp4")
        await repository.add(video)

        results = await repository.search("myvideo")
        assert len(results) == 1


@pytest.mark.contract
class TestAsyncUpdate:
    """Tests for async update() method."""

    async def test_update_changes_video(self, repository: AsyncRepositoryType) -> None:
        """Update modifies video fields."""
        video = make_test_video(filename="original.mp4")
        await repository.add(video)

        updated = replace(video, filename="updated.mp4", updated_at=datetime.now(timezone.utc))
        await repository.update(updated)

        retrieved = await repository.get(video.id)
        assert retrieved is not None
        assert retrieved.filename == "updated.mp4"

    async def test_update_nonexistent_raises(self, repository: AsyncRepositoryType) -> None:
        """Updating nonexistent video raises ValueError."""
        video = make_test_video()
        with pytest.raises(ValueError):
            await repository.update(video)

    async def test_update_path_changes_lookup(self, repository: AsyncRepositoryType) -> None:
        """Updating path allows lookup by new path."""
        video = make_test_video(path="/videos/old.mp4")
        await repository.add(video)

        updated = replace(video, path="/videos/new.mp4")
        await repository.update(updated)

        # Old path should not find video
        assert await repository.get_by_path("/videos/old.mp4") is None
        # New path should find video
        assert await repository.get_by_path("/videos/new.mp4") is not None


@pytest.mark.contract
class TestAsyncCount:
    """Tests for async count() method."""

    async def test_count_empty(self, repository: AsyncRepositoryType) -> None:
        """Count returns zero for empty repository."""
        result = await repository.count()
        assert result == 0

    async def test_count_reflects_adds(self, repository: AsyncRepositoryType) -> None:
        """Count returns the number of stored videos."""
        await repository.add(make_test_video())
        assert await repository.count() == 1

        await repository.add(make_test_video())
        assert await repository.count() == 2

    async def test_count_reflects_deletes(self, repository: AsyncRepositoryType) -> None:
        """Count decreases after deletion."""
        video = make_test_video()
        await repository.add(video)
        assert await repository.count() == 1

        await repository.delete(video.id)
        assert await repository.count() == 0


@pytest.mark.contract
class TestAsyncDelete:
    """Tests for async delete() method."""

    async def test_delete_removes_video(self, repository: AsyncRepositoryType) -> None:
        """Delete removes video from repository."""
        video = make_test_video()
        await repository.add(video)

        result = await repository.delete(video.id)

        assert result is True
        assert await repository.get(video.id) is None

    async def test_delete_nonexistent_returns_false(self, repository: AsyncRepositoryType) -> None:
        """Deleting nonexistent video returns False."""
        result = await repository.delete("nonexistent")
        assert result is False

    async def test_delete_removes_from_path_lookup(self, repository: AsyncRepositoryType) -> None:
        """Delete removes video from path lookup."""
        video = make_test_video()
        await repository.add(video)

        await repository.delete(video.id)

        assert await repository.get_by_path(video.path) is None
