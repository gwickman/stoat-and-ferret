# Backlog Details — v010

## BL-072: Fix blocking subprocess.run() in ffprobe freezing async event loop

**Priority:** P0 | **Size:** L | **Status:** open | **Tags:** bug, async, ffmpeg, scan, user-feedback

**Description:**
> The `ffprobe_video()` function in `src/stoat_ferret/ffmpeg/probe.py` uses synchronous `subprocess.run()` with a 30s timeout per file. This is called from the async scan handler, which blocks the entire asyncio event loop for the duration of each ffprobe call. While blocked, the server cannot handle any HTTP requests — including job status polling — making the scan appear completely frozen. This also makes `asyncio.wait_for()` timeout unreliable since the event loop has no opportunity to check it between blocking calls. This is the primary cause of the "scan directory hangs forever" bug.

**Acceptance Criteria:**
1. ffprobe_video() uses asyncio.create_subprocess_exec() or asyncio.to_thread() instead of blocking subprocess.run()
2. HTTP status polling endpoint remains responsive during an active scan job
3. asyncio.wait_for() job timeout fires reliably at the configured threshold
4. Existing ffprobe tests pass with the async implementation
5. Scan of a directory with multiple video files completes without blocking other API requests

**Use Case:** When a user scans a media directory, the server must remain responsive so progress polling, cancellation, and other API calls continue working throughout the scan.

**Notes:** None

**Complexity Assessment:** HIGH — Touches the async subprocess layer affecting all FFmpeg/ffprobe interactions. Requires converting synchronous subprocess calls to async equivalents while preserving timeout behavior. The fix propagates through the scan pipeline and affects how tests mock subprocess behavior. Must maintain backward compatibility with existing ffprobe output parsing.

---

## BL-073: Add progress reporting to job queue and scan handler

**Priority:** P1 | **Size:** L | **Status:** open | **Tags:** jobs, scan, gui, ux, user-feedback

**Description:**
> The job queue (`AsyncioJobQueue`), job result model (`JobResult`), and job status response (`JobStatusResponse`) have no progress field. The scan handler processes files in a loop but never reports intermediate progress. The frontend polls job status but always receives `null` for progress, so the progress bar is permanently stuck at 0%. Users have no visibility into how far along a scan is or whether it's actually working.

**Acceptance Criteria:**
1. _AsyncJobEntry includes a progress field (0.0-1.0 float or integer percentage)
2. AsyncioJobQueue exposes a set_progress(job_id, value) method callable from within job handlers
3. Scan handler calls set_progress after each file, reporting scanned_count/total_files
4. GET /api/v1/jobs/{id} response includes a populated progress field during active jobs
5. Frontend ScanModal progress bar reflects actual scan progress in real time

**Use Case:** During a directory scan that may take minutes, users need to see real progress to know the operation is working and estimate remaining time.

**Notes:** None

**Complexity Assessment:** MEDIUM-HIGH — Requires changes across multiple layers: job queue data model, queue API, scan handler logic, REST API response schema, and frontend component. Each layer is straightforward but the cross-cutting nature increases coordination risk. Depends on BL-072 being complete (progress reporting is meaningless if the event loop is frozen).

---

## BL-074: Implement job cancellation support for scan and job queue

**Priority:** P1 | **Size:** M | **Status:** open | **Tags:** jobs, scan, api, gui, user-feedback

**Description:**
> The `AsyncioJobQueue` has no `cancel()` method, no cancellation flag mechanism, and no cancel API endpoint. The scan handler's file processing loop has no cancellation check point. The frontend cancel button exists in ScanModal but has nothing to call — once a scan starts, the only way to stop it is to restart the server. Users are stuck waiting for potentially long scans with no way to abort.

**Acceptance Criteria:**
1. AsyncioJobQueue has a cancel(job_id) method that sets a cancellation flag on the running job
2. A cancel API endpoint exists (DELETE /api/v1/jobs/{id} or POST /api/v1/jobs/{id}/cancel) returning appropriate status
3. Scan handler checks the cancellation flag between file iterations and exits cleanly when cancelled
4. Cancelled jobs report status 'cancelled' with partial results (files scanned so far are retained)
5. Frontend ScanModal cancel button calls the cancel endpoint and updates UI to reflect cancellation

**Use Case:** When a user accidentally scans the wrong directory or needs to stop a long-running scan, they need the cancel button to actually work rather than being forced to restart the application.

**Notes:** None

**Complexity Assessment:** MEDIUM — Cooperative cancellation is a well-understood pattern. The main design decision is the cancellation flag mechanism (asyncio.Event, threading.Event, or a simple boolean). Requires changes across the same layers as BL-073 (queue, handler, API, frontend) but the cancellation logic at each layer is simpler than progress reporting.

---

## BL-077: Add CI quality gate for blocking calls in async context

**Priority:** P2 | **Size:** L | **Status:** open | **Tags:** ci, quality-gates, async, lint, rca

**Description:**
> No automated check exists to detect synchronous blocking calls inside async code. Ruff, mypy, and pytest all pass despite `subprocess.run()` being called from an async scan handler, which froze the entire asyncio event loop. Two additional `subprocess.run()` calls exist in `src/` (executor.py:96, health.py:96) — one will cause the same problem when render jobs use the async job queue. A grep-based CI script (~20 lines) scanning for blocking calls in files containing `async def` would catch this entire class of bug at CI time.

**Acceptance Criteria:**
1. A CI script or quality gate check exists that scans Python source files for blocking calls (subprocess.run, subprocess.call, subprocess.check_output, time.sleep) inside files that also contain async def
2. The check runs as part of the existing quality gates (alongside ruff, mypy, pytest)
3. The check fails with a clear error message identifying the file, line number, and the blocking call
4. The check passes on the current codebase after BL-072 is fixed (async ffprobe)
5. False positives for legitimate sync-only files are avoided by only flagging files containing async def

**Use Case:** null — Updated to: When a developer adds new FFmpeg features, they might unknowingly use blocking subprocess calls inside async handlers. Without a CI check, this class of bug silently passes all tests and only manifests under load. A CI gate catches this at PR time.

**Notes:** Depends on BL-072 (fix blocking ffprobe) being completed first, otherwise the check would immediately fail on the known bug.

**Complexity Assessment:** MEDIUM — The CI script itself is simple (~20 lines of grep/awk). The design decisions are: (1) where to integrate it in the quality gate pipeline, (2) how to handle legitimate exceptions (e.g., allowlist for sync-only files), and (3) how to report violations clearly. Depends on BL-072 being complete first.

---

## BL-078: Add event-loop responsiveness integration test for scan pipeline

**Priority:** P2 | **Size:** L | **Status:** open | **Tags:** testing, integration, async, scan, rca

**Description:**
> All current scan tests mock `ffprobe_video()`, making the blocking behavior that caused the "scan hangs forever" bug invisible to the test suite. No integration test verifies that the server remains responsive during a scan. An event-loop responsiveness test that uses real or simulated-slow subprocess calls (not mocks) would have caught the ffprobe blocking bug and would serve as a regression guard against future async/blocking issues in the scan pipeline.

**Acceptance Criteria:**
1. An integration test exists that starts a directory scan with multiple files requiring real or simulated-slow processing
2. While the scan runs, the test verifies that GET /api/v1/jobs/{id} responds within 2 seconds
3. The test does NOT mock ffprobe_video — it must exercise real or simulated subprocess behavior to detect event-loop blocking
4. The test fails if the event loop is starved (i.e. if blocking subprocess calls prevent polling responses)
5. The test passes after BL-072 (async ffprobe) is implemented

**Use Case:** null — Updated to: When a developer modifies the scan pipeline or adds new subprocess calls to async code paths, this integration test verifies the event loop remains responsive, detecting event-loop starvation that unit tests with mocks cannot catch.

**Notes:** Depends on BL-072 (fix blocking ffprobe) — this test validates the fix and prevents regression. Should be implemented alongside or after BL-072.

**Complexity Assessment:** HIGH — Integration tests that verify event-loop responsiveness require careful timing, concurrent request handling, and simulated-slow subprocess calls. Must avoid flaky timing-dependent assertions while still reliably detecting blocking. CI environment variability (slower runners) adds complexity. The test design needs to balance sensitivity with reliability.
