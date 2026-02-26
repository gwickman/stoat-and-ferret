# Backend Scan Flow

Full trace of the directory scan from API request to database write.

## 1. Endpoint — `POST /api/v1/videos/scan`

**File:** `src/stoat_ferret/api/routers/videos.py:167-207`

```python
@router.post("/scan", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def scan_videos(scan_request: ScanRequest, request: Request) -> JobSubmitResponse:
```

1. Validates `scan_request.path` is a directory (400 if not)
2. Validates path against `allowed_scan_roots` (403 if blocked)
3. Calls `job_queue.submit("scan", payload)` — returns `job_id`
4. Returns `{"job_id": "..."}` with 202 Accepted

## 2. Job Queue — `AsyncioJobQueue`

**File:** `src/stoat_ferret/jobs/queue.py:316-507`

- `submit()` (line 377) creates `_AsyncJobEntry`, adds to `asyncio.Queue`, returns `job_id`
- `process_jobs()` (line 433) is a background worker coroutine that:
  1. Pulls `job_id` from queue (line 443)
  2. Sets status to `RUNNING` (line 461)
  3. Injects `_job_id` and `_cancel_event` into payload (lines 465-469)
  4. Wraps handler call in `asyncio.wait_for(timeout=300s)` (line 472)
  5. On success: sets status to `COMPLETE`, stores result (line 481)
  6. On cancel: sets status to `CANCELLED` (line 477)
  7. On timeout: sets status to `TIMEOUT` (line 485)
  8. On error: sets status to `FAILED` (line 494)

## 3. Status Polling — `GET /api/v1/jobs/{job_id}`

**File:** `src/stoat_ferret/api/routers/jobs.py:13-45`

Returns `JobStatusResponse` with:
- `status`: serialized from `JobStatus` enum `.value` — one of `"pending"`, `"running"`, `"complete"`, `"failed"`, `"timeout"`, `"cancelled"`
- `progress`: `float | None` (0.0-1.0)
- `result`: scan results when complete
- `error`: error message on failure/timeout

## 4. Scan Handler — `make_scan_handler()`

**File:** `src/stoat_ferret/api/services/scan.py:57-118`

Creates a closure with `repository`, `thumbnail_service`, `ws_manager`, and `queue`. The inner `handler()`:
1. Extracts `_job_id` and `_cancel_event` from payload
2. Creates `progress_callback` that calls `queue.set_progress(job_id, value)`
3. Broadcasts `SCAN_STARTED` WebSocket event
4. Calls `scan_directory()` with all parameters
5. Broadcasts `SCAN_COMPLETED` WebSocket event
6. Returns `result.model_dump()` — serialized `ScanResponse`

## 5. `scan_directory()` — File Processing Loop

**File:** `src/stoat_ferret/api/services/scan.py:121-226`

For each video file found:
1. Check `cancel_event` — break if set
2. `await repository.get_by_path()` — check if video already exists
3. `await ffprobe_video()` — extract metadata via async subprocess
4. `thumbnail_service.generate()` — sync thumbnail generation (returns None on failure)
5. Build `Video` object with all metadata
6. `await repository.add()` or `await repository.update()`
7. Errors caught per-file and appended to `errors` list
8. `progress_callback(processed / total_files)` — updates job progress

Returns `ScanResponse(scanned, new, updated, skipped, errors)`.

## 6. Database Writes

**File:** `src/stoat_ferret/db/async_repository.py`

- `add()` (line 138): `INSERT INTO videos` with commit
- `update()` (line 217): `UPDATE videos SET ... WHERE id = ?` with commit
- Each operation commits individually (no batch transaction)

## 7. Progress Communication

Two channels:
1. **Polling**: `queue.set_progress()` → stored in `_AsyncJobEntry.progress` → returned by `get_result()` → serialized in `JobStatusResponse.progress`
2. **WebSocket**: `SCAN_STARTED` and `SCAN_COMPLETED` events broadcast to all connected clients

The frontend currently uses polling only (1-second interval).

## 8. Error Handling

- Per-file exceptions are caught and added to `errors` list — scan continues
- Thumbnail failures logged as warnings, scan continues with `thumbnail_path=None`
- FFprobe timeout (30s per file) raises `FFprobeError` → caught as per-file error
- Job-level timeout (300s total) sets `TIMEOUT` status
- All async operations are properly awaited (fixed in commit `32859cc`)
