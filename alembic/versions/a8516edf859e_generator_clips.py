"""generator_clips

Revision ID: a8516edf859e
Revises: g1h2i3j4k5l6
Create Date: 2026-06-11 23:34:35.751846

Add clip_type + generator_params columns to clips table and make source_video_id nullable
to support generator/source clips that synthesize audio via FFmpeg source filters (BL-441).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8516edf859e"
down_revision: Union[str, Sequence[str], None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("clips") as batch_op:
        batch_op.add_column(
            sa.Column("clip_type", sa.String(), nullable=False, server_default="file")
        )
        batch_op.add_column(sa.Column("generator_params", sa.Text(), nullable=True))
        batch_op.alter_column("source_video_id", nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("clips") as batch_op:
        batch_op.drop_column("generator_params")
        batch_op.drop_column("clip_type")
        batch_op.alter_column("source_video_id", nullable=False)
