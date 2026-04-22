"""add_feature_flag_log

Revision ID: e5b2c4f1a9d8
Revises: d7a1b2c3e4f5
Create Date: 2026-04-22 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b2c4f1a9d8"
down_revision: Union[str, Sequence[str], None] = "d7a1b2c3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create feature_flag_log table for BL-268 feature flag audit log.

    Append-only audit table that records each feature flag's name,
    value, and the timestamp it was observed at application startup.
    """
    op.execute("""
        CREATE TABLE IF NOT EXISTS feature_flag_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flag_name TEXT NOT NULL,
            flag_value INTEGER NOT NULL,
            logged_at TEXT NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feature_flag_log_logged_at "
        "ON feature_flag_log(logged_at)"
    )


def downgrade() -> None:
    """Intentionally preserve feature_flag_log on downgrade.

    feature_flag_log is an append-only audit record of deployment-time
    flag state. Dropping it on downgrade would erase the record of a
    configuration that may still be relevant for incident analysis;
    retention is treated the same way as migration_history (BL-266).
    """
    # no-op: see docstring
