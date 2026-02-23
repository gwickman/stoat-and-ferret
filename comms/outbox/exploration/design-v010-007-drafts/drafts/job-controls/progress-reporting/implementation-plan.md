# Implementation Plan: progress-reporting

## Overview

Add a `progress` field to `_AsyncJobEntry`, a `set_progress()` method to `AsyncioJobQueue`, and wire a progress callback through `make_scan_handler()` and `scan_directory()` to populate the progress field after each file. Update the jobs router to include progress in the API response.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/jobs/queue.py` | Modify | Add progress field to _AsyncJobEntry, set_progress() to AsyncioJobQueue, update AsyncJobQueue Protocol, add no-op to InMemoryJobQueue |
| `src/stoat_ferret/api/services/scan.py` | Modify | Add progress_callback keyword-only parameter to scan_directory(), call after each file; update make_scan_handler() to pass callback |
| `src/stoat_ferret/api/routers/jobs.py` | Modify | Wire progress into JobStatusResponse construction |
| `tests/test_jobs/test_asyncio_queue.py` | Modify | Add tests for set_progress() method |
| `tests/test_api/test_videos.py` | Modify | Add tests for progress callback in scan handler (scan-related tests live here) |
| `tests/test_api/test_jobs.py` | Modify | Add test for progress field in GET /api/v1/jobs/{id} response |
| `tests/test_doubles/test_inmemory_job_queue.py` | Modify | Add test for no-op set_progress() on InMemoryJobQueue |

## Test Files

`tests/test_jobs/test_asyncio_queue.py tests/test_api/test_videos.py tests/test_api/test_jobs.py tests/test_doubles/test_inmemory_job_queue.py`

## Implementation Stages

### Stage 1: Queue layer — progress field and set_progress()

1. In `src/stoat_ferret/jobs/queue.py`:
   - Add `progress: float | None = None` to `_AsyncJobEntry` dataclass
   - Add `set_progress(self, job_id: str, value: float) -> None` to `AsyncioJobQueue`:
     ```python
     def set_progress(self, job_id: str, value: float) -> None:
         entry = self._jobs.get(job_id)
         if entry is not None:
             entry.progress = value
     ```
   - Add `set_progress` to `AsyncJobQueue` Protocol
   - Add no-op `set_progress` to `InMemoryJobQueue`:
     ```python
     def set_progress(self, job_id: str, value: float) -> None:
         pass
     ```
   - Update `get_status()` / `get_result()` to include progress in the returned data

**Verification:**
```bash
uv run ruff check src/stoat_ferret/jobs/queue.py
uv run mypy src/stoat_ferret/jobs/queue.py
uv run pytest tests/test_jobs/ tests/test_doubles/ -v
```

### Stage 2: Scan handler — progress callback

1. In `src/stoat_ferret/api/services/scan.py`:
   - Add keyword-only parameter: `async def scan_directory(..., *, progress_callback=None)`
   - After each file is processed, call: `if progress_callback: progress_callback(scanned / total_files)`
   - In `make_scan_handler()`, create a progress callback closure that calls `queue.set_progress(job_id, value)` and pass it to `scan_directory()`

**Verification:**
```bash
uv run ruff check src/stoat_ferret/api/services/scan.py
uv run pytest tests/test_api/test_videos.py -v
```

### Stage 3: API response — wire progress

1. In `src/stoat_ferret/api/routers/jobs.py`:
   - Add `progress=result.progress` (or equivalent) to the `JobStatusResponse` construction

**Verification:**
```bash
uv run pytest tests/test_api/test_jobs.py -v
```

### Stage 4: Full quality gates

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Test Infrastructure Updates

- `InMemoryJobQueue` gets `set_progress()` no-op — prevents test double drift
- Existing test fixtures using `InMemoryJobQueue` remain unaffected (no-op method)

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- scan_directory() parameter accumulation — KISS-acceptable with keyword-only args. See `006-critical-thinking/risk-assessment.md`
- InMemoryJobQueue drift — mitigated by Protocol update and no-op stub. See `006-critical-thinking/investigation-log.md` Investigation 3

## Commit Message

```
feat: add progress reporting to job queue and scan handler (BL-073)
```
