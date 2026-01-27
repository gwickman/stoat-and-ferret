"""Database schema definitions for video metadata storage."""

from __future__ import annotations

import sqlite3

# Table names
TABLE_VIDEOS = "videos"
TABLE_VIDEOS_FTS = "videos_fts"

VIDEOS_TABLE = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    duration_frames INTEGER NOT NULL,
    frame_rate_numerator INTEGER NOT NULL,
    frame_rate_denominator INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    video_codec TEXT NOT NULL,
    audio_codec TEXT,
    file_size INTEGER NOT NULL,
    thumbnail_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

VIDEOS_PATH_INDEX = """
CREATE INDEX IF NOT EXISTS idx_videos_path ON videos(path);
"""

VIDEOS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
    filename,
    path,
    content='videos',
    content_rowid='rowid'
);
"""

VIDEOS_FTS_INSERT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS videos_fts_insert AFTER INSERT ON videos BEGIN
    INSERT INTO videos_fts(rowid, filename, path) VALUES (new.rowid, new.filename, new.path);
END;
"""

VIDEOS_FTS_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS videos_fts_delete AFTER DELETE ON videos BEGIN
    INSERT INTO videos_fts(videos_fts, rowid, filename, path)
    VALUES ('delete', old.rowid, old.filename, old.path);
END;
"""

VIDEOS_FTS_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS videos_fts_update AFTER UPDATE ON videos BEGIN
    INSERT INTO videos_fts(videos_fts, rowid, filename, path)
    VALUES ('delete', old.rowid, old.filename, old.path);
    INSERT INTO videos_fts(rowid, filename, path)
    VALUES (new.rowid, new.filename, new.path);
END;
"""


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all database tables and indexes.

    Creates the videos table, path index, FTS5 virtual table,
    and triggers to keep FTS in sync with the videos table.

    Args:
        conn: SQLite database connection.
    """
    cursor = conn.cursor()
    cursor.execute(VIDEOS_TABLE)
    cursor.execute(VIDEOS_PATH_INDEX)
    cursor.execute(VIDEOS_FTS)
    cursor.execute(VIDEOS_FTS_INSERT_TRIGGER)
    cursor.execute(VIDEOS_FTS_DELETE_TRIGGER)
    cursor.execute(VIDEOS_FTS_UPDATE_TRIGGER)
    conn.commit()
