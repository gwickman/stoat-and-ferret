"""add_clips_table

Revision ID: 39896ab3d0b7
Revises: 4488866d89cc
Create Date: 2026-01-28 21:52:12.424841

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "39896ab3d0b7"
down_revision: Union[str, Sequence[str], None] = "4488866d89cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create clips table for video clip segments."""
    op.execute("""
        CREATE TABLE clips (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            source_video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE RESTRICT,
            in_point INTEGER NOT NULL,
            out_point INTEGER NOT NULL,
            timeline_position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_clips_project ON clips(project_id)")
    op.execute(
        "CREATE INDEX idx_clips_timeline ON clips(project_id, timeline_position)"
    )


def downgrade() -> None:
    """Remove clips table."""
    op.execute("DROP INDEX IF EXISTS idx_clips_timeline")
    op.execute("DROP INDEX IF EXISTS idx_clips_project")
    op.execute("DROP TABLE IF EXISTS clips")
