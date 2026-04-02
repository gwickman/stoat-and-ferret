# Render Repository

**Source:** `src/stoat_ferret/render/render_repository.py`
**Component:** Render Engine

## Purpose

Defines the persistence protocol for render jobs and provides two implementations: an async SQLite repository for production and an in-memory repository for testing. Both enforce state machine transitions via `validate_render_transition()`.

## Public Interface

### Protocols

- `AsyncRenderRepository`: Protocol defining render job persistence
  - `create(job: RenderJob) -> RenderJob`: Persist a new render job
  - `get(job_id: str) -> RenderJob | None`: Retrieve job by ID
  - `get_by_project(project_id: str) -> list[RenderJob]`: List jobs for a project
  - `list_by_status(status: RenderStatus) -> list[RenderJob]`: List jobs by status, ordered by created_at
  - `update_status(job_id: str, status: RenderStatus, error_message: str | None = None) -> None`: Update job status with transition validation
  - `update_progress(job_id: str, progress: float) -> None`: Update job progress (0.0-1.0)
  - `list_jobs(status: RenderStatus | None = None, limit: int = 20, offset: int = 0) -> tuple[list[RenderJob], int]`: Paginated job listing with optional status filter; returns (jobs, total_count)
  - `delete(job_id: str) -> bool`: Delete job by ID, return True if found

### Classes

- `AsyncSQLiteRenderRepository`: Production SQLite implementation
  - `__init__(connection: aiosqlite.Connection) -> None`: Initialize with async SQLite connection
  - Row factory: `aiosqlite.Row` for dict-like row access

- `InMemoryRenderRepository`: Test double using in-memory dict
  - Uses `deepcopy` isolation to prevent mutation of stored objects

## Dependencies

### Internal Dependencies

- `stoat_ferret.render.models.RenderJob, RenderStatus, OutputFormat, QualityPreset`: Domain model types
- `stoat_ferret.render.models.validate_render_transition`: State machine enforcement

### External Dependencies

- `aiosqlite`: Async SQLite access (production implementation)
- `copy.deepcopy`: Object isolation (test implementation)
- `typing.Protocol`: Structural subtyping for the repository interface

## Key Implementation Details

### State Machine Enforcement at Repository Level

`update_status()` in both implementations:
1. Fetches current job status
2. Calls `validate_render_transition(current_status, new_status)` — raises ValueError on invalid
3. Applies status-specific side effects:
   - FAILED -> QUEUED (retry): Resets progress to 0.0 and clears error_message
   - Any -> COMPLETED: Sets progress to 1.0 and completed_at timestamp

### SQLite Schema

The repository operates on the `render_jobs` table with columns matching `RenderJob` fields. Status and format/preset are stored as string enum values.

### In-Memory Isolation

`InMemoryRenderRepository` uses `deepcopy` on all reads and writes to prevent callers from mutating stored state, providing the same isolation semantics as the database implementation.

### Paginated Listing

`list_jobs()` returns a tuple of `(jobs, total_count)` to support pagination in the API. Supports optional status filtering.

## Relationships

- **Used by:** RenderQueue (enqueue, dequeue, recovery), RenderService (job lookups), API Gateway (render router CRUD endpoints)
- **Uses:** RenderJob model, validate_render_transition function
