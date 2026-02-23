# Implementation Plan: job-cancellation

## Overview

Add an `asyncio.Event` cancel field to `_AsyncJobEntry`, a `cancel()` method to `AsyncioJobQueue`, a `CANCELLED` status to `JobStatus`, and wire cooperative cancellation through the scan handler, REST API, and frontend cancel button.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/jobs/queue.py` | Modify | Add cancel_event to _AsyncJobEntry, cancel() to AsyncioJobQueue, CANCELLED to JobStatus, update Protocol, add no-op to InMemoryJobQueue |
| `src/stoat_ferret/api/services/scan.py` | Modify | Add cancel_event keyword-only parameter to scan_directory(), check between files, return partial results; update make_scan_handler() |
| `src/stoat_ferret/api/routers/jobs.py` | Modify | Add POST /api/v1/jobs/{id}/cancel endpoint |
| `gui/src/components/ScanModal.tsx` | Modify | Enable cancel button during active scan, wire to POST /api/v1/jobs/{id}/cancel |
| `docs/design/05-api-specification.md` | Modify | Document POST /api/v1/jobs/{id}/cancel endpoint |
| `tests/test_jobs/test_asyncio_queue.py` | Modify | Add tests for cancel() method and CANCELLED status |
| `tests/test_api/test_videos.py` | Modify | Add tests for scan cancellation with partial results (scan-related tests live here) |
| `tests/test_api/test_jobs.py` | Modify | Add tests for cancel endpoint |
| `tests/test_doubles/test_inmemory_job_queue.py` | Modify | Add test for no-op cancel() on InMemoryJobQueue |
| `gui/src/components/__tests__/ScanModal.test.tsx` | Modify | Add tests for cancel button behavior |

## Test Files

`tests/test_jobs/test_asyncio_queue.py tests/test_api/test_videos.py tests/test_api/test_jobs.py tests/test_doubles/test_inmemory_job_queue.py`

## Implementation Stages

### Stage 1: Queue layer — cancel event and CANCELLED status

1. In `src/stoat_ferret/jobs/queue.py`:
   - Add `CANCELLED = "cancelled"` to `JobStatus` enum
   - Add `cancel_event: asyncio.Event = field(default_factory=asyncio.Event)` to `_AsyncJobEntry`
   - Add `cancel(self, job_id: str) -> None` to `AsyncioJobQueue`:
     ```python
     def cancel(self, job_id: str) -> None:
         entry = self._jobs.get(job_id)
         if entry is not None:
             entry.cancel_event.set()
     ```
   - Update `AsyncJobQueue` Protocol with `cancel()` method
   - Add no-op `cancel()` to `InMemoryJobQueue`
   - In `process_jobs()`, after handler completes or is cancelled, check `cancel_event.is_set()` and set `status = JobStatus.CANCELLED`

**Verification:**
```bash
uv run ruff check src/stoat_ferret/jobs/queue.py
uv run mypy src/stoat_ferret/jobs/queue.py
uv run pytest tests/test_jobs/ tests/test_doubles/ -v
```

### Stage 2: Scan handler — cancellation check

1. In `src/stoat_ferret/api/services/scan.py`:
   - Add keyword-only parameter: `async def scan_directory(..., *, progress_callback=None, cancel_event=None)`
   - Before processing each file, check: `if cancel_event and cancel_event.is_set(): break`
   - Return partial results (files scanned so far) when cancelled
   - In `make_scan_handler()`, pass the cancel event from the job entry to `scan_directory()`

**Verification:**
```bash
uv run ruff check src/stoat_ferret/api/services/scan.py
uv run pytest tests/test_api/test_videos.py -v
```

### Stage 3: REST endpoint — cancel API

1. In `src/stoat_ferret/api/routers/jobs.py`:
   - Add `POST /api/v1/jobs/{job_id}/cancel` endpoint
   - Call `queue.cancel(job_id)` and return updated status
   - Return 404 for non-existent job
   - Return appropriate error for already-completed job

**Verification:**
```bash
uv run pytest tests/test_api/test_jobs.py -v
```

### Stage 4: Frontend — enable cancel button

1. In `gui/src/components/ScanModal.tsx`:
   - Enable the cancel button during active scan (remove disabled condition)
   - Wire `onClick` to call `POST /api/v1/jobs/{id}/cancel`
   - Update UI state to reflect cancelled status

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 5: Documentation

1. In `docs/design/05-api-specification.md`:
   - Add `POST /api/v1/jobs/{id}/cancel` endpoint documentation

### Stage 6: Full quality gates

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
cd gui && npx vitest run
```

## Test Infrastructure Updates

- `InMemoryJobQueue` gets `cancel()` no-op — prevents test double drift
- Need to test `CANCELLED` enum serialization in Pydantic models

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
```

## Risks

- asyncio.Event creation timing — verified safe in async def submit(). See `006-critical-thinking/risk-assessment.md`
- InMemoryJobQueue drift — mitigated by Protocol update and no-op stub. See `006-critical-thinking/investigation-log.md` Investigation 3

## Commit Message

```
feat: add cooperative job cancellation with cancel endpoint (BL-074)
```