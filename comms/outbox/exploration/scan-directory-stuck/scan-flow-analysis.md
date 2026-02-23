# Scan Flow Analysis

End-to-end trace of the scan directory feature, identifying where the flow breaks down.

## Step 1: User Clicks "Start Scan"

**File:** `gui/src/components/ScanModal.tsx:50-70`

The `handleSubmit` function fires, POSTing to `/api/v1/videos/scan`:

```tsx
const res = await fetch('/api/v1/videos/scan', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ path: directory.trim(), recursive }),
})
const { job_id } = await res.json()
```

**Status:** Works correctly. Returns quickly with a `job_id`.

## Step 2: Job Submitted to Queue

**File:** `src/stoat_ferret/api/routers/videos.py:167-207`

The endpoint validates the path and submits an async job:

```python
job_id = await job_queue.submit(SCAN_JOB_TYPE, {"path": path, "recursive": body.recursive})
return JobSubmitResponse(job_id=job_id)  # HTTP 202
```

**File:** `src/stoat_ferret/jobs/queue.py:312-327`

`AsyncioJobQueue.submit()` puts the job ID on an `asyncio.Queue` for the background worker.

**Status:** Works correctly. Job enters the queue in `PENDING` state.

## Step 3: Frontend Starts Polling

**File:** `gui/src/components/ScanModal.tsx:72-92`

A 1-second `setInterval` polls `GET /api/v1/jobs/{job_id}`:

```tsx
pollRef.current = setInterval(async () => {
  const statusRes = await fetch(`/api/v1/jobs/${job_id}`)
  const status: JobStatus = await statusRes.json()
  setProgress(status.progress)  // Always null - never set by backend
  if (status.status === 'completed') { ... }
  else if (status.status === 'failed') { ... }
  // NOTE: 'timeout' status is not handled
}, 1000)
```

**Status:** Starts correctly but polls will stall (see Step 4).

## Step 4: Background Worker Picks Up Job -- EVENT LOOP BLOCKED

**File:** `src/stoat_ferret/jobs/queue.py:367-428`

The worker sets status to `RUNNING` and calls the scan handler:

```python
entry.status = JobStatus.RUNNING
result = await asyncio.wait_for(
    handler(entry.job_type, entry.payload),
    timeout=self._timeout,  # 300s
)
```

**File:** `src/stoat_ferret/api/services/scan.py:140-188`

The scan handler iterates every file and calls `ffprobe_video()`:

```python
for file_path in root.glob(pattern):
    # ...
    metadata = ffprobe_video(str_path)  # BLOCKING CALL
```

**File:** `src/stoat_ferret/ffmpeg/probe.py:65-79`

`ffprobe_video()` uses `subprocess.run()` — a **synchronous, blocking** call:

```python
result = subprocess.run(
    [ffprobe_path, "-v", "quiet", "-print_format", "json", ...],
    capture_output=True,
    timeout=30,
    check=False,
)
```

### THIS IS WHERE THE FLOW BREAKS

`subprocess.run()` blocks the **entire asyncio event loop** for up to 30 seconds per file. During this time:
- The FastAPI server cannot process ANY HTTP requests
- Polling requests from the frontend queue up but cannot be served
- The progress bar appears frozen because no poll responses return
- With many files, the event loop is blocked for the entire duration of the scan

The scan itself may actually be progressing file-by-file, but the user sees no indication because the event loop is monopolized.

## Step 5: Scan Completes (Eventually) or Times Out

If the scan finishes within the 300s job timeout, the worker sets `COMPLETE` status. If it exceeds 300s, the `asyncio.wait_for()` raises `asyncio.TimeoutError` and status becomes `TIMEOUT`.

However, the timeout mechanism itself is broken by the blocking calls. `asyncio.wait_for()` can only raise `TimeoutError` when the event loop regains control. Since `subprocess.run()` never yields, the timeout may not fire at the expected time — it fires on the next `await` after the blocking call returns.

## Step 6: Frontend Receives Status Update

Once the event loop is unblocked (scan completes or a subprocess finishes), the backlogged polling request is served. The frontend then transitions from `scanning` to `complete` or `error`.

**Additional issue:** The frontend does not handle `timeout` status (line 80-88 only checks `completed` and `failed`). If the job times out, the frontend continues polling indefinitely.

## Flow Diagram

```
User clicks "Start Scan"
       |
       v
POST /api/v1/videos/scan  -->  Submit to AsyncioJobQueue  -->  Return 202 + job_id
       |
       v
Frontend starts polling GET /api/v1/jobs/{id} every 1s
       |                                                Worker picks up job
       v                                                       |
Poll request #1  -----> BLOCKED                         ffprobe_video() [BLOCKING]
Poll request #2  -----> BLOCKED                         ffprobe_video() [BLOCKING]
Poll request #3  -----> BLOCKED                         ffprobe_video() [BLOCKING]
  ...                    ...                                   ...
                                                        All files processed
       |                                                       |
       v                                                       v
Backlogged polls served  <-----  Event loop unblocked   Job status = COMPLETE
       |
       v
Frontend shows completion (progress bar jumped from 0% to done)
```
