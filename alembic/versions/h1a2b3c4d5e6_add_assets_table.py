# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Add assets table for user-asset library (BL-515).

Revision ID: h1a2b3c4d5e6
Revises: a8516edf859e
Create Date: 2026-06-28 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "h1a2b3c4d5e6"
down_revision = "a8516edf859e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create assets table and indexes (idempotent)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                content_hash TEXT NOT NULL UNIQUE,
                mime_type TEXT NOT NULL,
                kind TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                deleted_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
    )
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_assets_content_hash ON assets(content_hash)")
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind)"))


def downgrade() -> None:
    """Intentionally preserve assets on downgrade.

    The assets table is append-only operational data. Dropping it on rollback
    would destroy user-uploaded files' database records. Downgrade is a no-op
    per the Migration Safeguard Rule.
    """
