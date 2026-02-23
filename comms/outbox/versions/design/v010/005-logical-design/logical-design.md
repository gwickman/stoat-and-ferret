# Logical Design — v010 Async Pipeline & Job Controls

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

**Goal:** Fix the P0 blocking `subprocess.run()` in ffprobe that freezes the asyncio event loop during scans, then add CI guardrails (ruff ASYNC rules) and an integration test to prevent this class of bug from recurring. All three features address the same root cause — blocking subprocess calls in async context.

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

Reference: `comms/outbox/versions/design/v010/004-research/external-research.md` (Section 1), `comms/outbox/versions/design/v010/004-research/codebase-patterns.md` (Sections 1-2)

**002-async-blocking-ci-gate (BL-077)**

Add `"ASYNC"` to the ruff lint `select` list in `pyproject.toml`. This enables ASYNC221 (blocking subprocess in async), ASYNC210 (blocking HTTP in async), and ASYNC230 (blocking file I/O in async) — AST-based detection with zero CI configuration changes.

Handle `health.py:96` which has `subprocess.run()` in a file with `async def`. Convert the `_check_ffmpeg()` helper to use `asyncio.to_thread(subprocess.run, ...)` for consistency with v010's async-correctness theme.

Research finding adopted: Ruff ASYNC221 replaces the originally-planned grep-based CI script — superior detection (AST-aware, no false positives), 1-line config change.

Reference: `comms/outbox/versions/design/v010/004-research/external-research.md` (Section 2)

**003-event-loop-responsiveness-test (BL-078)**

Create an integration test using `httpx.AsyncClient` with a simulated-slow async ffprobe (using `asyncio.sleep()`, not mocks). Start a scan, then concurrently poll `GET /api/v1/jobs/{id}` with a 2-second timeout. If someone regresses to blocking calls, `time.sleep()` would starve the event loop and the polling request would time out.

Mark with `@pytest.mark.slow` and `@pytest.mark.integration`. Use explicit `asyncio.wait_for()` for the 2-second threshold per LRN-043.

Reference: `comms/outbox/versions/design/v010/004-research/external-research.md` (Section 4)

---

## Theme 2: 02-job-controls

**Goal:** Add user-facing job progress reporting and cooperative cancellation to the scan pipeline. Both features extend the existing `AsyncioJobQueue` (LRN-009, LRN-010) and touch the same layers: queue data model, scan handler, REST API, and frontend. Depends on Theme 1 completing — progress and cancellation are meaningless if the event loop is frozen.

**Backlog Items:** BL-073, BL-074

### Features

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-progress-reporting | Add progress tracking to job queue and wire through scan handler to frontend | BL-073 | Theme 1 complete |
| 2 | 002-job-cancellation | Add cooperative cancellation with cancel endpoint and partial results | BL-074 | 001-progress-reporting |

### Feature Details

**001-progress-reporting (BL-073)**

Add `progress: float | None = None` to `_AsyncJobEntry`. Add `set_progress(job_id, value)` to `AsyncioJobQueue`. Pass a progress callback into `scan_directory()` via the `make_scan_handler()` factory closure. Call `set_progress(job_id, scanned / total_files)` after each file. Wire `progress` into `JobStatusResponse` in the jobs router. No new `create_app()` kwargs needed — progress is internal to the job queue.

The frontend (`ScanModal.tsx`) already reads `status.progress` and renders a percentage bar — only backend population is missing.

Acceptance criteria for end-to-end validation: progress bar must update in real time during a multi-file scan, not just pass unit tests for `set_progress()`.

Reference: `comms/outbox/versions/design/v010/004-research/codebase-patterns.md` (Sections 3-6)

**002-job-cancellation (BL-074)**

Add `cancel_event: asyncio.Event` to `_AsyncJobEntry`. Add `cancel(job_id)` method to `AsyncioJobQueue` that sets the event. Add `CANCELLED` to `JobStatus` enum. Pass the cancel event into `scan_directory()` via the handler factory. Check `cancel_event.is_set()` between files in the scan loop — break and return partial results when set. Add `POST /api/v1/jobs/{id}/cancel` REST endpoint. Enable the frontend cancel button in `ScanModal.tsx` to call the endpoint.

Cancellation mechanism: `asyncio.Event` per job — lightweight, awaitable, thread-safe, stdlib only (LRN-010).

Acceptance criteria for end-to-end validation: cancel button must stop the scan and show partial results in the UI, not just pass unit tests for the cancel event.

Reference: `comms/outbox/versions/design/v010/004-research/external-research.md` (Section 3)

---

## Execution Order

### Theme Order

1. **Theme 1: 01-async-pipeline-fix** — Must complete first. The P0 blocking bug (BL-072) makes the event loop unresponsive, which means progress reporting and cancellation cannot function. CI guardrails (BL-077, BL-078) validate and protect the fix.

2. **Theme 2: 02-job-controls** — Builds on the working async pipeline. Progress and cancellation extend the same `AsyncioJobQueue` and `scan_directory()` that Theme 1 fixes.

### Feature Order Within Themes

**Theme 1:**
1. `001-fix-blocking-ffprobe` — Foundation fix. Everything else depends on this.
2. `002-async-blocking-ci-gate` — Depends on 001 (ruff ASYNC rules would fail on unfixed code).
3. `003-event-loop-responsiveness-test` — Depends on 001 (test validates the fix). Can be parallel with 002 but sequential is safer since both modify test infrastructure.

**Theme 2:**
1. `001-progress-reporting` — Adds `progress` field and callback infrastructure to `_AsyncJobEntry` and `scan_directory()`.
2. `002-job-cancellation` — Adds `cancel_event` and `cancel()` to the same `_AsyncJobEntry` and `scan_directory()`. Ordered second to avoid merge conflicts on the shared data structures.

### Rationale

- BL-072 (P0) first aligns with LRN-033 (fix foundational issues first)
- Theme grouping by modification point aligns with LRN-042
- Within Theme 2, progress before cancellation because: (a) both modify `_AsyncJobEntry` — sequential avoids conflicts, (b) progress infrastructure is simpler and establishes the pattern for scan handler callbacks

---

## Handler Concurrency Decisions

Not applicable — no new MCP tool handlers are introduced in v010.

The new REST endpoint (`POST /api/v1/jobs/{id}/cancel`) is a lightweight in-memory operation (setting an `asyncio.Event`). It is inherently async-safe and requires no special concurrency handling.

---

## Research Sources Adopted

| Finding | Source | Decision |
|---------|--------|----------|
| `asyncio.create_subprocess_exec()` for ffprobe | `004-research/external-research.md` §1 | Adopted — native async, no thread overhead |
| Ruff ASYNC221 rule replaces grep script | `004-research/external-research.md` §2 | Adopted — AST-aware, 1-line config change |
| `asyncio.Event` per job for cancellation | `004-research/external-research.md` §3 | Adopted — lightweight, stdlib, awaitable |
| `httpx.AsyncClient` responsiveness test pattern | `004-research/external-research.md` §4 | Adopted — concurrent polling during slow scan |
| Frontend already reads `progress` field | `004-research/codebase-patterns.md` §5-6 | Confirmed — only backend population needed |
| 0 new `create_app()` kwargs | `004-research/codebase-patterns.md` §7 | Confirmed — progress/cancel internal to queue |
| `health.py:96` will trigger ASYNC221 | `004-research/impact-analysis.md` §Breaking | Handle with `asyncio.to_thread()` in BL-077 |
| All 12 learnings verified | `004-research/evidence-log.md` §Learning Verification | All conditions still present in codebase |
