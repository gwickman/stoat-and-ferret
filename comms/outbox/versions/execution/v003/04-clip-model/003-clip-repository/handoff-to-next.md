# Handoff: 003-clip-repository

## What Was Done

Created the async clip repository layer for persisting `Clip` entities to the database. The repository follows the same patterns established by `project_repository.py` and `async_repository.py`.

## Key Components

### AsyncClipRepository Protocol

Defines the interface for clip persistence with these methods:
- `add(clip: Clip) -> Clip` - Insert a new clip
- `get(id: str) -> Clip | None` - Retrieve by ID
- `list_by_project(project_id: str) -> list[Clip]` - Get clips ordered by timeline position
- `update(clip: Clip) -> Clip` - Update clip fields
- `delete(id: str) -> bool` - Remove a clip

### Implementations

1. **AsyncSQLiteClipRepository** - Uses aiosqlite for production
2. **AsyncInMemoryClipRepository** - Dict-based for testing

## Usage Example

```python
from stoat_ferret.db import AsyncSQLiteClipRepository, Clip
import aiosqlite

conn = await aiosqlite.connect("stoat_ferret.db")
repo = AsyncSQLiteClipRepository(conn)

# Create and add a clip
clip = Clip(
    id=Clip.new_id(),
    project_id="project-123",
    source_video_id="video-456",
    in_point=0,
    out_point=100,
    timeline_position=0,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)
await repo.add(clip)

# List clips in a project (ordered by timeline_position)
clips = await repo.list_by_project("project-123")
```

## Notes for Next Features

- Clips have foreign key constraints to both `projects` and `videos` tables
- The `list_by_project` method returns clips ordered by `timeline_position` (ascending)
- Update only modifies `in_point`, `out_point`, `timeline_position`, and `updated_at`
- The SQLite implementation raises `ValueError` on foreign key violations
