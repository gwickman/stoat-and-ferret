# Version Retrospective: v010

## Version Summary

**Version:** v010
**Title:** Fix the P0 async blocking bug, add CI guardrails to prevent recurrence, then build user-facing job progress and cancellation on the working pipeline.
**Date:** 2026-02-23

v010 delivered two tightly coupled themes addressing a P0 event-loop blocking bug and then building user-facing job controls on the now-working async pipeline. Theme 01 fixed the root cause (`subprocess.run()` in `ffprobe_video()` freezing the asyncio event loop), added ruff ASYNC rules as a CI guardrail, and added an integration test for event-loop responsiveness. Theme 02 built on that foundation to deliver real-time progress reporting and cooperative job cancellation across the full stack (queue → scan handler → REST API → frontend).

All 5 features across both themes shipped successfully with all acceptance criteria met and all quality gates passing (ruff, mypy, pytest, vitest).

## Theme Results

| # | Theme | Features | Result | Quality Gates | Outcome |
|---|-------|----------|--------|---------------|---------|
| 01 | async-pipeline-fix | 3 | 3/3 complete | All passing | Fixed P0 blocking ffprobe, added ASYNC ruff rules, added event-loop responsiveness integration test |
| 02 | job-controls | 2 | 2/2 complete | All passing | Added progress reporting and cooperative cancellation with frontend cancel button |

## C4 Documentation

**Status:** Regeneration failed.

C4 architecture documentation was not regenerated for this version. This should be tracked as technical debt and addressed in a future version or as a standalone task.

## Cross-Theme Learnings

### Layered defense-in-depth pattern
Theme 01 demonstrated an effective three-layer approach to bug fixes: fix the bug (async ffprobe), add static analysis prevention (ruff ASYNC rules), add runtime regression detection (event-loop responsiveness test). This pattern should be applied to future critical bug fixes.

### Protocol-first design across both themes
Both themes benefited from updating the `AsyncJobQueue` Protocol alongside the production `AsyncioJobQueue` and keeping `InMemoryJobQueue` in sync. Type checking caught integration issues early throughout the version.

### Shared-layer cohesion
Theme 02's features (progress and cancellation) both touched the same stack layers (queue → scan handler → API → frontend). Grouping features by modification point within a theme minimized merge conflicts and kept changes cohesive.

### Python 3.10 compatibility awareness
Using `asyncio.TimeoutError` (not `builtins.TimeoutError`) and `asyncio.Event` (safe when created inside async context) were identified early from project memory, avoiding subtle cross-version failures.

### Optional kwargs for backward compatibility
Both themes added optional keyword arguments (`progress_callback`, `cancel_event`, `queue`) to existing functions rather than changing signatures, avoiding breaking changes across the test suite and application wiring.

## Technical Debt Summary

| Item | Source | Priority | Notes |
|------|--------|----------|-------|
| C4 documentation regeneration failed | v010 close | Medium | Architecture docs not updated for v010 changes |
| 20 pre-existing test skips | Both themes | Low | Tests requiring ffprobe/ffmpeg binaries not available in test environment |
| `InMemoryJobQueue` growing no-op surface | Theme 02 | Low | `set_progress()` and `cancel()` are no-ops on the test double; gap widens with each queue feature |
| Health check uses `asyncio.to_thread()` not `create_subprocess_exec()` | Theme 01 | Low | Inconsistency in async subprocess approach; acceptable for low-frequency endpoint |
| No WebSocket/SSE push for progress | Theme 02 | Low | Progress is poll-based; real-time push deferred as out of scope |
| `tests/test_integration.py` vs `tests/test_integration/` module name conflict | Theme 01 | Low | Should be resolved if more integration tests are added |

## Process Improvements

1. **Layered bug-fix themes work well**: The fix → static analysis → runtime test pattern from Theme 01 should become a standard template for P0/P1 bug-fix versions.
2. **Theme dependency ordering is effective**: Making Theme 02 depend on Theme 01 (progress/cancellation need a working event loop) prevented wasted work and kept the execution order logical.
3. **Full-stack feature delivery validated**: Theme 02 Feature 002 delivered changes from the queue data model through to the React frontend cancel button with Vitest coverage, confirming the pipeline can handle end-to-end features.
4. **Frontend testing with Vitest integrates well**: The quality gate pipeline successfully includes Vitest alongside ruff, mypy, and pytest.

## Statistics

| Metric | Value |
|--------|-------|
| Themes | 2 |
| Features completed | 5/5 |
| Acceptance criteria passed | 37/37 |
| Quality gate failures | 0 |
| Backlog items addressed | BL-072, BL-073, BL-074, BL-077, BL-078 |
| Key files modified | `ffprobe.py`, `health.py`, `job_queue.py`, `scan.py`, `jobs_router.py`, frontend components |
