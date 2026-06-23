# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Add delivery_profiles table for DeliveryProfile persistence (BL-425).

Revision ID: g1h2i3j4k5l6
Revises: f2a3b4c5d6e7
Create Date: 2026-06-08 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "g1h2i3j4k5l6"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create delivery_profiles table and name index (idempotent)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS delivery_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                output_formats TEXT NOT NULL,
                loudness_target_lufs REAL NOT NULL,
                true_peak_ceiling_dbtp REAL NOT NULL,
                metadata_template TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
    )
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_delivery_profiles_name ON delivery_profiles(name)")
    )


def downgrade() -> None:
    """Intentionally preserve delivery_profiles on downgrade.

    DeliveryProfile is append-only configuration data — dropping the table
    on rollback would destroy operator-configured profiles. Downgrade is a
    no-op per the Migration Safeguard Rule.
    """
