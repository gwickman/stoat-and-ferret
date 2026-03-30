# Batch Repository

**Source:** `src/stoat_ferret/db/batch_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for batch job persistence. Defines AsyncBatchRepository protocol and offers two implementations: AsyncSQLiteBatchRepository for production use and InMemoryBatchRepository for testing. Handles batch job CRUD operations with strict status transition validation for the render queue system.

## Public Interface

### Protocols

- `AsyncBatchRepository`
  - Abstract protocol defining asynchronous batch job repository operations
  - Methods:
    - `async create_batch_job(*, batch_id: str, job_id: str, project_id: str, output_path: str, quality: str) -> BatchJobRecord` — Create a new batch job record
    - `async get_by_batch_id(batch_id: str) -> list[BatchJobRecord]` — Get all jobs belonging to a batch, ordered by id
    - `async get_by_job_id(job_id: str) -> BatchJobRecord | None` — Get a single job by its unique job ID
    - `async update_status(job_id: str, status: str, *, error: str | None = None) -> None` — Update job status with transition validation
    - `async update_progress(job_id: str, progress: float) -> None` — Update render progress (0.0-1.0)

### Dataclasses

- `BatchJobRecord`
  - Represents a single job within a batch render operation
  - Properties:
    - `id: int | None` — Database row ID (None for unsaved records)
    - `batch_id: str` — UUID grouping jobs into a batch
    - `job_id: str` — Unique UUID for this individual job
    - `project_id: str` — The project to render
    - `output_path: str` — Output file path for rendered video
    - `quality: str` — Render quality preset
    - `status: str` — Job status (queued, running, completed, failed)
    - `progress: float` — Render progress 0.0-1.0
    - `error: str | None` — Error message when status is failed
    - `created_at: datetime` — When this job was created
    - `updated_at: datetime` — When this job was last modified

### Classes

- `AsyncSQLiteBatchRepository`
  - Async SQLite implementation of AsyncBatchRepository protocol
  - `__init__(conn: aiosqlite.Connection) -> None`
    - Initialize with async SQLite connection
    - Sets row_factory to aiosqlite.Row for named column access
  - `async create_batch_job(*, batch_id: str, job_id: str, project_id: str, output_path: str, quality: str) -> BatchJobRecord` — INSERT into batch_jobs table
    - Creates job with initial status "queued", progress 0.0, no error
    - Returns new BatchJobRecord with assigned database id and timestamps
  - `async get_by_batch_id(batch_id: str) -> list[BatchJobRecord]` — SELECT jobs by batch_id
    - Returns records ordered by id (ascending)
  - `async get_by_job_id(job_id: str) -> BatchJobRecord | None` — SELECT job by unique job_id
  - `async update_status(job_id: str, status: str, *, error: str | None = None) -> None` — UPDATE job status with transition validation
    - Validates status transition per allowed states
    - Raises ValueError if job not found or transition invalid
    - Updates updated_at to current UTC time
  - `async update_progress(job_id: str, progress: float) -> None` — UPDATE job progress
    - Raises ValueError if job not found
    - Updates updated_at to current UTC time
  - `_row_to_record(row: aiosqlite.Row) -> BatchJobRecord` — Convert database row to BatchJobRecord

- `InMemoryBatchRepository`
  - In-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains index: `_jobs` (job_id → BatchJobRecord)
  - Maintains counter: `_next_id` for generating row IDs
  - `__init__() -> None` — Initialize empty repository
  - `async create_batch_job(*, batch_id: str, job_id: str, project_id: str, output_path: str, quality: str) -> BatchJobRecord` — Store deepcopy in _jobs
    - Auto-increments _next_id for each new job
    - Returns deepcopy to prevent external mutations
  - `async get_by_batch_id(batch_id: str) -> list[BatchJobRecord]` — Return deepcopies matching batch_id sorted by id
  - `async get_by_job_id(job_id: str) -> BatchJobRecord | None` — Return deepcopy from _jobs
  - `async update_status(job_id: str, status: str, *, error: str | None = None) -> None` — Update _jobs entry with transition validation
    - Raises ValueError if job not found or transition invalid
  - `async update_progress(job_id: str, progress: float) -> None` — Update _jobs progress
    - Raises ValueError if job not found

### Helper Functions

- `_validate_status_transition(current: str, new: str) -> None`
  - Validates that a status transition is allowed
  - Enforces state machine: queued → running → (completed | failed)
  - Raises ValueError with detailed message if transition invalid

## Dependencies

- **stoat_ferret.db.models**: (future) BatchJobStatus enum (if added)
- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection and aiosqlite.Row
- **datetime**: For timestamp fields (created_at, updated_at)
- **copy**: For deepcopy isolation in in-memory repository
- **structlog**: For logging batch repository operations

## Key Implementation Details

### Status Transitions

Valid transitions are strictly enforced:
```
queued -> running -> completed
queued -> running -> failed
```

Any attempt to transition outside this state machine raises ValueError with details of allowed next states.

### Timestamps

- All timestamps are stored as ISO format strings in SQLite and converted back to datetime objects on retrieval
- `created_at` and `updated_at` are set to UTC now (datetime.now(timezone.utc))
- `updated_at` is refreshed whenever job status or progress is updated

### Batch Grouping

- Multiple jobs can belong to a single batch via `batch_id`
- `get_by_batch_id()` returns all jobs for a batch in id order (useful for monitoring overall batch progress)
- Each job has unique `job_id` for individual job tracking

### Progress Tracking

- Progress is a float 0.0-1.0 representing render completion percentage
- Updated independently from status transitions (can progress while in "running" state)
- Used by the batch render system to provide UI progress feedback

### Deepcopy Isolation

- InMemoryBatchRepository stores and returns deepcopies to prevent test code from accidentally mutating internal state
- Each returned record is independent and changes won't affect future queries

### Row ID Management

- SQLite uses auto-incrementing INTEGER PRIMARY KEY for database row IDs
- InMemoryBatchRepository mimics this with _next_id counter
- Row ID is returned in BatchJobRecord.id for reference but jobs are primarily accessed by job_id

## Relationships

- **Used by:**
  - Batch render service for queuing and monitoring render jobs
  - API endpoints for batch status queries and progress polling
  - Background job processor for job state management

- **Uses:**
  - aiosqlite — async database operations
  - datetime — timestamp management

- **Associated entities:**
  - Projects (via project_id FK) — each job renders a specific project
  - Videos (indirectly through projects) — source content for rendering
