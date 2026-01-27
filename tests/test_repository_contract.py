"""Contract tests for VideoRepository implementations.

These tests run against both SQLiteVideoRepository and InMemoryVideoRepository
to verify they have identical behavior.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from stoat_ferret.db.models import Video
from stoat_ferret.db.repository import InMemoryVideoRepository, SQLiteVideoRepository
from stoat_ferret.db.schema import create_tables


def make_test_video(**kwargs: object) -> Video:
    """Create a test video with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Video.new_id(),
        "path": f"/videos/{Video.new_id()}.mp4",
        "filename": "test.mp4",
        "duration_frames": 1000,
        "frame_rate_numerator": 24,
        "frame_rate_denominator": 1,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "file_size": 1000000,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Video(**defaults)  # type: ignore[arg-type]


RepositoryType = SQLiteVideoRepository | InMemoryVideoRepository


@pytest.fixture(params=["sqlite", "memory"])
def repository(request: pytest.FixtureRequest) -> Generator[RepositoryType, None, None]:
    """Provide both repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = sqlite3.connect(":memory:")
        create_tables(conn)
        yield SQLiteVideoRepository(conn)
        conn.close()
    else:
        yield InMemoryVideoRepository()


class TestAddAndGet:
    """Tests for add() and get() methods."""

    def test_add_and_get(self, repository: RepositoryType) -> None:
        """Adding a video allows retrieving it by ID."""
        video = make_test_video()
        repository.add(video)
        retrieved = repository.get(video.id)

        assert retrieved is not None
        assert retrieved.id == video.id
        assert retrieved.path == video.path
        assert retrieved.filename == video.filename

    def test_get_nonexistent_returns_none(self, repository: RepositoryType) -> None:
        """Getting a nonexistent video returns None."""
        result = repository.get("nonexistent-id")
        assert result is None

    def test_add_duplicate_id_raises(self, repository: RepositoryType) -> None:
        """Adding a video with duplicate ID raises ValueError."""
        video = make_test_video()
        repository.add(video)

        duplicate = make_test_video(id=video.id, path="/videos/different.mp4")
        with pytest.raises(ValueError):
            repository.add(duplicate)

    def test_add_duplicate_path_raises(self, repository: RepositoryType) -> None:
        """Adding a video with duplicate path raises ValueError."""
        video = make_test_video()
        repository.add(video)

        duplicate = make_test_video(path=video.path)
        with pytest.raises(ValueError):
            repository.add(duplicate)


class TestGetByPath:
    """Tests for get_by_path() method."""

    def test_get_by_path(self, repository: RepositoryType) -> None:
        """Videos can be retrieved by path."""
        video = make_test_video(path="/videos/unique_path.mp4")
        repository.add(video)

        retrieved = repository.get_by_path("/videos/unique_path.mp4")
        assert retrieved is not None
        assert retrieved.id == video.id

    def test_get_by_path_nonexistent(self, repository: RepositoryType) -> None:
        """Getting by nonexistent path returns None."""
        result = repository.get_by_path("/nonexistent/path.mp4")
        assert result is None


class TestListVideos:
    """Tests for list_videos() method."""

    def test_list_empty(self, repository: RepositoryType) -> None:
        """Listing empty repository returns empty list."""
        result = repository.list_videos()
        assert result == []

    def test_list_returns_all_videos(self, repository: RepositoryType) -> None:
        """Listing returns all added videos."""
        video1 = make_test_video()
        video2 = make_test_video()
        repository.add(video1)
        repository.add(video2)

        result = repository.list_videos()
        assert len(result) == 2
        ids = {v.id for v in result}
        assert video1.id in ids
        assert video2.id in ids

    def test_list_with_limit(self, repository: RepositoryType) -> None:
        """Limit restricts number of returned videos."""
        for _ in range(5):
            repository.add(make_test_video())

        result = repository.list_videos(limit=3)
        assert len(result) == 3

    def test_list_with_offset(self, repository: RepositoryType) -> None:
        """Offset skips videos."""
        for _ in range(5):
            repository.add(make_test_video())

        result = repository.list_videos(offset=2)
        assert len(result) == 3

    def test_list_orders_by_created_at_descending(self, repository: RepositoryType) -> None:
        """Videos are returned newest first."""
        now = datetime.now(timezone.utc)
        old_video = make_test_video(created_at=now - timedelta(hours=1))
        new_video = make_test_video(created_at=now)

        repository.add(old_video)
        repository.add(new_video)

        result = repository.list_videos()
        assert result[0].id == new_video.id
        assert result[1].id == old_video.id


class TestSearch:
    """Tests for search() method."""

    def test_search_by_filename(self, repository: RepositoryType) -> None:
        """Search finds videos matching filename."""
        video = make_test_video(filename="my_cool_video.mp4")
        repository.add(video)

        results = repository.search("cool")
        assert len(results) == 1
        assert results[0].id == video.id

    def test_search_by_path(self, repository: RepositoryType) -> None:
        """Search finds videos matching path."""
        video = make_test_video(path="/videos/vacation/beach_day.mp4")
        repository.add(video)

        results = repository.search("beach")
        assert len(results) == 1
        assert results[0].id == video.id

    def test_search_no_match(self, repository: RepositoryType) -> None:
        """Search returns empty when nothing matches."""
        video = make_test_video(filename="test.mp4", path="/videos/test.mp4")
        repository.add(video)

        results = repository.search("nonexistent")
        assert len(results) == 0

    def test_search_with_limit(self, repository: RepositoryType) -> None:
        """Search respects limit parameter."""
        for i in range(5):
            repository.add(make_test_video(filename=f"video_{i}.mp4"))

        results = repository.search("video", limit=2)
        assert len(results) == 2

    def test_search_case_insensitive(self, repository: RepositoryType) -> None:
        """Search is case-insensitive."""
        video = make_test_video(filename="MyVideo.mp4")
        repository.add(video)

        results = repository.search("myvideo")
        assert len(results) == 1


class TestUpdate:
    """Tests for update() method."""

    def test_update_changes_video(self, repository: RepositoryType) -> None:
        """Update modifies video fields."""
        video = make_test_video(filename="original.mp4")
        repository.add(video)

        updated = replace(video, filename="updated.mp4", updated_at=datetime.now(timezone.utc))
        repository.update(updated)

        retrieved = repository.get(video.id)
        assert retrieved is not None
        assert retrieved.filename == "updated.mp4"

    def test_update_nonexistent_raises(self, repository: RepositoryType) -> None:
        """Updating nonexistent video raises ValueError."""
        video = make_test_video()
        with pytest.raises(ValueError):
            repository.update(video)

    def test_update_path_changes_lookup(self, repository: RepositoryType) -> None:
        """Updating path allows lookup by new path."""
        video = make_test_video(path="/videos/old.mp4")
        repository.add(video)

        updated = replace(video, path="/videos/new.mp4")
        repository.update(updated)

        # Old path should not find video
        assert repository.get_by_path("/videos/old.mp4") is None
        # New path should find video
        assert repository.get_by_path("/videos/new.mp4") is not None


class TestDelete:
    """Tests for delete() method."""

    def test_delete_removes_video(self, repository: RepositoryType) -> None:
        """Delete removes video from repository."""
        video = make_test_video()
        repository.add(video)

        result = repository.delete(video.id)

        assert result is True
        assert repository.get(video.id) is None

    def test_delete_nonexistent_returns_false(self, repository: RepositoryType) -> None:
        """Deleting nonexistent video returns False."""
        result = repository.delete("nonexistent")
        assert result is False

    def test_delete_removes_from_path_lookup(self, repository: RepositoryType) -> None:
        """Delete removes video from path lookup."""
        video = make_test_video()
        repository.add(video)

        repository.delete(video.id)

        assert repository.get_by_path(video.path) is None


class TestVideoModel:
    """Tests for Video dataclass."""

    def test_frame_rate_property(self) -> None:
        """frame_rate computes correctly."""
        video = make_test_video(frame_rate_numerator=30000, frame_rate_denominator=1001)
        assert abs(video.frame_rate - 29.97) < 0.01

    def test_duration_seconds_property(self) -> None:
        """duration_seconds computes correctly."""
        video = make_test_video(
            duration_frames=240,
            frame_rate_numerator=24,
            frame_rate_denominator=1,
        )
        assert video.duration_seconds == 10.0

    def test_new_id_generates_uuid(self) -> None:
        """new_id generates valid UUIDs."""
        id1 = Video.new_id()
        id2 = Video.new_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID format
