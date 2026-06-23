# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""add_auxiliary_stream_fields

Revision ID: f1a2b3c4d5e6
Revises: 8cba156be54c
Create Date: 2026-06-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "8cba156be54c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add subtitle_count, data_count, subtitle_streams columns to videos table.

    Idempotent: checks existing columns via PRAGMA table_info before each
    ALTER TABLE, so re-running after a no-op downgrade does not error.
    """
    bind = op.get_bind()
    existing = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(videos)")).fetchall()}
    if "subtitle_count" not in existing:
        op.execute("ALTER TABLE videos ADD COLUMN subtitle_count INTEGER NOT NULL DEFAULT 0")
    if "data_count" not in existing:
        op.execute("ALTER TABLE videos ADD COLUMN data_count INTEGER NOT NULL DEFAULT 0")
    if "subtitle_streams" not in existing:
        op.execute("ALTER TABLE videos ADD COLUMN subtitle_streams TEXT NOT NULL DEFAULT '[]'")


def downgrade() -> None:
    """No-op: SQLite does not support DROP COLUMN in older versions.

    The columns remain with their defaults; existing rows are unaffected.
    """
    pass
