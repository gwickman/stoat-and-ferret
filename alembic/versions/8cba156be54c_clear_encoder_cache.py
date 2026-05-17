"""clear_encoder_cache

Revision ID: 8cba156be54c
Revises: e5b2c4f1a9d8
Create Date: 2026-05-17 14:31:01.072375

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8cba156be54c'
down_revision: Union[str, Sequence[str], None] = 'e5b2c4f1a9d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Clear poisoned encoder cache rows.

    encoder_type column previously stored Python repr (EncoderType.Software)
    instead of bare token (Software). DELETE forces re-detection on first request
    post-deploy, which repopulates with correct values.

    The encoder_cache table is created by create_tables_async (Phase 7), not by
    Alembic. On fresh installs this migration runs at Phase 5 before the table
    exists; the existence check makes it safe. Poisoned rows only exist on
    upgraded deployments where the bad serialization was already cached.
    """
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='encoder_cache'"
        )
    )
    if result.fetchone() is not None:
        op.execute("DELETE FROM encoder_cache")


def downgrade() -> None:
    """No-op: encoder_cache rows are ephemeral cache data.

    Downgrade cannot restore the deleted rows (they were stale anyway).
    The cache will repopulate automatically on next detection run.
    """
    pass
