# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""add_track_audio_columns_and_ducking_pair

Revision ID: j1a2b3c4d5e6
Revises: i1b2c3d4e5f6
Create Date: 2026-06-29 00:00:00.000000

Add kind, volume_envelope, weight columns to tracks table (BL-517).
Create ducking_pair table for voice-triggered music ducking configuration.
Downgrade for ducking_pair is a no-op (append-only table; dropping would erase
ducking configuration without recourse).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "i1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add audio columns to tracks and create ducking_pair table."""
    conn = op.get_bind()

    # Check whether the tracks table already exists.
    tables = {
        row[0]
        for row in conn.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }

    if "tracks" not in tables:
        op.execute(
            sa.text("""
            CREATE TABLE IF NOT EXISTS tracks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                track_type TEXT NOT NULL,
                label TEXT NOT NULL,
                z_index INTEGER NOT NULL DEFAULT 0,
                muted INTEGER NOT NULL DEFAULT 0,
                locked INTEGER NOT NULL DEFAULT 0,
                kind TEXT,
                volume_envelope TEXT,
                weight REAL DEFAULT 1.0
            )
        """)
        )
    else:
        # Table exists — add audio columns idempotently.
        existing_cols = {
            row[1] for row in conn.execute(sa.text("PRAGMA table_info(tracks)")).fetchall()
        }
        if "kind" not in existing_cols:
            op.execute(sa.text("ALTER TABLE tracks ADD COLUMN kind TEXT"))
        if "volume_envelope" not in existing_cols:
            op.execute(sa.text("ALTER TABLE tracks ADD COLUMN volume_envelope TEXT"))
        if "weight" not in existing_cols:
            op.execute(sa.text("ALTER TABLE tracks ADD COLUMN weight REAL DEFAULT 1.0"))

    # Create ducking_pair table (idempotent via IF NOT EXISTS).
    op.execute(
        sa.text("""
        CREATE TABLE IF NOT EXISTS ducking_pair (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            ducked_track_id TEXT NOT NULL,
            sidechain_track_id TEXT NOT NULL,
            threshold REAL DEFAULT 0.02,
            ratio REAL DEFAULT 8,
            attack_ms REAL DEFAULT 20,
            release_ms REAL DEFAULT 300,
            apply_pre_volume INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(ducked_track_id) REFERENCES tracks(id),
            FOREIGN KEY(sidechain_track_id) REFERENCES tracks(id),
            CONSTRAINT ck_ducking_pair_diff_tracks CHECK(ducked_track_id != sidechain_track_id)
        )
    """)
    )


def downgrade() -> None:
    """No-op downgrade for ducking_pair (append-only table; dropping would erase data).

    Track columns (kind, volume_envelope, weight) cannot be removed in SQLite
    without a full table rebuild; since they are nullable, leaving them is safe.
    """
    pass
