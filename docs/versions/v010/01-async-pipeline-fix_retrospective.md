# Theme Retrospective: 01-async-pipeline-fix

## Theme Summary

This theme fixed a P0 blocking `subprocess.run()` call in `ffprobe_video()` that froze the asyncio event loop during directory scans, then added two layers of prevention to stop this class of bug from recurring. All three features shipped successfully with all acceptance criteria met and all quality gates passing.

**Scope:** 3 features | **Result:** 3/3 complete | **Quality gates:** All passing (ruff, mypy, pytest)

## Feature Results

| # | Feature | Acceptance | Quality Gates | Outcome |
|---|---------|------------|---------------|---------|
| 001 | fix-blocking-ffprobe | 5/5 PASS | ruff, mypy, pytest all pass | Converted `ffprobe_video()` to async using `asyncio.create_subprocess_exec()` with timeout and process cleanup |
| 002 | async-blocking-ci-gate | 3/3 PASS | ruff, mypy, pytest all pass | Enabled ruff ASYNC rules (ASYNC221/210/230) and fixed `_check_ffmpeg()` in health.py |
| 003 | event-loop-responsiveness-test | 4/4 PASS | ruff, mypy, pytest all pass | Added integration test verifying event-loop stays responsive during scans |

## Key Learnings

### What Worked

- **Layered approach to the fix**: The theme addressed the immediate bug (feature 001), added static analysis prevention (feature 002), and added runtime regression detection (feature 003). This defense-in-depth strategy means the same class of bug is unlikely to recur.
- **Python 3.10 compatibility awareness**: Using `asyncio.TimeoutError` instead of `builtins.TimeoutError` for the timeout catch was identified early from project memory, avoiding a subtle cross-platform failure.
- **`new_callable=AsyncMock` pattern**: Using `new_callable=AsyncMock` in `patch()` calls was cleaner than manually wrapping return values in coroutines. This is a reusable pattern for testing async code.
- **Using production `AsyncioJobQueue` in integration test**: The decision to use the real async queue instead of the sync `InMemoryJobQueue` stub was critical — only the production queue exercises actual async concurrency.

### Patterns Discovered

- **Module name collision avoidance**: The integration test was placed at `tests/test_event_loop_responsiveness.py` rather than in `tests/test_integration/` to avoid a Python module name collision with the existing `tests/test_integration.py` file.
- **`asyncio.to_thread()` for legacy sync code**: For code that must remain synchronous (like health check subprocess calls), `asyncio.to_thread()` is a clean bridge that avoids event-loop blocking without a full async rewrite.

## Technical Debt

No quality-gaps files were generated for this theme's features, indicating clean implementations. Minor items to note:

- **20 pre-existing test skips**: These are from tests requiring ffprobe/ffmpeg binaries not available in the test environment. Not introduced by this theme but worth tracking.
- **Health check still uses `subprocess.run` under `asyncio.to_thread()`**: Feature 002 wrapped the blocking call rather than converting it fully to `asyncio.create_subprocess_exec()`. This is acceptable for a low-frequency health check endpoint but is an inconsistency with the approach taken in feature 001.

## Recommendations

1. **Apply the same layered pattern for future bug-fix themes**: Fix the bug, add static analysis rules to catch it, add a runtime regression test. This theme demonstrated the pattern well.
2. **Consider standardizing async subprocess usage**: Two different approaches were used — `asyncio.create_subprocess_exec()` (feature 001) vs `asyncio.to_thread(subprocess.run)` (feature 002). For consistency, prefer `create_subprocess_exec()` for new code.
3. **Track the module name collision**: The `tests/test_integration.py` vs `tests/test_integration/` conflict should be resolved if more integration tests are added in the future.
