"""add_project_markers_table

Revision ID: ad17d3f76340
Revises: f1a2b3c4d5e6
Create Date: 2026-06-07 14:15:19.374775

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ad17d3f76340"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create project_markers table with FK CASCADE from projects."""
    op.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS project_markers (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            start_time REAL NOT NULL,
            end_time REAL,
            name TEXT,
            region_type TEXT NOT NULL DEFAULT 'point',
            created_at TEXT NOT NULL
        )
    """)
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_project_markers_project_id "
            "ON project_markers(project_id)"
        )
    )


def downgrade() -> None:
    pass  # no-op: markers are operational data; cascade delete handles cleanup
