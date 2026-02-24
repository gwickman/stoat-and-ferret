# Architecture Alignment: v010

Architecture drift detected. v010 introduced 11 new drift items across the job queue, scan service, FFmpeg probe, health check, REST API, and frontend. All findings are grounded in code evidence. The existing open backlog item BL-069 (from v009) was updated with the additional v010 drift rather than creating a duplicate.

## Existing Open Items

- **BL-069**: "Update C4 architecture documentation for v009 changes" (P2, open). Documents 5 drift areas from v009 including logging rotation, project repository count(), SPA routing, ObservableFFmpegExecutor/AuditLogger wiring, and WebSocket broadcast wiring. C4 docs were last generated for v008; regeneration failed for both v009 and v010.

## Changes in v010

v010 delivered 5 features across 2 themes:

**Theme 01 (async-pipeline-fix):**
- Converted `ffprobe_video()` from sync `subprocess.run()` to async `asyncio.create_subprocess_exec()` with timeout and process cleanup
- Added ruff ASYNC rules (ASYNC221/210/230) as CI guardrails
- Converted `_check_ffmpeg()` to async via `asyncio.to_thread()`
- Added event-loop responsiveness integration test

**Theme 02 (job-controls):**
- Added `progress` field to `JobResult` and `set_progress()` to `AsyncJobQueue` Protocol
- Added cooperative cancellation via `asyncio.Event` with `cancel()` on Protocol and `CANCELLED` status
- Added `POST /api/v1/jobs/{id}/cancel` REST endpoint (200/404/409)
- Extended `scan_directory()` with `progress_callback` and `cancel_event` kwargs
- Extended `make_scan_handler()` with `ws_manager` and `queue` kwargs
- Added cancel button to frontend ScanModal component

## Documentation Status

| Document | Exists | Last Updated | Version |
|----------|--------|--------------|---------|
| docs/C4-Documentation/README.md | Yes | 2026-02-22 | v008 |
| docs/C4-Documentation/c4-context.md | Yes | v008 | v008 |
| docs/C4-Documentation/c4-container.md | Yes | v008 | v008 |
| docs/C4-Documentation/c4-component-application-services.md | Yes | v008 | v008 |
| docs/C4-Documentation/c4-code-stoat-ferret-jobs.md | Yes | v008 | v008 |
| docs/C4-Documentation/c4-code-stoat-ferret-ffmpeg.md | Yes | v008 | v008 |
| docs/C4-Documentation/c4-code-stoat-ferret-api-services.md | Yes | v008 | v008 |
| docs/C4-Documentation/c4-code-stoat-ferret-api-routers.md | Yes | v008 | v008 |
| docs/ARCHITECTURE.md | Yes | - | - |

C4 documentation is now 2 versions behind (last generated for v008, with drift from both v009 and v010). Regeneration failed for both v009 and v010.

## Drift Assessment

11 new drift items detected, all verified against code:

### Application Services / Job Queue (5 items)

1. **AsyncJobQueue Protocol expanded**: C4 lists only `submit/get_status/get_result`. Protocol now includes `set_progress(job_id, value)` and `cancel(job_id)`. Evidence: `src/stoat_ferret/jobs/queue.py:102-117`.

2. **New CANCELLED job status**: C4 lists PENDING/RUNNING/COMPLETE/FAILED/TIMEOUT. Code adds CANCELLED. Evidence: `src/stoat_ferret/jobs/queue.py:25`.

3. **JobResult includes progress field**: C4 lists job_id/status/result/error. Code adds `progress: float | None`. Evidence: `src/stoat_ferret/jobs/queue.py:52`.

4. **AsyncioJobQueue.process_jobs() injects _job_id and _cancel_event**: Undocumented handler payload injection pattern. Evidence: `src/stoat_ferret/jobs/queue.py:464-469`.

5. **C4 context "Async Job Processing" feature description outdated**: Lists statuses without cancelled, doesn't mention progress reporting or cancellation capabilities.

### FFmpeg / Probe (2 items)

6. **ffprobe_video() converted to async**: C4 documents it as sync `ffprobe_video(path: str) -> VideoMetadata` using subprocess. Now uses `async def ffprobe_video()` with `asyncio.create_subprocess_exec()`, 30s timeout, and process cleanup on timeout. Evidence: `src/stoat_ferret/ffmpeg/probe.py:45-83`.

7. **_check_ffmpeg() converted to async**: C4 lists it as sync. Now `async def _check_ffmpeg()` using `asyncio.to_thread(subprocess.run)`. Evidence: `src/stoat_ferret/api/routers/health.py:86-97`.

### API / REST Endpoints (1 item)

8. **New REST endpoint POST /api/v1/jobs/{id}/cancel**: Returns 200 (cancelled), 404 (not found), 409 (already terminal). Not in C4 container API interfaces list. Evidence: `src/stoat_ferret/api/routers/jobs.py:51`.

### Scan Service (2 items)

9. **scan_directory() signature expanded**: C4 shows `scan_directory(path, recursive, repository, thumbnail_service)`. Code adds `progress_callback` and `cancel_event` keyword arguments. Evidence: `src/stoat_ferret/api/services/scan.py:121-128`.

10. **make_scan_handler() signature expanded**: C4 shows `make_scan_handler(repository, thumbnail_service)`. Code adds `ws_manager` and `queue` keyword arguments. Evidence: `src/stoat_ferret/api/services/scan.py:57-62`.

### Frontend (1 item)

11. **ScanModal includes cancel button**: C4 GUI component doesn't mention scan cancellation capability. Evidence: `gui/src/components/ScanModal.tsx:58`.

## Action Taken

Updated existing open backlog item **BL-069** with notes documenting all 11 v010 drift items. No new backlog item created since BL-069 already covers C4 documentation regeneration. The item now tracks drift from both v009 (5 items) and v010 (11 items), totaling 16 documented drift areas.
