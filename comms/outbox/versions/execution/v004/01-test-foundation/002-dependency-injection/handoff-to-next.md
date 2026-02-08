# Handoff: 002-dependency-injection -> next feature

## What Changed

`create_app()` now accepts optional `video_repository`, `project_repository`, and `clip_repository` parameters. When provided, the lifespan skips database initialization and dependency functions read from `app.state` instead of constructing SQLite repositories.

## Test Pattern

To create a test app with in-memory repos:

```python
from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

app = create_app(
    video_repository=AsyncInMemoryVideoRepository(),
    project_repository=AsyncInMemoryProjectRepository(),
    clip_repository=AsyncInMemoryClipRepository(),
)
```

No `dependency_overrides` needed. The shared conftest fixtures already use this pattern.

## Caveats

- The health check `_check_database()` returns `{"status": "ok", "latency_ms": 0.0}` when no DB is present (injection mode). This is appropriate for testing but means readiness checks in test mode don't validate real DB connectivity.
- `executor` and `job_queue` parameters were not added per YAGNI. Add them to `create_app()` when those dependencies need injection.
