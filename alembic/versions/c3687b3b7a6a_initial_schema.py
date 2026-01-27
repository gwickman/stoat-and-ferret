"""initial_schema

Revision ID: c3687b3b7a6a
Revises:
Create Date: 2026-01-27 22:32:24.719551

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3687b3b7a6a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema: videos table, path index, FTS5, and triggers."""
    # Create videos table
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

    # Create path index
    op.execute("CREATE INDEX idx_videos_path ON videos(path)")

    # Create FTS5 virtual table
    op.execute("""
        CREATE VIRTUAL TABLE videos_fts USING fts5(
            filename,
            path,
            content='videos',
            content_rowid='rowid'
        )
    """)

    # Create FTS insert trigger
    op.execute("""
        CREATE TRIGGER videos_fts_insert AFTER INSERT ON videos BEGIN
            INSERT INTO videos_fts(rowid, filename, path)
            VALUES (new.rowid, new.filename, new.path);
        END
    """)

    # Create FTS delete trigger
    op.execute("""
        CREATE TRIGGER videos_fts_delete AFTER DELETE ON videos BEGIN
            INSERT INTO videos_fts(videos_fts, rowid, filename, path)
            VALUES ('delete', old.rowid, old.filename, old.path);
        END
    """)

    # Create FTS update trigger
    op.execute("""
        CREATE TRIGGER videos_fts_update AFTER UPDATE ON videos BEGIN
            INSERT INTO videos_fts(videos_fts, rowid, filename, path)
            VALUES ('delete', old.rowid, old.filename, old.path);
            INSERT INTO videos_fts(rowid, filename, path)
            VALUES (new.rowid, new.filename, new.path);
        END
    """)


def downgrade() -> None:
    """Remove all tables, triggers, and indexes."""
    op.execute("DROP TRIGGER IF EXISTS videos_fts_update")
    op.execute("DROP TRIGGER IF EXISTS videos_fts_delete")
    op.execute("DROP TRIGGER IF EXISTS videos_fts_insert")
    op.execute("DROP TABLE IF EXISTS videos_fts")
    op.execute("DROP INDEX IF EXISTS idx_videos_path")
    op.execute("DROP TABLE IF EXISTS videos")
