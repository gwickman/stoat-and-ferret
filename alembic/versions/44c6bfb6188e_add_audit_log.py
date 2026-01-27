"""add_audit_log

Revision ID: 44c6bfb6188e
Revises: c3687b3b7a6a
Create Date: 2026-01-27 22:44:09.377315

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44c6bfb6188e"
down_revision: Union[str, Sequence[str], None] = "c3687b3b7a6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_log table and index for tracking data modifications."""
    # Create audit_log table
    op.execute("""
        CREATE TABLE audit_log (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            operation TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            changes_json TEXT,
            context TEXT
        )
    """)

    # Create index for efficient entity history queries
    op.execute(
        "CREATE INDEX idx_audit_log_entity ON audit_log(entity_id, timestamp)"
    )


def downgrade() -> None:
    """Remove audit_log table and index."""
    op.execute("DROP INDEX IF EXISTS idx_audit_log_entity")
    op.execute("DROP TABLE IF EXISTS audit_log")
