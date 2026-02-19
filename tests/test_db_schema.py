"""Tests for database schema creation."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from stoat_ferret.db.schema import (
    TABLE_VIDEOS,
    TABLE_VIDEOS_FTS,
    create_tables,
)


@pytest.fixture
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Create an in-memory database connection."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


def test_create_tables_creates_videos_table(db_conn: sqlite3.Connection) -> None:
    """Verify that the videos table is created."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert TABLE_VIDEOS in tables


def test_create_tables_creates_fts_table(db_conn: sqlite3.Connection) -> None:
    """Verify that the FTS5 virtual table is created."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert TABLE_VIDEOS_FTS in tables


def test_create_tables_creates_path_index(db_conn: sqlite3.Connection) -> None:
    """Verify that the path index is created."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}

    assert "idx_videos_path" in indexes


def test_videos_table_has_correct_columns(db_conn: sqlite3.Connection) -> None:
    """Verify the videos table has all required columns."""
    cursor = db_conn.cursor()
    cursor.execute("PRAGMA table_info(videos)")
    columns = {row[1] for row in cursor.fetchall()}

    expected_columns = {
        "id",
        "path",
        "filename",
        "duration_frames",
        "frame_rate_numerator",
        "frame_rate_denominator",
        "width",
        "height",
        "video_codec",
        "audio_codec",
        "file_size",
        "thumbnail_path",
        "created_at",
        "updated_at",
    }
    assert columns == expected_columns


def test_fts_search_finds_inserted_video(db_conn: sqlite3.Connection) -> None:
    """Verify FTS search works after inserting a video."""
    db_conn.execute(
        """
        INSERT INTO videos (id, path, filename, duration_frames, frame_rate_numerator,
            frame_rate_denominator, width, height, video_codec, file_size, created_at, updated_at)
        VALUES ('id1', '/path/to/test_video.mp4', 'test_video.mp4', 1000, 24, 1,
                1920, 1080, 'h264', 1000000, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z')
    """
    )
    db_conn.commit()

    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM videos_fts WHERE videos_fts MATCH 'test'")
    results = cursor.fetchall()

    assert len(results) == 1
    assert results[0][0] == "test_video.mp4"


def test_fts_sync_on_delete(db_conn: sqlite3.Connection) -> None:
    """Verify FTS table syncs when a video is deleted."""
    db_conn.execute(
        """
        INSERT INTO videos (id, path, filename, duration_frames, frame_rate_numerator,
            frame_rate_denominator, width, height, video_codec, file_size, created_at, updated_at)
        VALUES ('id1', '/path/to/test_video.mp4', 'test_video.mp4', 1000, 24, 1,
                1920, 1080, 'h264', 1000000, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z')
    """
    )
    db_conn.commit()

    # Verify it's searchable
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM videos_fts WHERE videos_fts MATCH 'test'")
    assert len(cursor.fetchall()) == 1

    # Delete the video
    db_conn.execute("DELETE FROM videos WHERE id = 'id1'")
    db_conn.commit()

    # Verify it's no longer searchable
    cursor.execute("SELECT * FROM videos_fts WHERE videos_fts MATCH 'test'")
    assert len(cursor.fetchall()) == 0


def test_fts_sync_on_update(db_conn: sqlite3.Connection) -> None:
    """Verify FTS table syncs when a video filename is updated."""
    db_conn.execute(
        """
        INSERT INTO videos (id, path, filename, duration_frames, frame_rate_numerator,
            frame_rate_denominator, width, height, video_codec, file_size, created_at, updated_at)
        VALUES ('id1', '/videos/clip.mp4', 'oldname.mp4', 1000, 24, 1,
                1920, 1080, 'h264', 1000000, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z')
    """
    )
    db_conn.commit()

    # Verify oldname is searchable
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM videos_fts WHERE videos_fts MATCH 'oldname'")
    assert len(cursor.fetchall()) == 1

    # Update the filename
    db_conn.execute("UPDATE videos SET filename = 'newname.mp4' WHERE id = 'id1'")
    db_conn.commit()

    # Old name should not be found after update
    cursor.execute("SELECT * FROM videos_fts WHERE videos_fts MATCH 'oldname'")
    assert len(cursor.fetchall()) == 0

    # New name should be found
    cursor.execute("SELECT * FROM videos_fts WHERE videos_fts MATCH 'newname'")
    assert len(cursor.fetchall()) == 1


def test_create_tables_idempotent(db_conn: sqlite3.Connection) -> None:
    """Verify create_tables can be called multiple times safely."""
    # create_tables was already called by the fixture, call it again
    create_tables(db_conn)

    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert TABLE_VIDEOS in tables
    assert TABLE_VIDEOS_FTS in tables


def test_clips_table_has_effects_json_column(db_conn: sqlite3.Connection) -> None:
    """Verify the clips table includes the effects_json column."""
    cursor = db_conn.cursor()
    cursor.execute("PRAGMA table_info(clips)")
    columns = {row[1] for row in cursor.fetchall()}

    assert "effects_json" in columns
