# Implementation Plan: Migration Support

## Step 1: Add Alembic Dependency
Edit pyproject.toml:
```toml
[project]
dependencies = [
    "alembic>=1.13",
]
```

Run `uv sync`.

## Step 2: Initialize Alembic
```bash
uv run alembic init alembic
```

## Step 3: Configure alembic.ini
Edit alembic.ini:
```ini
sqlalchemy.url = sqlite:///stoat_ferret.db
```

## Step 4: Configure env.py
Edit alembic/env.py to support SQLite properly and handle the FTS5 virtual tables.

## Step 5: Create Initial Migration
```bash
uv run alembic revision -m "initial_schema"
```

Edit generated migration file:
```python
"""initial_schema

Revision ID: 001
"""
from alembic import op

def upgrade():
    op.execute("""
        CREATE TABLE videos (
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
        )
    """)
    op.execute("CREATE INDEX idx_videos_path ON videos(path)")
    op.execute("""
        CREATE VIRTUAL TABLE videos_fts USING fts5(
            filename, path, content='videos', content_rowid='rowid'
        )
    """)
    # Insert/update/delete triggers for FTS sync
    op.execute("""
        CREATE TRIGGER videos_fts_insert AFTER INSERT ON videos BEGIN
            INSERT INTO videos_fts(rowid, filename, path) 
            VALUES (new.rowid, new.filename, new.path);
        END
    """)
    op.execute("""
        CREATE TRIGGER videos_fts_delete AFTER DELETE ON videos BEGIN
            INSERT INTO videos_fts(videos_fts, rowid, filename, path) 
            VALUES ('delete', old.rowid, old.filename, old.path);
        END
    """)
    op.execute("""
        CREATE TRIGGER videos_fts_update AFTER UPDATE ON videos BEGIN
            INSERT INTO videos_fts(videos_fts, rowid, filename, path) 
            VALUES ('delete', old.rowid, old.filename, old.path);
            INSERT INTO videos_fts(rowid, filename, path) 
            VALUES (new.rowid, new.filename, new.path);
        END
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS videos_fts_update")
    op.execute("DROP TRIGGER IF EXISTS videos_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS videos_fts_insert")
    op.execute("DROP TABLE IF EXISTS videos_fts")
    op.execute("DROP INDEX IF EXISTS idx_videos_path")
    op.execute("DROP TABLE IF EXISTS videos")
```

## Step 6: Test Migrations
```bash
uv run alembic upgrade head
uv run alembic current
uv run alembic downgrade -1
uv run alembic upgrade head
```

## Verification
- Alembic commands work
- Integration test passes