# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""generator_clips

Revision ID: a8516edf859e
Revises: g1h2i3j4k5l6
Create Date: 2026-06-11 23:34:35.751846

Add clip_type + generator_params columns to clips table and make source_video_id nullable
to support generator/source clips that synthesize audio via FFmpeg source filters (BL-441).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8516edf859e"
down_revision: str | Sequence[str] | None = "g1h2i3j4k5l6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Recreates clips table via raw SQL so that ON DELETE CASCADE on project_id
    is preserved. SQLAlchemy's batch_alter_table reflects the existing table
    without preserving ON DELETE actions, which breaks project deletion when
    PRAGMA foreign_keys=ON.

    Handles optional columns (track_id, timeline_start, timeline_end) that
    schema.py adds outside the Alembic chain — present in production DBs but
    absent when migrating from a clean initial schema in tests.
    """
    conn = op.get_bind()
    existing_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(clips)")).fetchall()}

    # Columns that may or may not exist depending on whether schema.py ran first
    optional_cols = ["effects_json", "track_id", "timeline_start", "timeline_end"]
    base_cols = [
        "id",
        "project_id",
        "source_video_id",
        "in_point",
        "out_point",
        "timeline_position",
        "created_at",
        "updated_at",
    ]
    select_parts = base_cols[:]
    for col in optional_cols:
        select_parts.append(col if col in existing_cols else f"NULL AS {col}")
    select_parts += ["'file'", "NULL"]

    insert_cols = base_cols + optional_cols + ["clip_type", "generator_params"]

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
            effects_json TEXT,
            track_id TEXT,
            timeline_start REAL,
            timeline_end REAL,
            clip_type VARCHAR NOT NULL DEFAULT 'file',
            generator_params TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (source_video_id) REFERENCES videos (id) ON DELETE RESTRICT
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


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    existing_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(clips)")).fetchall()}

    optional_cols = ["effects_json", "track_id", "timeline_start", "timeline_end"]
    base_cols = [
        "id",
        "project_id",
        "source_video_id",
        "in_point",
        "out_point",
        "timeline_position",
        "created_at",
        "updated_at",
    ]
    select_parts = base_cols[:]
    for col in optional_cols:
        select_parts.append(col if col in existing_cols else f"NULL AS {col}")

    # For downgrade: source_video_id was NOT NULL; COALESCE handles generator clips
    select_parts[2] = "COALESCE(source_video_id, '')"

    insert_cols = base_cols + optional_cols

    op.execute(
        sa.text("""
        CREATE TABLE clips_old (
            id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            source_video_id TEXT NOT NULL,
            in_point INTEGER NOT NULL,
            out_point INTEGER NOT NULL,
            timeline_position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            effects_json TEXT,
            track_id TEXT,
            timeline_start REAL,
            timeline_end REAL,
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
