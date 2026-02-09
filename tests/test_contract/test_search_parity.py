"""Parity tests verifying InMemory vs SQLite search behavior.

These tests confirm that the InMemory per-token prefix-match search
produces the same results as SQLite FTS5 for common query patterns.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import aiosqlite
import pytest

from stoat_ferret.db.async_repository import (
    AsyncInMemoryVideoRepository,
    AsyncSQLiteVideoRepository,
)
from stoat_ferret.db.models import Video
from stoat_ferret.db.schema import (
    VIDEOS_FTS,
    VIDEOS_FTS_DELETE_TRIGGER,
    VIDEOS_FTS_INSERT_TRIGGER,
    VIDEOS_FTS_UPDATE_TRIGGER,
    VIDEOS_PATH_INDEX,
    VIDEOS_TABLE,
)


async def _create_video_tables(conn: aiosqlite.Connection) -> None:
    """Create video-related tables for search tests."""
    await conn.execute(VIDEOS_TABLE)
    await conn.execute(VIDEOS_PATH_INDEX)
    await conn.execute(VIDEOS_FTS)
    await conn.execute(VIDEOS_FTS_INSERT_TRIGGER)
    await conn.execute(VIDEOS_FTS_DELETE_TRIGGER)
    await conn.execute(VIDEOS_FTS_UPDATE_TRIGGER)
    await conn.commit()


def _make_video(**kwargs: object) -> Video:
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


@pytest.fixture
async def search_repos() -> AsyncGenerator[
    tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository], None
]:
    """Provide paired InMemory and SQLite repos with the same data."""
    conn = await aiosqlite.connect(":memory:")
    await _create_video_tables(conn)
    mem = AsyncInMemoryVideoRepository()
    sql = AsyncSQLiteVideoRepository(conn)
    yield mem, sql
    await conn.close()


@pytest.mark.contract
class TestSearchParity:
    """Verify InMemory and SQLite search produce consistent results."""

    async def test_single_word_prefix_match(
        self,
        search_repos: tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository],
    ) -> None:
        """Both repos match when query is a prefix of a filename token."""
        mem, sql = search_repos
        video = _make_video(filename="testing_video.mp4", path="/v/testing_video.mp4")
        await mem.add(video)
        await sql.add(video)

        mem_results = await mem.search("test")
        sql_results = await sql.search("test")

        assert len(mem_results) == 1
        assert len(sql_results) == 1
        assert mem_results[0].id == sql_results[0].id

    async def test_non_prefix_substring_no_match(
        self,
        search_repos: tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository],
    ) -> None:
        """Neither repo matches a mid-word substring (not a token prefix)."""
        mem, sql = search_repos
        video = _make_video(filename="testing.mp4", path="/v/testing.mp4")
        await mem.add(video)
        await sql.add(video)

        # "est" is a substring of "testing" but not a prefix of any token
        mem_results = await mem.search("est")
        sql_results = await sql.search("est")

        assert len(mem_results) == 0
        assert len(sql_results) == 0

    async def test_exact_token_match(
        self,
        search_repos: tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository],
    ) -> None:
        """Both repos match when query exactly equals a filename token."""
        mem, sql = search_repos
        video = _make_video(filename="intro_scene.mp4", path="/v/intro_scene.mp4")
        await mem.add(video)
        await sql.add(video)

        mem_results = await mem.search("intro")
        sql_results = await sql.search("intro")

        assert len(mem_results) == 1
        assert len(sql_results) == 1
        assert mem_results[0].id == sql_results[0].id

    async def test_case_insensitive_parity(
        self,
        search_repos: tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository],
    ) -> None:
        """Both repos perform case-insensitive matching."""
        mem, sql = search_repos
        video = _make_video(filename="MyVideo.mp4", path="/v/MyVideo.mp4")
        await mem.add(video)
        await sql.add(video)

        mem_results = await mem.search("myvideo")
        sql_results = await sql.search("myvideo")

        assert len(mem_results) == 1
        assert len(sql_results) == 1

    async def test_no_match_parity(
        self,
        search_repos: tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository],
    ) -> None:
        """Both repos return empty for queries that don't match."""
        mem, sql = search_repos
        video = _make_video(filename="holiday.mp4", path="/v/holiday.mp4")
        await mem.add(video)
        await sql.add(video)

        mem_results = await mem.search("xyz")
        sql_results = await sql.search("xyz")

        assert len(mem_results) == 0
        assert len(sql_results) == 0

    async def test_multiple_videos_prefix_filter(
        self,
        search_repos: tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository],
    ) -> None:
        """Both repos return the same subset of matching videos."""
        mem, sql = search_repos
        v1 = _make_video(filename="beach_sunset.mp4", path="/v/beach_sunset.mp4")
        v2 = _make_video(filename="mountain_view.mp4", path="/v/mountain_view.mp4")
        v3 = _make_video(filename="beach_morning.mp4", path="/v/beach_morning.mp4")

        for v in [v1, v2, v3]:
            await mem.add(v)
            await sql.add(v)

        mem_results = await mem.search("beach")
        sql_results = await sql.search("beach")

        mem_ids = {r.id for r in mem_results}
        sql_ids = {r.id for r in sql_results}

        assert mem_ids == sql_ids
        assert len(mem_ids) == 2

    async def test_path_token_prefix_parity(
        self,
        search_repos: tuple[AsyncInMemoryVideoRepository, AsyncSQLiteVideoRepository],
    ) -> None:
        """Both repos match on path-derived tokens."""
        mem, sql = search_repos
        video = _make_video(
            filename="clip.mp4",
            path="/projects/vacation/summer_trip/clip.mp4",
        )
        await mem.add(video)
        await sql.add(video)

        mem_results = await mem.search("vacation")
        sql_results = await sql.search("vacation")

        assert len(mem_results) == 1
        assert len(sql_results) == 1
        assert mem_results[0].id == sql_results[0].id
