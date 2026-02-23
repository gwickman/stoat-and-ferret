# Backend Issues

## Issue 1: Blocking subprocess.run() in Async Context (CRITICAL - Confirmed Bug)

**File:** `src/stoat_ferret/ffmpeg/probe.py:65-79`

```python
result = subprocess.run(
    [ffprobe_path, "-v", "quiet", "-print_format", "json",
     "-show_format", "-show_streams", path],
    capture_output=True,
    timeout=30,
    check=False,
)
```

`subprocess.run()` is synchronous and blocks the asyncio event loop. Since the scan handler calls this for every video file (`src/stoat_ferret/api/services/scan.py:154`), the event loop is blocked for the entire scan duration.

**Impact:** All HTTP request handling (including job status polling) is blocked while ffprobe runs. This is the primary reason the scan appears to hang.

**Fix:** Use `asyncio.create_subprocess_exec()` or run `subprocess.run()` in a thread via `asyncio.to_thread()` / `loop.run_in_executor()`:

```python
# Option A: asyncio subprocess
proc = await asyncio.create_subprocess_exec(
    ffprobe_path, "-v", "quiet", ...
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

# Option B: thread executor (minimal change)
result = await asyncio.to_thread(subprocess.run, [...], capture_output=True, timeout=30)
```

## Issue 2: Progress Never Reported (Confirmed Gap)

**File:** `src/stoat_ferret/api/services/scan.py:106-198`

The `scan_directory()` function processes files in a loop but never reports intermediate progress. The job queue has no mechanism to update progress during execution.

**File:** `src/stoat_ferret/jobs/queue.py:267-276`

`_AsyncJobEntry` has no `progress` field. `JobResult` has no `progress` field. The only status transitions are `PENDING -> RUNNING -> COMPLETE/FAILED/TIMEOUT`.

**File:** `src/stoat_ferret/api/routers/jobs.py:38-43`

The `get_job_status` endpoint builds `JobStatusResponse` from `JobResult` which never includes progress:

```python
return JobStatusResponse(
    job_id=result.job_id,
    status=result.status.value,
    result=result.result,
    error=result.error,
    # progress is never set -- defaults to None
)
```

**Impact:** The frontend `progress` state is always `null`, so the progress bar width is always `0%`.

**Fix:** Add a `progress` field to `_AsyncJobEntry`, expose a `set_progress(job_id, value)` method on the queue, and pass a progress callback into the scan handler so it can report `scanned / total_files`.

## Issue 3: No Cancellation Support (Confirmed Gap)

**File:** `src/stoat_ferret/jobs/queue.py:279-429`

The `AsyncioJobQueue` has no `cancel()` method. There is no API endpoint to cancel a job. The `process_jobs()` worker loop has no cancellation check between file iterations.

**File:** `src/stoat_ferret/api/routers/jobs.py`

Only one endpoint exists: `GET /{job_id}`. There is no `DELETE /{job_id}` or `POST /{job_id}/cancel`.

**Impact:** Once a scan starts, it cannot be stopped. The user must wait for completion or restart the server.

**Fix:** Add a `cancel(job_id)` method to the queue that sets a cancellation flag. Pass a `is_cancelled` callback into the scan handler. Check it between files in the scan loop. Add a `DELETE /api/v1/jobs/{job_id}` or `POST /api/v1/jobs/{job_id}/cancel` endpoint.

## Issue 4: asyncio.wait_for() Timeout Unreliable with Blocking Code (Confirmed Bug)

**File:** `src/stoat_ferret/jobs/queue.py:399-402`

```python
result = await asyncio.wait_for(
    handler(entry.job_type, entry.payload),
    timeout=self._timeout,
)
```

`asyncio.wait_for()` relies on the event loop to check the timeout. When the handler blocks the event loop with `subprocess.run()`, the timeout cannot fire until the next `await` point. A 300s timeout on a job that blocks for 30s per file will only trigger at the boundary of a blocking call, not precisely at 300s.

**Impact:** Jobs may run longer than the configured timeout before being terminated.

**Fix:** Resolving Issue 1 (using async subprocess) will also fix this, since `await` points will be available for timeout checking.

## Issue 5: Single Worker Queue Serialization (Design Limitation)

**File:** `src/stoat_ferret/jobs/queue.py:367-428`

The `process_jobs()` worker is a single coroutine processing one job at a time from `asyncio.Queue`. If a scan job is running, all subsequent jobs (including other scans) wait until it completes.

**Impact:** Low severity currently (scan is the only job type), but could become a bottleneck if more job types are added.

**Fix (future):** Consider a worker pool or concurrent job processing with configurable concurrency limits.
