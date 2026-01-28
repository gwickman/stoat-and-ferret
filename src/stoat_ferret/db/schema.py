"""Database schema definitions for video metadata storage."""

from __future__ import annotations

import sqlite3

# Table names
TABLE_VIDEOS = "videos"
TABLE_VIDEOS_FTS = "videos_fts"
TABLE_AUDIT_LOG = "audit_log"
TABLE_PROJECTS = "projects"

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

AUDIT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    operation TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    changes_json TEXT,
    context TEXT
);
"""

AUDIT_LOG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_id, timestamp);
"""

PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    output_width INTEGER NOT NULL DEFAULT 1920,
    output_height INTEGER NOT NULL DEFAULT 1080,
    output_fps INTEGER NOT NULL DEFAULT 30,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all database tables and indexes.

    Creates the videos table, path index, FTS5 virtual table,
    triggers to keep FTS in sync with the videos table,
    and the audit_log table for tracking data modifications.

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
    cursor.execute(AUDIT_LOG_TABLE)
    cursor.execute(AUDIT_LOG_INDEX)
    cursor.execute(PROJECTS_TABLE)
    conn.commit()
