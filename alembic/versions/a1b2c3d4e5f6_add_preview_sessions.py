"""add_preview_sessions

Revision ID: a1b2c3d4e5f6
Revises: 1e895699ad50
Create Date: 2026-03-25 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "1e895699ad50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create preview_sessions table for HLS preview session tracking."""
    op.execute("""
        CREATE TABLE preview_sessions (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'initializing',
            manifest_path TEXT,
            segment_count INTEGER NOT NULL DEFAULT 0,
            quality_level TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            error_message TEXT
        )
    """)
    op.execute(
        "CREATE INDEX idx_preview_sessions_project ON preview_sessions(project_id)"
    )
    op.execute(
        "CREATE INDEX idx_preview_sessions_expires ON preview_sessions(expires_at)"
    )


def downgrade() -> None:
    """Remove preview_sessions table."""
    op.execute("DROP INDEX IF EXISTS idx_preview_sessions_expires")
    op.execute("DROP INDEX IF EXISTS idx_preview_sessions_project")
    op.execute("DROP TABLE IF EXISTS preview_sessions")
