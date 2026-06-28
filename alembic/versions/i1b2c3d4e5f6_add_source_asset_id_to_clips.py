# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""add_source_asset_id_to_clips

Revision ID: i1b2c3d4e5f6
Revises: h1a2b3c4d5e6
Create Date: 2026-06-28 12:00:00.000000

Add source_asset_id column to clips table for image clip support (BL-511).
Uses raw SQL to preserve all existing FK constraints (ON DELETE RESTRICT on
source_video_id, ON DELETE CASCADE on project_id).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "h1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add source_asset_id column via raw SQL to preserve FK constraints.

    Recreates clips table with all existing columns plus source_asset_id.
    Handles optional columns that may not exist in older migration states.
    """
    conn = op.get_bind()
    existing_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(clips)")).fetchall()}

    # Columns that may or may not exist depending on migration state
    optional_cols = ["effects_json", "track_id", "timeline_start", "timeline_end", "generator_params"]
    base_cols = [
        "id",
        "project_id",
        "source_video_id",
        "in_point",
        "out_point",
        "timeline_position",
        "created_at",
        "updated_at",
        "clip_type",
    ]
    select_parts = base_cols[:]
    for col in optional_cols:
        select_parts.append(col if col in existing_cols else f"NULL AS {col}")
    # source_asset_id is always NULL for existing rows
    select_parts.append("NULL AS source_asset_id")

    insert_cols = base_cols + optional_cols + ["source_asset_id"]

    # Disable FK enforcement during table swap
    op.execute(sa.text("PRAGMA foreign_keys = OFF"))
    op.execute(
        sa.text("""
        CREATE TABLE clips_new (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            source_video_id TEXT,
            in_point INTEGER NOT NULL,
            out_point INTEGER NOT NULL,
            timeline_position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            clip_type VARCHAR NOT NULL DEFAULT 'file',
            effects_json TEXT,
            track_id TEXT,
            timeline_start REAL,
            timeline_end REAL,
            generator_params TEXT,
            source_asset_id TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (source_video_id) REFERENCES videos (id) ON DELETE RESTRICT,
            FOREIGN KEY (source_asset_id) REFERENCES assets (id) ON DELETE RESTRICT
        )
    """)
    )
    op.execute(
        sa.text(
            f"INSERT INTO clips_new ({', '.join(insert_cols)}) "
            f"SELECT {', '.join(select_parts)} FROM clips"
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_clips_timeline"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_clips_project"))
    op.execute(sa.text("DROP TABLE clips"))
    op.execute(sa.text("ALTER TABLE clips_new RENAME TO clips"))
    op.execute(sa.text("CREATE INDEX idx_clips_project ON clips(project_id)"))
    op.execute(sa.text("CREATE INDEX idx_clips_timeline ON clips(project_id, timeline_position)"))
    op.execute(sa.text("PRAGMA foreign_keys = ON"))


def downgrade() -> None:
    """Remove source_asset_id column via raw SQL (reverse the upgrade)."""
    conn = op.get_bind()
    existing_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(clips)")).fetchall()}

    optional_cols = ["effects_json", "track_id", "timeline_start", "timeline_end", "generator_params"]
    base_cols = [
        "id",
        "project_id",
        "source_video_id",
        "in_point",
        "out_point",
        "timeline_position",
        "created_at",
        "updated_at",
        "clip_type",
    ]
    select_parts = base_cols[:]
    for col in optional_cols:
        select_parts.append(col if col in existing_cols else f"NULL AS {col}")

    insert_cols = base_cols + optional_cols

    op.execute(sa.text("PRAGMA foreign_keys = OFF"))
    op.execute(
        sa.text("""
        CREATE TABLE clips_old (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            source_video_id TEXT,
            in_point INTEGER NOT NULL,
            out_point INTEGER NOT NULL,
            timeline_position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            clip_type VARCHAR NOT NULL DEFAULT 'file',
            effects_json TEXT,
            track_id TEXT,
            timeline_start REAL,
            timeline_end REAL,
            generator_params TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (source_video_id) REFERENCES videos (id) ON DELETE RESTRICT
        )
    """)
    )
    op.execute(
        sa.text(
            f"INSERT INTO clips_old ({', '.join(insert_cols)}) "
            f"SELECT {', '.join(select_parts)} FROM clips"
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_clips_timeline"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_clips_project"))
    op.execute(sa.text("DROP TABLE clips"))
    op.execute(sa.text("ALTER TABLE clips_old RENAME TO clips"))
    op.execute(sa.text("CREATE INDEX idx_clips_project ON clips(project_id)"))
    op.execute(sa.text("CREATE INDEX idx_clips_timeline ON clips(project_id, timeline_position)"))
    op.execute(sa.text("PRAGMA foreign_keys = ON"))
