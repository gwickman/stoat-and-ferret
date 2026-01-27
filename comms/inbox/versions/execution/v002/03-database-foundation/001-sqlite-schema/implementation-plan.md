# Implementation Plan: SQLite Schema

## Step 1: Create Module Structure
```bash
mkdir -p src/stoat_ferret/db
touch src/stoat_ferret/db/__init__.py
touch src/stoat_ferret/db/schema.py
```

## Step 2: Define Schema SQL
In `src/stoat_ferret/db/schema.py`:

```python
"""Database schema definitions."""

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
    INSERT INTO videos_fts(videos_fts, rowid, filename, path) VALUES ('delete', old.rowid, old.filename, old.path);
END;
"""

VIDEOS_FTS_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS videos_fts_update AFTER UPDATE ON videos BEGIN
    INSERT INTO videos_fts(videos_fts, rowid, filename, path) VALUES ('delete', old.rowid, old.filename, old.path);
    INSERT INTO videos_fts(rowid, filename, path) VALUES (new.rowid, new.filename, new.path);
END;
"""


def create_tables(conn) -> None:
    """Create all database tables."""
    cursor = conn.cursor()
    cursor.execute(VIDEOS_TABLE)
    cursor.execute(VIDEOS_PATH_INDEX)
    cursor.execute(VIDEOS_FTS)
    cursor.execute(VIDEOS_FTS_INSERT_TRIGGER)
    cursor.execute(VIDEOS_FTS_DELETE_TRIGGER)
    cursor.execute(VIDEOS_FTS_UPDATE_TRIGGER)
    conn.commit()
```

## Step 3: Add Tests
Create `tests/test_db_schema.py`:

```python
import sqlite3
from stoat_ferret.db.schema import create_tables

def test_create_tables():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    
    # Verify tables exist
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    assert "videos" in tables
    assert "videos_fts" in tables

def test_fts_search():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    
    # Insert test data
    conn.execute("""
        INSERT INTO videos (id, path, filename, duration_frames, frame_rate_numerator,
            frame_rate_denominator, width, height, video_codec, file_size, created_at, updated_at)
        VALUES ('id1', '/path/to/test_video.mp4', 'test_video.mp4', 1000, 24, 1, 1920, 1080, 'h264', 1000000, '2024-01-01', '2024-01-01')
    """)
    conn.commit()
    
    # Search
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos_fts WHERE videos_fts MATCH 'test'")
    results = cursor.fetchall()
    
    assert len(results) == 1
```

## Verification
- `uv run pytest tests/test_db_schema.py -v` passes