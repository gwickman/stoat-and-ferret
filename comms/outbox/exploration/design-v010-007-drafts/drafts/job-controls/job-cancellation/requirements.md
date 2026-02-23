# Requirements: job-cancellation

## Goal

Add cooperative cancellation with a cancel endpoint and partial results so users can stop long-running scans.

## Background

Backlog Item: BL-074

The `AsyncioJobQueue` has no `cancel()` method, no cancellation flag, and no cancel API endpoint. The scan handler's file processing loop has no cancellation checkpoint. The frontend cancel button exists in `ScanModal.tsx` but has nothing to call — once a scan starts, the only way to stop it is to restart the server.

## Functional Requirements

**FR-001: Cancel event on job entry**
- Add `cancel_event: asyncio.Event = field(default_factory=asyncio.Event)` to `_AsyncJobEntry`
- Acceptance: _AsyncJobEntry initializes with unset cancel_event

**FR-002: Queue cancel method**
- Add `cancel(job_id: str) -> None` method to `AsyncioJobQueue` that sets the cancel event
- Acceptance: cancel(job_id) sets the cancel event; cancel() with invalid job_id returns appropriate error

**FR-003: Protocol update**
- Update `AsyncJobQueue` Protocol to include `cancel()` method
- Add no-op `cancel()` to `InMemoryJobQueue` for protocol compliance
- Acceptance: InMemoryJobQueue passes protocol compliance check

**FR-004: CANCELLED job status**
- Add `CANCELLED` to `JobStatus` enum
- Cancelled jobs report status `CANCELLED` with partial results (files scanned before cancellation are retained)
- Acceptance: JobStatus.CANCELLED enum value exists and serializes correctly

**FR-005: Scan handler cancellation**
- Pass cancel event into `scan_directory()` via the handler factory
- Use keyword-only parameter: `scan_directory(..., *, progress_callback=None, cancel_event=None)`
- Check `cancel_event.is_set()` between files in the scan loop — break and return partial results when set
- Acceptance: scan handler breaks file loop when cancel_event is set; partial results retained

**FR-006: Cancel REST endpoint**
- Add `POST /api/v1/jobs/{id}/cancel` endpoint
- Return 200 with updated status on success
- Return 404 for non-existent job
- Return appropriate error for already-completed job
- Acceptance: endpoint returns correct status codes for each scenario

**FR-007: Frontend cancel button**
- Enable the cancel button in `ScanModal.tsx` during active scan
- Wire to call `POST /api/v1/jobs/{id}/cancel`
- Update UI to reflect cancelled state
- Acceptance: cancel button calls endpoint and UI updates to reflect cancellation

## Non-Functional Requirements

**NFR-001: Python 3.10 compatibility**
- `asyncio.Event` creation is safe in `_AsyncJobEntry` because it is only instantiated inside `async def submit()` where the event loop is running (verified)

**NFR-002: No new DI surface**
- No new `create_app()` kwargs — cancellation is internal to the job queue

## Handler Pattern

Not applicable for v010 — no new handlers introduced.

## Out of Scope

- Cancelling individual ffprobe subprocess calls mid-execution — cancellation is cooperative between files
- Undo/rollback of partial scan results — partial results are preserved as-is
- Cancellation of non-scan job types — only scan handler implements cancellation for v010

## Test Requirements

- Unit: _AsyncJobEntry initializes with unset cancel_event
- Unit: AsyncioJobQueue.cancel() sets the cancel event
- Unit: cancel() with invalid job_id returns appropriate error
- Unit: scan handler breaks file loop when cancel_event is set
- Unit: cancelled scan returns partial results
- Unit: cancelled job has status = CANCELLED
- Unit: JobStatus.CANCELLED serializes correctly
- API: POST /api/v1/jobs/{id}/cancel returns 200 with updated status
- API: POST /api/v1/jobs/{id}/cancel for non-existent job returns 404
- API: POST /api/v1/jobs/{id}/cancel for completed job returns appropriate error
- API: GET /api/v1/jobs/{id} shows status cancelled and partial result after cancellation
- Frontend: cancel button enabled during active scan
- Frontend: cancel button calls POST /api/v1/jobs/{id}/cancel
- Frontend: UI updates to reflect cancelled state
- System: start scan, cancel mid-way, verify partial results preserved and status cancelled

## Reference

See `comms/outbox/versions/design/v010/004-research/` for supporting evidence.
