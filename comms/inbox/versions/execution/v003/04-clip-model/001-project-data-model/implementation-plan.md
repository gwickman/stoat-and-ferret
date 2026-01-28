# Implementation Plan: Project Data Model

## Step 1: Add Project Model
Update `src/stoat_ferret/db/models.py`:

```python
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Project:
    """Video editing project."""
    
    id: str
    name: str
    output_width: int
    output_height: int
    output_fps: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new_id(cls) -> str:
        return str(uuid.uuid4())
```

## Step 2: Create Migration
```bash
uv run alembic revision -m "add_projects_table"
```

Edit migration:
```python
def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("output_width", sa.Integer(), nullable=False, server_default="1920"),
        sa.Column("output_height", sa.Integer(), nullable=False, server_default="1080"),
        sa.Column("output_fps", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("projects")
```

## Step 3: Create Repository
Create `src/stoat_ferret/db/project_repository.py` with AsyncProjectRepository protocol, AsyncSQLiteProjectRepository, and AsyncInMemoryProjectRepository implementations.

## Verification
- Migration applies cleanly
- Repository CRUD works
- `uv run pytest -m contract` passes