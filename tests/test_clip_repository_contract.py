"""Contract tests for async ClipRepository implementations.

These tests run against both AsyncSQLiteClipRepository and
AsyncInMemoryClipRepository to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.clip_repository import (
    AsyncInMemoryClipRepository,
    AsyncSQLiteClipRepository,
)
from stoat_ferret.db.models import Clip
from stoat_ferret.db.schema import (
    AUDIT_LOG_INDEX,
    AUDIT_LOG_TABLE,
    CLIPS_PROJECT_INDEX,
    CLIPS_TABLE,
    CLIPS_TIMELINE_INDEX,
    PROJECTS_TABLE,
    VIDEOS_FTS,
    VIDEOS_FTS_DELETE_TRIGGER,
    VIDEOS_FTS_INSERT_TRIGGER,
    VIDEOS_FTS_UPDATE_TRIGGER,
    VIDEOS_PATH_INDEX,
    VIDEOS_TABLE,
)

AsyncClipRepositoryType = AsyncSQLiteClipRepository | AsyncInMemoryClipRepository


def make_test_clip(**kwargs: object) -> Clip:
    """Create a test clip with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Clip.new_id(),
        "project_id": "project-1",
        "source_video_id": "video-1",
        "in_point": 0,
        "out_point": 100,
        "timeline_position": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Clip(**defaults)  # type: ignore[arg-type]


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
    await conn.execute(PROJECTS_TABLE)
    await conn.execute(CLIPS_TABLE)
    await conn.execute(CLIPS_PROJECT_INDEX)
    await conn.execute(CLIPS_TIMELINE_INDEX)
    await conn.commit()


async def insert_test_project_and_video(conn: aiosqlite.Connection) -> None:
    """Insert test project and video for foreign key references."""
    await conn.execute(
        """
        INSERT INTO projects (
            id, name, output_width, output_height, output_fps, created_at, updated_at
        ) VALUES (
            'project-1', 'Test', 1920, 1080, 30,
            '2024-01-01T00:00:00', '2024-01-01T00:00:00'
        )
        """
    )
    await conn.execute(
        """
        INSERT INTO projects (
            id, name, output_width, output_height, output_fps, created_at, updated_at
        ) VALUES (
            'project-2', 'Test 2', 1920, 1080, 30,
            '2024-01-01T00:00:00', '2024-01-01T00:00:00'
        )
        """
    )
    await conn.execute(
        """
        INSERT INTO videos (
            id, path, filename, duration_frames, frame_rate_numerator,
            frame_rate_denominator, width, height, video_codec, file_size,
            created_at, updated_at
        ) VALUES (
            'video-1', '/test.mp4', 'test.mp4', 1000, 24, 1, 1920, 1080,
            'h264', 1000000, '2024-01-01T00:00:00', '2024-01-01T00:00:00'
        )
        """
    )
    await conn.commit()


@pytest.fixture(params=["sqlite", "memory"])
async def clip_repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncClipRepositoryType, None]:
    """Provide both async clip repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        await create_tables_async(conn)
        await insert_test_project_and_video(conn)

        yield AsyncSQLiteClipRepository(conn)
        await conn.close()
    else:
        yield AsyncInMemoryClipRepository()


@pytest.mark.contract
class TestAsyncClipAddAndGet:
    """Tests for async add() and get() methods."""

    async def test_add_and_get(self, clip_repository: AsyncClipRepositoryType) -> None:
        """Adding a clip allows retrieving it by ID."""
        clip = make_test_clip()
        await clip_repository.add(clip)
        retrieved = await clip_repository.get(clip.id)

        assert retrieved is not None
        assert retrieved.id == clip.id
        assert retrieved.project_id == clip.project_id
        assert retrieved.source_video_id == clip.source_video_id
        assert retrieved.in_point == clip.in_point
        assert retrieved.out_point == clip.out_point
        assert retrieved.timeline_position == clip.timeline_position

    async def test_get_nonexistent_returns_none(
        self, clip_repository: AsyncClipRepositoryType
    ) -> None:
        """Getting a nonexistent clip returns None."""
        result = await clip_repository.get("nonexistent-id")
        assert result is None

    async def test_add_duplicate_id_raises(self, clip_repository: AsyncClipRepositoryType) -> None:
        """Adding a clip with duplicate ID raises ValueError."""
        clip = make_test_clip()
        await clip_repository.add(clip)

        duplicate = make_test_clip(id=clip.id, timeline_position=200)
        with pytest.raises(ValueError):
            await clip_repository.add(duplicate)


@pytest.mark.contract
class TestAsyncClipListByProject:
    """Tests for async list_by_project() method."""

    async def test_list_empty_project(self, clip_repository: AsyncClipRepositoryType) -> None:
        """Listing empty project returns empty list."""
        result = await clip_repository.list_by_project("project-1")
        assert result == []

    async def test_list_returns_ordered_clips(
        self, clip_repository: AsyncClipRepositoryType
    ) -> None:
        """list_by_project returns clips ordered by timeline position."""
        clip1 = make_test_clip(timeline_position=100)
        clip2 = make_test_clip(timeline_position=0)
        clip3 = make_test_clip(timeline_position=50)

        await clip_repository.add(clip1)
        await clip_repository.add(clip2)
        await clip_repository.add(clip3)

        clips = await clip_repository.list_by_project("project-1")
        assert len(clips) == 3
        assert clips[0].timeline_position == 0
        assert clips[1].timeline_position == 50
        assert clips[2].timeline_position == 100

    async def test_list_filters_by_project(self, clip_repository: AsyncClipRepositoryType) -> None:
        """list_by_project only returns clips for specified project."""
        clip1 = make_test_clip(project_id="project-1")
        clip2 = make_test_clip(project_id="project-2")

        await clip_repository.add(clip1)
        await clip_repository.add(clip2)

        clips = await clip_repository.list_by_project("project-1")
        assert len(clips) == 1
        assert clips[0].project_id == "project-1"


@pytest.mark.contract
class TestAsyncClipUpdate:
    """Tests for async update() method."""

    async def test_update_existing(self, clip_repository: AsyncClipRepositoryType) -> None:
        """Updating existing clip succeeds."""
        clip = make_test_clip()
        await clip_repository.add(clip)

        updated = replace(
            clip,
            in_point=50,
            out_point=150,
            timeline_position=200,
            updated_at=datetime.now(timezone.utc),
        )
        await clip_repository.update(updated)

        retrieved = await clip_repository.get(clip.id)
        assert retrieved is not None
        assert retrieved.in_point == 50
        assert retrieved.out_point == 150
        assert retrieved.timeline_position == 200

    async def test_update_nonexistent_raises(
        self, clip_repository: AsyncClipRepositoryType
    ) -> None:
        """Updating nonexistent clip raises ValueError."""
        clip = make_test_clip()
        with pytest.raises(ValueError):
            await clip_repository.update(clip)


@pytest.mark.contract
class TestAsyncClipDelete:
    """Tests for async delete() method."""

    async def test_delete_existing(self, clip_repository: AsyncClipRepositoryType) -> None:
        """Deleting existing clip returns True."""
        clip = make_test_clip()
        await clip_repository.add(clip)

        result = await clip_repository.delete(clip.id)
        assert result is True
        assert await clip_repository.get(clip.id) is None

    async def test_delete_nonexistent(self, clip_repository: AsyncClipRepositoryType) -> None:
        """Deleting nonexistent clip returns False."""
        result = await clip_repository.delete("nonexistent")
        assert result is False
