"""add_thumbnail_strips

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-26 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create thumbnail_strips table for sprite sheet metadata."""
    op.execute("""
        CREATE TABLE thumbnail_strips (
            id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'pending',
            file_path TEXT,
            frame_count INTEGER NOT NULL DEFAULT 0,
            frame_width INTEGER NOT NULL DEFAULT 160,
            frame_height INTEGER NOT NULL DEFAULT 90,
            interval_seconds REAL NOT NULL DEFAULT 5.0,
            columns INTEGER NOT NULL DEFAULT 10,
            rows INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX idx_thumbnail_strips_video ON thumbnail_strips(video_id)"
    )


def downgrade() -> None:
    """Remove thumbnail_strips table."""
    op.execute("DROP INDEX IF EXISTS idx_thumbnail_strips_video")
    op.execute("DROP TABLE IF EXISTS thumbnail_strips")
