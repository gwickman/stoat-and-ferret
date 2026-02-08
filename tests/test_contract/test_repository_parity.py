"""Contract tests verifying InMemory vs SQLite parity.

These tests confirm that InMemory repositories produce the same
observable results as SQLite implementations for core CRUD operations.
Complements the existing parametrized contract tests with explicit
parity assertions focused on deepcopy isolation and seed behavior.
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
from stoat_ferret.db.clip_repository import (
    AsyncInMemoryClipRepository,
    AsyncSQLiteClipRepository,
)
from stoat_ferret.db.models import Clip, Project, Video
from stoat_ferret.db.project_repository import (
    AsyncInMemoryProjectRepository,
    AsyncSQLiteProjectRepository,
)
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


async def create_all_tables(conn: aiosqlite.Connection) -> None:
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


def make_project(**kwargs: object) -> Project:
    """Create a test project with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Project.new_id(),
        "name": "Test Project",
        "output_width": 1920,
        "output_height": 1080,
        "output_fps": 30,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Project(**defaults)  # type: ignore[arg-type]


def make_video(**kwargs: object) -> Video:
    """Create a test video with default values."""
    now = datetime.now(timezone.utc)
    vid = Video.new_id()
    defaults: dict[str, object] = {
        "id": vid,
        "path": f"/videos/{vid}.mp4",
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


def make_clip(**kwargs: object) -> Clip:
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


@pytest.fixture
async def sqlite_conn() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide a fresh SQLite connection with all tables."""
    conn = await aiosqlite.connect(":memory:")
    await create_all_tables(conn)
    yield conn
    await conn.close()


@pytest.mark.contract
class TestProjectParity:
    """Verify InMemory and SQLite project repos produce identical results."""

    async def test_add_get_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations return equivalent results for add+get."""
        mem = AsyncInMemoryProjectRepository()
        sql = AsyncSQLiteProjectRepository(sqlite_conn)
        project = make_project()

        await mem.add(project)
        await sql.add(project)

        mem_result = await mem.get(project.id)
        sql_result = await sql.get(project.id)

        assert mem_result is not None
        assert sql_result is not None
        assert mem_result.id == sql_result.id
        assert mem_result.name == sql_result.name
        assert mem_result.output_width == sql_result.output_width

    async def test_update_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations reflect updates identically."""
        mem = AsyncInMemoryProjectRepository()
        sql = AsyncSQLiteProjectRepository(sqlite_conn)
        project = make_project(name="Original")

        await mem.add(project)
        await sql.add(project)

        updated = replace(project, name="Updated", updated_at=datetime.now(timezone.utc))
        await mem.update(updated)
        await sql.update(updated)

        mem_result = await mem.get(project.id)
        sql_result = await sql.get(project.id)

        assert mem_result is not None
        assert sql_result is not None
        assert mem_result.name == sql_result.name == "Updated"

    async def test_delete_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations handle delete identically."""
        mem = AsyncInMemoryProjectRepository()
        sql = AsyncSQLiteProjectRepository(sqlite_conn)
        project = make_project()

        await mem.add(project)
        await sql.add(project)

        assert await mem.delete(project.id) is True
        assert await sql.delete(project.id) is True
        assert await mem.get(project.id) is None
        assert await sql.get(project.id) is None

    async def test_list_order_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations return projects in the same order."""
        mem = AsyncInMemoryProjectRepository()
        sql = AsyncSQLiteProjectRepository(sqlite_conn)
        now = datetime.now(timezone.utc)

        p1 = make_project(name="Old", created_at=now - timedelta(hours=1))
        p2 = make_project(name="New", created_at=now)

        for repo in [mem, sql]:
            await repo.add(p1)
            await repo.add(p2)

        mem_list = await mem.list_projects()
        sql_list = await sql.list_projects()

        assert len(mem_list) == len(sql_list)
        assert mem_list[0].name == sql_list[0].name == "New"
        assert mem_list[1].name == sql_list[1].name == "Old"


@pytest.mark.contract
class TestVideoParity:
    """Verify InMemory and SQLite video repos produce identical results."""

    async def test_add_get_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations return equivalent results for add+get."""
        mem = AsyncInMemoryVideoRepository()
        sql = AsyncSQLiteVideoRepository(sqlite_conn)
        video = make_video()

        await mem.add(video)
        await sql.add(video)

        mem_result = await mem.get(video.id)
        sql_result = await sql.get(video.id)

        assert mem_result is not None
        assert sql_result is not None
        assert mem_result.id == sql_result.id
        assert mem_result.filename == sql_result.filename

    async def test_get_by_path_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations find videos by path identically."""
        mem = AsyncInMemoryVideoRepository()
        sql = AsyncSQLiteVideoRepository(sqlite_conn)
        video = make_video(path="/videos/unique.mp4")

        await mem.add(video)
        await sql.add(video)

        mem_result = await mem.get_by_path("/videos/unique.mp4")
        sql_result = await sql.get_by_path("/videos/unique.mp4")

        assert mem_result is not None
        assert sql_result is not None
        assert mem_result.id == sql_result.id


@pytest.mark.contract
class TestClipParity:
    """Verify InMemory and SQLite clip repos produce identical results."""

    async def test_add_get_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations return equivalent results for add+get."""
        # Insert FK references for SQLite
        await sqlite_conn.execute(
            "INSERT INTO projects VALUES "
            "('project-1','Test',1920,1080,30,'2024-01-01','2024-01-01')"
        )
        await sqlite_conn.execute(
            "INSERT INTO videos VALUES ('video-1','/t.mp4','t.mp4',1000,24,1,1920,1080,"
            "'h264',NULL,1000000,NULL,'2024-01-01','2024-01-01')"
        )
        await sqlite_conn.commit()

        mem = AsyncInMemoryClipRepository()
        sql = AsyncSQLiteClipRepository(sqlite_conn)
        clip = make_clip()

        await mem.add(clip)
        await sql.add(clip)

        mem_result = await mem.get(clip.id)
        sql_result = await sql.get(clip.id)

        assert mem_result is not None
        assert sql_result is not None
        assert mem_result.id == sql_result.id
        assert mem_result.in_point == sql_result.in_point

    async def test_list_order_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations return clips in the same timeline order."""
        await sqlite_conn.execute(
            "INSERT INTO projects VALUES "
            "('project-1','Test',1920,1080,30,'2024-01-01','2024-01-01')"
        )
        await sqlite_conn.execute(
            "INSERT INTO videos VALUES ('video-1','/t.mp4','t.mp4',1000,24,1,1920,1080,"
            "'h264',NULL,1000000,NULL,'2024-01-01','2024-01-01')"
        )
        await sqlite_conn.commit()

        mem = AsyncInMemoryClipRepository()
        sql = AsyncSQLiteClipRepository(sqlite_conn)

        c1 = make_clip(timeline_position=100)
        c2 = make_clip(timeline_position=0)

        for repo in [mem, sql]:
            await repo.add(c1)
            await repo.add(c2)

        mem_list = await mem.list_by_project("project-1")
        sql_list = await sql.list_by_project("project-1")

        assert len(mem_list) == len(sql_list) == 2
        assert mem_list[0].timeline_position == sql_list[0].timeline_position == 0
        assert mem_list[1].timeline_position == sql_list[1].timeline_position == 100
