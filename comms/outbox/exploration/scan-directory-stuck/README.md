# Scan Directory Stuck - Investigation Results

The scan appears to hang because of two compounding issues: (1) `ffprobe_video()` uses blocking `subprocess.run()` inside the async scan handler, which blocks the entire asyncio event loop — including the polling endpoint — so the frontend can never receive status updates while a scan is in progress, and (2) the `progress` field is never populated by the backend, so the progress bar is permanently stuck at 0% even if polling were working.

## Architecture Overview

The scan feature uses an async job queue pattern:

1. **Frontend** (`gui/src/components/ScanModal.tsx`) — modal with directory input, submits POST to `/api/v1/videos/scan`, then polls `GET /api/v1/jobs/{id}` every 1 second
2. **Scan endpoint** (`src/stoat_ferret/api/routers/videos.py:167`) — validates path, submits job to `AsyncioJobQueue`, returns 202 with `job_id`
3. **Job queue** (`src/stoat_ferret/jobs/queue.py:279`) — `AsyncioJobQueue` with single background worker coroutine processing jobs sequentially
4. **Scan handler** (`src/stoat_ferret/api/services/scan.py:55`) — iterates files, runs `ffprobe_video()` per file, writes to DB
5. **FFprobe** (`src/stoat_ferret/ffmpeg/probe.py:45`) — blocking `subprocess.run()` with 30s timeout per file

## Identified Issues Summary

| # | Issue | Severity | Type |
|---|-------|----------|------|
| 1 | Blocking `subprocess.run()` in async context freezes event loop | **Critical** | Confirmed bug |
| 2 | Progress field never populated (always `None`) | **High** | Confirmed gap |
| 3 | Cancel button disabled during scan; no backend cancel support | **High** | Confirmed gap |
| 4 | Frontend ignores `timeout` job status | **Medium** | Confirmed bug |
| 5 | Single-worker queue means one stuck scan blocks all jobs | **Medium** | Design limitation |

## Output Files

- `scan-flow-analysis.md` — End-to-end trace showing where the flow breaks
- `backend-issues.md` — Backend bugs and gaps with code references
- `frontend-issues.md` — Frontend state management and UI issues
