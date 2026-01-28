"""add_projects_table

Revision ID: 4488866d89cc
Revises: 44c6bfb6188e
Create Date: 2026-01-28 21:43:19.450636

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4488866d89cc"
down_revision: Union[str, Sequence[str], None] = "44c6bfb6188e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create projects table for organizing video clips."""
    op.execute("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            output_width INTEGER NOT NULL DEFAULT 1920,
            output_height INTEGER NOT NULL DEFAULT 1080,
            output_fps INTEGER NOT NULL DEFAULT 30,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)


def downgrade() -> None:
    """Remove projects table."""
    op.execute("DROP TABLE IF EXISTS projects")
