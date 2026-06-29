# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

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
from stoat_ferret.db.ducking_pair_repository import (
    AsyncInMemoryDuckingPairRepository,
    AsyncSQLiteDuckingPairRepository,
)
from stoat_ferret.db.models import Clip, DuckingPair, Project, Track, Video
from stoat_ferret.db.project_repository import (
    AsyncInMemoryProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.db.schema import (
    AUDIT_LOG_INDEX,
    AUDIT_LOG_TABLE,
    CLIPS_IMAGE_COLUMNS,
    CLIPS_PROJECT_INDEX,
    CLIPS_TABLE,
    CLIPS_TIMELINE_COLUMNS,
    CLIPS_TIMELINE_INDEX,
    DUCKING_PAIR_PROJECT_INDEX,
    DUCKING_PAIR_TABLE,
    PROJECTS_AUDIO_BASELINE_COLUMNS,
    PROJECTS_AUDIO_MIX_COLUMNS,
    PROJECTS_TABLE,
    TRACKS_AUDIO_COLUMNS,
    TRACKS_PROJECT_INDEX,
    TRACKS_TABLE,
    TTS_CUE_PROJECT_INDEX,
    TTS_CUE_TABLE,
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
    await conn.execute(TRACKS_TABLE)
    await conn.execute(TRACKS_PROJECT_INDEX)
    await conn.execute(DUCKING_PAIR_TABLE)
    await conn.execute(DUCKING_PAIR_PROJECT_INDEX)
    await conn.execute(TTS_CUE_TABLE)
    await conn.execute(TTS_CUE_PROJECT_INDEX)
    # Apply migrations for columns added after initial schema
    for col, col_type in CLIPS_TIMELINE_COLUMNS:
        await conn.execute(f"ALTER TABLE clips ADD COLUMN {col} {col_type}")
    for col, col_type in CLIPS_IMAGE_COLUMNS:
        await conn.execute(f"ALTER TABLE clips ADD COLUMN {col} {col_type}")
    for col, col_type in PROJECTS_AUDIO_MIX_COLUMNS:
        await conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {col_type}")
    for col, col_type in PROJECTS_AUDIO_BASELINE_COLUMNS:
        await conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {col_type}")
    for col, col_type in TRACKS_AUDIO_COLUMNS:
        await conn.execute(f"ALTER TABLE tracks ADD COLUMN {col} {col_type}")
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
            "('project-1','Test',1920,1080,30,NULL,'2024-01-01','2024-01-01',NULL,48000,24)"
        )
        await sqlite_conn.execute(
            "INSERT INTO videos VALUES ('video-1','/t.mp4','t.mp4',1000,24,1,1920,1080,"
            "'h264',NULL,1000000,NULL,'2024-01-01','2024-01-01',0,0,'[]')"
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
            "('project-1','Test',1920,1080,30,NULL,'2024-01-01','2024-01-01',NULL,48000,24)"
        )
        await sqlite_conn.execute(
            "INSERT INTO videos VALUES ('video-1','/t.mp4','t.mp4',1000,24,1,1920,1080,"
            "'h264',NULL,1000000,NULL,'2024-01-01','2024-01-01',0,0,'[]')"
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


def make_track(**kwargs: object) -> Track:
    """Create a test track with default values."""
    defaults: dict[str, object] = {
        "id": Track.new_id(),
        "project_id": "project-1",
        "track_type": "audio",
        "label": "Test Track",
        "z_index": 0,
        "muted": False,
        "locked": False,
        "kind": None,
        "volume_envelope": None,
        "weight": 1.0,
    }
    defaults.update(kwargs)
    return Track(**defaults)  # type: ignore[arg-type]


def make_ducking_pair(**kwargs: object) -> DuckingPair:
    """Create a test ducking pair with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": DuckingPair.new_id(),
        "project_id": "project-1",
        "ducked_track_id": "track-music",
        "sidechain_track_id": "track-voice",
        "threshold": 0.02,
        "ratio": 8.0,
        "attack_ms": 20.0,
        "release_ms": 300.0,
        "apply_pre_volume": False,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return DuckingPair(**defaults)  # type: ignore[arg-type]


@pytest.mark.contract
class TestDuckingPairParity:
    """Verify InMemory and SQLite DuckingPair repos produce identical results (BL-517)."""

    async def _seed_project_and_tracks(self, conn: aiosqlite.Connection) -> None:
        """Insert FK-required project and two tracks into the SQLite DB."""
        await conn.execute(
            "INSERT INTO projects VALUES "
            "('project-1','Test',1920,1080,30,NULL,'2024-01-01','2024-01-01',NULL,48000,24)"
        )
        await conn.execute(
            "INSERT INTO tracks (id, project_id, track_type, label, z_index, muted, locked) "
            "VALUES ('track-music','project-1','audio','Music',0,0,0)"
        )
        await conn.execute(
            "INSERT INTO tracks (id, project_id, track_type, label, z_index, muted, locked) "
            "VALUES ('track-voice','project-1','audio','Voice',1,0,0)"
        )
        await conn.commit()

    async def test_create_get_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations return equivalent results for create+get."""
        await self._seed_project_and_tracks(sqlite_conn)
        mem = AsyncInMemoryDuckingPairRepository()
        sql = AsyncSQLiteDuckingPairRepository(sqlite_conn)
        pair = make_ducking_pair()

        await mem.create(pair)
        await sql.create(pair)

        mem_result = await mem.get(pair.id)
        sql_result = await sql.get(pair.id)

        assert mem_result is not None
        assert sql_result is not None
        assert mem_result.id == sql_result.id
        assert mem_result.ducked_track_id == sql_result.ducked_track_id == "track-music"
        assert mem_result.sidechain_track_id == sql_result.sidechain_track_id == "track-voice"
        assert mem_result.threshold == sql_result.threshold == pytest.approx(0.02)
        assert mem_result.ratio == sql_result.ratio == pytest.approx(8.0)

    async def test_list_by_project_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations list pairs for a project in created_at order."""
        await self._seed_project_and_tracks(sqlite_conn)
        mem = AsyncInMemoryDuckingPairRepository()
        sql = AsyncSQLiteDuckingPairRepository(sqlite_conn)

        p1 = make_ducking_pair(id=DuckingPair.new_id())
        p2 = make_ducking_pair(id=DuckingPair.new_id())

        for repo in [mem, sql]:
            await repo.create(p1)
            await repo.create(p2)

        mem_list = await mem.list_by_project("project-1")
        sql_list = await sql.list_by_project("project-1")

        assert len(mem_list) == len(sql_list) == 2

    async def test_update_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations reflect mutable field updates identically."""
        await self._seed_project_and_tracks(sqlite_conn)
        mem = AsyncInMemoryDuckingPairRepository()
        sql = AsyncSQLiteDuckingPairRepository(sqlite_conn)
        pair = make_ducking_pair()

        await mem.create(pair)
        await sql.create(pair)

        now = datetime.now(timezone.utc)
        updated = DuckingPair(
            id=pair.id,
            project_id=pair.project_id,
            ducked_track_id=pair.ducked_track_id,
            sidechain_track_id=pair.sidechain_track_id,
            threshold=0.05,
            ratio=4.0,
            attack_ms=pair.attack_ms,
            release_ms=pair.release_ms,
            apply_pre_volume=True,
            created_at=pair.created_at,
            updated_at=now,
        )

        mem_result = await mem.update(updated)
        sql_result = await sql.update(updated)

        assert mem_result.threshold == sql_result.threshold == pytest.approx(0.05)
        assert mem_result.ratio == sql_result.ratio == pytest.approx(4.0)
        assert mem_result.apply_pre_volume == sql_result.apply_pre_volume is True

    async def test_delete_parity(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Both implementations handle delete identically."""
        await self._seed_project_and_tracks(sqlite_conn)
        mem = AsyncInMemoryDuckingPairRepository()
        sql = AsyncSQLiteDuckingPairRepository(sqlite_conn)
        pair = make_ducking_pair()

        await mem.create(pair)
        await sql.create(pair)

        assert await mem.delete(pair.id) is True
        assert await sql.delete(pair.id) is True
        assert await mem.get(pair.id) is None
        assert await sql.get(pair.id) is None

    async def test_track_audio_columns_present(self, sqlite_conn: aiosqlite.Connection) -> None:
        """Track table has kind, volume_envelope, weight columns from BL-517 migration."""
        cursor = await sqlite_conn.execute("PRAGMA table_info(tracks)")
        rows = await cursor.fetchall()
        col_names = {row[1] for row in rows}
        assert "kind" in col_names, "tracks.kind column missing"
        assert "volume_envelope" in col_names, "tracks.volume_envelope column missing"
        assert "weight" in col_names, "tracks.weight column missing"

    async def test_ducking_pair_table_columns(self, sqlite_conn: aiosqlite.Connection) -> None:
        """ducking_pair table exists with all required columns."""
        cursor = await sqlite_conn.execute("PRAGMA table_info(ducking_pair)")
        rows = await cursor.fetchall()
        col_names = {row[1] for row in rows}
        required = {
            "id",
            "project_id",
            "ducked_track_id",
            "sidechain_track_id",
            "threshold",
            "ratio",
            "attack_ms",
            "release_ms",
            "apply_pre_volume",
            "created_at",
            "updated_at",
        }
        missing = required - col_names
        assert not missing, f"ducking_pair table missing columns: {missing}"

    async def test_tts_cue_table_columns(self, sqlite_conn: aiosqlite.Connection) -> None:
        """tts_cue table exists with all required columns (BL-516)."""
        cursor = await sqlite_conn.execute("PRAGMA table_info(tts_cue)")
        rows = await cursor.fetchall()
        col_names = {row[1] for row in rows}
        required = {
            "id",
            "project_id",
            "track_id",
            "start_s",
            "text",
            "voice",
            "backend",
            "gain_db",
            "pan",
            "cache_key",
            "generated_asset_id",
            "status",
            "error",
            "created_at",
            "updated_at",
        }
        missing = required - col_names
        assert not missing, f"tts_cue table missing columns: {missing}"
