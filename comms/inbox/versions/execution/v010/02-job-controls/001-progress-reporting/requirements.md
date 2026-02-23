# Requirements: progress-reporting

## Goal

Add progress tracking to the job queue and wire through the scan handler to the frontend so users see real-time scan progress.

## Background

Backlog Item: BL-073

The job queue (`AsyncioJobQueue`), job result model, and job status response have no progress field populated. The scan handler processes files in a loop but never reports intermediate progress. The frontend polls job status but always receives `null` for progress, so the progress bar is permanently stuck at 0%. The `JobStatusResponse` schema already has a `progress: float | None = None` field — only backend population is missing.

## Functional Requirements

**FR-001: Job entry progress field**
- Add `progress: float | None = None` to `_AsyncJobEntry` dataclass
- Acceptance: _AsyncJobEntry initializes with progress = None

**FR-002: Queue set_progress method**
- Add `set_progress(job_id: str, value: float) -> None` method to `AsyncioJobQueue`
- Acceptance: set_progress(job_id, 0.5) updates entry's progress field and is retrievable

**FR-003: Protocol update**
- Update `AsyncJobQueue` Protocol (at queue.py) to include `set_progress()` method
- Add no-op `set_progress()` to `InMemoryJobQueue` for protocol compliance
- Acceptance: InMemoryJobQueue passes protocol compliance check

**FR-004: Scan handler progress callback**
- Pass a progress callback into `scan_directory()` via the `make_scan_handler()` factory closure
- Use keyword-only parameter: `scan_directory(..., *, progress_callback=None)`
- Call `set_progress(job_id, scanned / total_files)` after each file
- Follow guard pattern: `if progress_callback:` before calling (consistent with ws_manager guard pattern)
- Acceptance: scan handler calls progress callback after each file with scanned/total_files

**FR-005: API response wiring**
- Wire `progress` into `JobStatusResponse` in the jobs router (add `progress=result.progress`)
- Acceptance: GET /api/v1/jobs/{id} response includes populated progress field during active jobs

## Non-Functional Requirements

**NFR-001: Progress accuracy**
- Progress value must be 0.0-1.0 float (scanned_count / total_files)
- Progress is None for queued jobs, 0.0-1.0 for running jobs, preserved for completed jobs

**NFR-002: No new DI surface**
- No new `create_app()` kwargs — progress is internal to the job queue

## Handler Pattern

Not applicable for v010 — no new handlers introduced.

## Out of Scope

- WebSocket push for progress updates — frontend already polls every 1 second, which is adequate
- Per-file progress within a single ffprobe call — progress is per-file-completed
- Progress persistence across server restarts — job state is ephemeral

## Test Requirements

- Unit: _AsyncJobEntry initializes with progress = None
- Unit: AsyncioJobQueue.set_progress() updates entry progress
- Unit: set_progress() with invalid job_id is a no-op or raises appropriate error
- Unit: scan handler calls progress callback after each file
- Unit: progress callback guard pattern — no error if callback is None
- API: GET /api/v1/jobs/{id} includes populated progress during active job
- API: progress is None for queued, 0.0-1.0 for running, preserved for completed
- Contract: JobStatusResponse with progress field round-trips correctly
- System: end-to-end scan of multi-file directory shows progress incrementing 0.0 to 1.0

## Reference

See `comms/outbox/versions/design/v010/004-research/` for supporting evidence.