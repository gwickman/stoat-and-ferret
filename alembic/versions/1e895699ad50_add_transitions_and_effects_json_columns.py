"""add_transitions_and_effects_json_columns

Revision ID: 1e895699ad50
Revises: 39896ab3d0b7
Create Date: 2026-02-19 18:53:24.675300

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1e895699ad50"
down_revision: Union[str, Sequence[str], None] = "39896ab3d0b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add transitions_json to projects and effects_json to clips.

    These nullable TEXT columns store JSON arrays for per-project transitions
    and per-clip effects. The repository code already references them, but
    the original CREATE TABLE migrations omitted them.
    """
    op.execute("ALTER TABLE projects ADD COLUMN transitions_json TEXT")
    op.execute("ALTER TABLE clips ADD COLUMN effects_json TEXT")


def downgrade() -> None:
    """Remove transitions_json and effects_json columns.

    SQLite does not support DROP COLUMN before 3.35.0, so we recreate
    each table without the column.
    """
    # Recreate projects without transitions_json
    op.execute("""
        CREATE TABLE projects_backup (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            output_width INTEGER NOT NULL DEFAULT 1920,
            output_height INTEGER NOT NULL DEFAULT 1080,
            output_fps INTEGER NOT NULL DEFAULT 30,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    op.execute("""
        INSERT INTO projects_backup
        SELECT id, name, output_width, output_height, output_fps,
               created_at, updated_at
        FROM projects
    """)
    op.execute("DROP TABLE projects")
    op.execute("ALTER TABLE projects_backup RENAME TO projects")

    # Recreate clips without effects_json
    op.execute("""
        CREATE TABLE clips_backup (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            source_video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE RESTRICT,
            in_point INTEGER NOT NULL,
            out_point INTEGER NOT NULL,
            timeline_position INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    op.execute("""
        INSERT INTO clips_backup
        SELECT id, project_id, source_video_id, in_point, out_point,
               timeline_position, created_at, updated_at
        FROM clips
    """)
    op.execute("DROP TABLE clips")
    op.execute("ALTER TABLE clips_backup RENAME TO clips")
    op.execute("CREATE INDEX idx_clips_project ON clips(project_id)")
    op.execute(
        "CREATE INDEX idx_clips_timeline ON clips(project_id, timeline_position)"
    )
