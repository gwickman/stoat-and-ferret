"""add_project_audio_baseline

Revision ID: a3f8b1c2d9e4
Revises: ad17d3f76340
Create Date: 2026-06-07 15:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f8b1c2d9e4"
down_revision: Union[str, Sequence[str], None] = "ad17d3f76340"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add sample_rate and bit_depth columns to projects table (idempotent)."""
    bind = op.get_bind()
    result = bind.execute(sa.text("PRAGMA table_info(projects)"))
    cols = {row[1] for row in result}
    if "sample_rate" not in cols:
        op.execute(
            sa.text(
                "ALTER TABLE projects ADD COLUMN sample_rate INTEGER NOT NULL DEFAULT 48000"
            )
        )
    if "bit_depth" not in cols:
        op.execute(
            sa.text(
                "ALTER TABLE projects ADD COLUMN bit_depth INTEGER NOT NULL DEFAULT 24"
            )
        )


def downgrade() -> None:
    pass  # SQLite does not support DROP COLUMN in most versions
