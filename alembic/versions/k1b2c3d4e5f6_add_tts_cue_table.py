# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""add_tts_cue_table

Revision ID: k1b2c3d4e5f6
Revises: j1a2b3c4d5e6
Create Date: 2026-06-29 00:00:00.000000

Add tts_cue table for TTS narration cue/track data model (BL-516).
Downgrade is a no-op (append-only table; dropping would erase synthesised cue data).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "j1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tts_cue table (idempotent via IF NOT EXISTS)."""
    op.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS tts_cue (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            track_id TEXT NOT NULL,
            start_s REAL NOT NULL,
            text TEXT NOT NULL,
            voice TEXT NOT NULL,
            backend TEXT NOT NULL DEFAULT 'piper_local',
            gain_db REAL NOT NULL DEFAULT 0.0,
            pan REAL NOT NULL DEFAULT 0.0,
            cache_key TEXT NOT NULL,
            generated_asset_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        )
    """)
    )


def downgrade() -> None:
    """No-op downgrade for tts_cue (append-only table; dropping would erase cue data)."""
    pass
