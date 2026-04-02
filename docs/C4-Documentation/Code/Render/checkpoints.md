# Checkpoint Manager

**Source:** `src/stoat_ferret/render/checkpoints.py`
**Component:** Render Engine

## Purpose

Provides write-once per-segment checkpoints for crash recovery of render jobs. After each segment is successfully processed, a checkpoint is recorded in SQLite. On server restart, the checkpoint manager identifies interrupted jobs and their resume points.

## Public Interface

### Classes

- `CheckpointManager`: Manages render job checkpoints for crash recovery
  - `__init__(connection: aiosqlite.Connection) -> None`: Initialize with async SQLite connection
  - `write_checkpoint(job_id: str, segment_index: int) -> None`: Record completed segment after successful processing
  - `get_completed_segments(job_id: str) -> list[int]`: Return sorted list of completed segment indexes for a job
  - `get_next_segment(job_id: str, total_segments: int) -> int | None`: Return next uncompleted segment index, or None if all done
  - `recover() -> list[tuple[str, int]]`: Scan for RUNNING jobs interrupted at server restart; return (job_id, next_segment_index) pairs where next_segment_index equals count of completed checkpoints
  - `cleanup_stale(job_ids: list[str]) -> int`: Delete checkpoints for given job IDs (used when jobs are cancelled/deleted); return count of deleted rows

## Dependencies

### Internal Dependencies

None — standalone checkpoint abstraction.

### External Dependencies

- `aiosqlite`: Async SQLite access for checkpoint persistence
- `structlog`: Structured logging

## Key Implementation Details

### Database Schema

Operates on the `render_checkpoints` table:
```sql
CREATE TABLE render_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    segment_index INTEGER NOT NULL,
    completed_at TEXT NOT NULL
)
```

### Write-Once Semantics

Checkpoints are only written after a segment is fully processed. This ensures that on recovery, only truly completed segments are counted, preventing data corruption from partial writes.

### Recovery Algorithm

`recover()`:
1. Queries `render_jobs` for all jobs with status RUNNING (interrupted by server restart)
2. For each, counts completed checkpoints to determine the resume point
3. Returns (job_id, next_segment_index) pairs for upstream handling

### Stale Cleanup

`cleanup_stale()` bulk-deletes checkpoints for cancelled or deleted jobs, preventing unbounded growth of the checkpoints table.

## Relationships

- **Used by:** RenderService (write_checkpoint during execution, recover on startup, cleanup_stale on job deletion)
- **Uses:** SQLite database (render_checkpoints table)
