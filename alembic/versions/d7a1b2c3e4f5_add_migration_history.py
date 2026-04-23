"""add_migration_history

Revision ID: d7a1b2c3e4f5
Revises: b2c3d4e5f6a7
Create Date: 2026-04-22 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7a1b2c3e4f5"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create migration_history table for BL-266 migration safety audit log.

    Uses IF NOT EXISTS because MigrationService self-heals the same table
    (it's infrastructure for the migration wrapper itself, not app schema)
    so the table may already exist if the service ran before this revision
    was applied.
    """
    op.execute("""
        CREATE TABLE IF NOT EXISTS migration_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_revision TEXT,
            to_revision TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            backup_path TEXT,
            rollback_revision TEXT,
            status TEXT NOT NULL DEFAULT 'applied'
                CHECK (status IN ('applied', 'rolled_back'))
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_migration_history_applied_at "
        "ON migration_history(applied_at)"
    )


def downgrade() -> None:
    """Intentionally preserve migration_history on downgrade.

    migration_history is an audit log for the MigrationService wrapper
    itself. Dropping it on downgrade would erase the record of the very
    downgrade that is about to occur — the audit must survive the
    operation it is auditing. MigrationService self-heals the table
    via CREATE TABLE IF NOT EXISTS, so a no-op downgrade is safe.
    """
    # no-op: see docstring
