# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Add qc_reports table for QCService persistence (BL-424).

Revision ID: f2a3b4c5d6e7
Revises: e5b2c4f1a9d8
Create Date: 2026-06-08 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f2a3b4c5d6e7"
down_revision = "a3f8b1c2d9e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create qc_reports table and job_id index (idempotent)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS qc_reports (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                artifact_path TEXT NOT NULL,
                delivery_profile_id TEXT,
                overall_verdict TEXT NOT NULL,
                checks TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_qc_reports_job_id ON qc_reports(job_id)"))


def downgrade() -> None:
    """Intentionally preserve qc_reports on downgrade.

    QCReport is append-only — dropping the table on rollback would destroy
    audit data. Downgrade is a no-op per the Migration Safeguard Rule.
    """
