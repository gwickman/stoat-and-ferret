# Refined Logical Design — v010 Async Pipeline & Job Controls

## Version Overview

**Version:** v010
**Description:** Fix the P0 async blocking bug, add CI guardrails to prevent recurrence, then build user-facing job progress and cancellation on the working pipeline.
**Backlog items:** BL-072, BL-073, BL-074, BL-077, BL-078 (5 items, all mandatory)

### Goals

1. Restore async correctness — eliminate event-loop blocking from the scan pipeline (BL-072)
2. Prevent recurrence — CI-level detection of blocking calls in async code (BL-077) and runtime regression test (BL-078)
3. Enable user visibility — progress reporting during scans (BL-073)
4. Enable user control — cooperative job cancellation (BL-074)

---

## Theme 1: 01-async-pipeline-fix

**Goal:** Fix the P0 blocking `subprocess.run()` in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails (ruff ASYNC rules) and an integration test to prevent this class of bug from recurring.

**Backlog Items:** BL-072, BL-077, BL-078

### Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-fix-blocking-ffprobe | Convert ffprobe_video() from blocking subprocess.run() to async create_subprocess_exec() | BL-072 | None |
| 2 | 002-async-blocking-ci-gate | Add ruff ASYNC rules to detect blocking calls in async functions at CI time | BL-077 | 001-fix-blocking-ffprobe |
| 3 | 003-event-loop-responsiveness-test | Integration test verifying the event loop stays responsive during scan | BL-078 | 001-fix-blocking-ffprobe |

### Feature Details

**001-fix-blocking-ffprobe (BL-072)**

Convert `ffprobe_video()` in `src/stoat_ferret/ffmpeg/probe.py` from synchronous `subprocess.run()` to `asyncio.create_subprocess_exec()` with `communicate()`. Update the sole caller `scan_directory()` to `await` the call. Update all ffprobe and scan tests to handle the async function.

Research finding adopted: `asyncio.create_subprocess_exec()` over `asyncio.to_thread()` — native async I/O, no thread pool overhead, `communicate()` handles pipes cleanly. Preserve existing 30-second timeout via `asyncio.wait_for()`.

**002-async-blocking-ci-gate (BL-077)**

Add `"ASYNC"` to the ruff lint `select` list in `pyproject.toml`. This enables ASYNC221, ASYNC210, and ASYNC230.

Handle `health.py:96` which has `subprocess.run()` in a file with `async def`. Convert `_check_ffmpeg()` to use `asyncio.to_thread(subprocess.run, ...)`.

**Risk investigation confirmed** (see `risk-assessment.md`): Only `health.py:96` triggers beyond the BL-072 target. Zero ASYNC210 or ASYNC230 violations exist. No additional work needed.

**003-event-loop-responsiveness-test (BL-078)**

Create an integration test using `httpx.AsyncClient` with ASGI transport and simulated-slow async ffprobe (`asyncio.sleep()`). Start a scan, concurrently poll `GET /api/v1/jobs/{id}` with a 2-second timeout via `asyncio.wait_for()`.

**Risk mitigation applied**: Document in the test docstring that the 2-second threshold is intentionally generous for in-process ASGI transport (typical response <10ms). If flaky on CI, increase to 5 seconds before investigating further.

---

## Theme 2: 02-job-controls

**Goal:** Add user-facing job progress reporting and cooperative cancellation to the scan pipeline. Both features extend `AsyncioJobQueue` and touch the same layers: queue data model, scan handler, REST API, and frontend. Depends on Theme 1 completing.

**Backlog Items:** BL-073, BL-074

### Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-progress-reporting | Add progress tracking to job queue and wire through scan handler to frontend | BL-073 | Theme 1 complete |
| 2 | 002-job-cancellation | Add cooperative cancellation with cancel endpoint and partial results | BL-074 | 001-progress-reporting |

### Feature Details

**001-progress-reporting (BL-073)**

Add `progress: float | None = None` to `_AsyncJobEntry`. Add `set_progress(job_id, value)` to `AsyncioJobQueue`. Pass a progress callback into `scan_directory()` via the `make_scan_handler()` factory closure. Call `set_progress(job_id, scanned / total_files)` after each file. Wire `progress` into `JobStatusResponse` in the jobs router.

**Design refinement from risk investigation**: Update `AsyncJobQueue` Protocol (at `queue.py:52`) to include `set_progress()`. Add no-op `set_progress()` to `InMemoryJobQueue` for protocol compliance. This prevents test double drift across 8+ test files using `InMemoryJobQueue`.

Use keyword-only parameter: `scan_directory(..., *, progress_callback=None)`.

The frontend (`ScanModal.tsx`) already reads `status.progress` and renders a percentage bar — only backend population is missing.

**002-job-cancellation (BL-074)**

Add `cancel_event: asyncio.Event` to `_AsyncJobEntry` via `field(default_factory=asyncio.Event)`. Add `cancel(job_id)` method to `AsyncioJobQueue` that sets the event. Add `CANCELLED` to `JobStatus` enum. Pass the cancel event into `scan_directory()` via the handler factory. Check `cancel_event.is_set()` between files. Add `POST /api/v1/jobs/{id}/cancel` endpoint. Enable the frontend cancel button.

**Risk investigation confirmed**: `asyncio.Event` creation is safe — `_AsyncJobEntry` is only instantiated inside `async def submit()` where the event loop is running. Python 3.10 compatible.

**Design refinement from risk investigation**: Update `AsyncJobQueue` Protocol to include `cancel()`. Add no-op `cancel()` to `InMemoryJobQueue`.

Use keyword-only parameter: `scan_directory(..., *, progress_callback=None, cancel_event=None)`.

---

## Execution Order

### Theme Order

1. **Theme 1: 01-async-pipeline-fix** — Must complete first. The P0 blocking bug makes progress/cancel impossible.
2. **Theme 2: 02-job-controls** — Builds on the working async pipeline.

### Feature Order Within Themes

**Theme 1:**
1. `001-fix-blocking-ffprobe` — Foundation fix
2. `002-async-blocking-ci-gate` — Depends on 001 (ruff ASYNC rules would fail on unfixed code)
3. `003-event-loop-responsiveness-test` — Depends on 001 (validates the fix)

**Theme 2:**
1. `001-progress-reporting` — Adds progress field, callback, and Protocol updates
2. `002-job-cancellation` — Adds cancel_event, cancel(), and Protocol updates. Ordered second to build on the callback pattern established in 001.

---

## Changes from Task 005

1. **Protocol and test double updates added**: BL-073 and BL-074 now explicitly include updating `AsyncJobQueue` Protocol and adding no-op methods to `InMemoryJobQueue`. Task 005 flagged the risk; this design makes it a required implementation step.
2. **CI timing mitigation documented**: BL-078 test includes explicit documentation guidance for the 2-second threshold, with a fallback-to-5-seconds mitigation strategy.
3. **ASYNC violation scope confirmed**: Task 005's "UNVERIFIED" assumption about only `health.py:96` triggering is now VERIFIED. No additional handling needed.
4. **asyncio.Event safety confirmed**: Task 005's "UNVERIFIED" assumption about event creation timing is now VERIFIED. `default_factory=asyncio.Event` is safe.
5. **Keyword-only parameters specified**: `scan_directory()` new parameters explicitly use `*` keyword-only syntax per KISS principle.

---

## Research Sources Adopted

| Finding | Source | Decision |
|---------|--------|----------|
| `asyncio.create_subprocess_exec()` for ffprobe | `004-research/external-research.md` §1 | Adopted |
| Ruff ASYNC221 replaces grep script | `004-research/external-research.md` §2 | Adopted |
| `asyncio.Event` per job for cancellation | `004-research/external-research.md` §3 | Adopted |
| `httpx.AsyncClient` responsiveness test | `004-research/external-research.md` §4 | Adopted |
| Frontend already reads `progress` field | `004-research/codebase-patterns.md` §5-6 | Confirmed |
| 0 new `create_app()` kwargs | `004-research/codebase-patterns.md` §7 | Confirmed |
| Only `health.py:96` triggers ASYNC221 | `006-critical-thinking/risk-assessment.md` | Verified |
| `asyncio.Event` safe in `submit()` | `006-critical-thinking/risk-assessment.md` | Verified |

---

## Handler Concurrency Decisions

Not applicable — no new MCP tool handlers introduced in v010.
