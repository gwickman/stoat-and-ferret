# Risks and Unknowns — v010

## Risk: health.py ASYNC221 violation when enabling ruff ASYNC rules

- **Severity**: medium
- **Description**: `src/stoat_ferret/api/routers/health.py:96` contains `subprocess.run()` in a file with `async def`. Enabling ruff ASYNC rules (BL-077) will immediately flag this as ASYNC221. This must be handled as part of BL-077 or the CI gate will fail on the existing codebase.
- **Investigation needed**: Confirm no other files in `src/` trigger ASYNC210 (blocking HTTP) or ASYNC230 (blocking file I/O) beyond the known subprocess calls.
- **Current assumption**: Only `health.py:96` will trigger. The recommended fix is converting `_check_ffmpeg()` to use `asyncio.to_thread(subprocess.run, ...)` — a minimal change consistent with v010's async-correctness theme. UNVERIFIED — full ruff ASYNC scan on current codebase not yet run.

## Risk: CI runner timing for 2-second responsiveness threshold (BL-078)

- **Severity**: medium
- **Description**: BL-078's integration test asserts that `GET /api/v1/jobs/{id}` responds within 2 seconds during an active scan. GitHub Actions runners have variable latency, and 2 seconds may be too tight under load, leading to flaky test failures.
- **Investigation needed**: Run the test on GitHub Actions and observe actual response times. If flaky, increase threshold or add retry logic.
- **Current assumption**: 2 seconds is generous enough for a simple JSON GET on an unblocked event loop. UNVERIFIED — no CI runner latency data for this specific test pattern.

## Risk: scan_directory() accumulating callback parameters

- **Severity**: medium
- **Description**: BL-072 makes `ffprobe_video()` async (changing how `scan_directory()` calls it). BL-073 adds a progress callback parameter. BL-074 adds a cancel event parameter. All three modify `scan_directory()` in sequence. The function signature grows and the file-processing loop gains complexity from three separate features.
- **Investigation needed**: Consider whether to pass a context object instead of individual parameters if the signature becomes unwieldy. However, per KISS/YAGNI, individual parameters are fine for 2-3 additions.
- **Current assumption**: Sequential feature implementation (BL-072 first, then BL-073, then BL-074) avoids merge conflicts and each feature cleanly extends the previous one's work. UNVERIFIED — depends on implementation details.

## Risk: executor.py blocking subprocess.run() future impact

- **Severity**: low
- **Description**: `src/stoat_ferret/ffmpeg/executor.py:96` contains a synchronous `subprocess.run()` that is not currently called from an async context. When the render pipeline is eventually wired through the async job queue, this will cause the same event-loop blocking as BL-072. The ruff ASYNC221 rule will not flag this because the function itself is not `async def`.
- **Investigation needed**: None for v010. Flag as tech debt for a future version when render jobs become async.
- **Current assumption**: Render jobs remain synchronous in v010. This is a known future risk, not a current blocker.

## Risk: asyncio.Event creation timing in _AsyncJobEntry

- **Severity**: low
- **Description**: `asyncio.Event` must be created on the event loop thread. If `_AsyncJobEntry` is instantiated before the event loop is running (e.g., during module import or in test setup), the event may not work correctly. Python 3.10 requires the event loop to be running when creating `asyncio.Event`.
- **Investigation needed**: Verify that `_AsyncJobEntry` is only instantiated at job submission time (inside the running event loop), not at module load time.
- **Current assumption**: Job entries are created in `submit()` which runs inside the event loop. UNVERIFIED — need to check test fixtures for edge cases.

## Risk: InMemoryJobQueue test double drift

- **Severity**: low
- **Description**: BL-073 and BL-074 add `set_progress()` and `cancel()` methods to `AsyncioJobQueue`. If an `InMemoryJobQueue` or similar test double exists, it must be updated to match. Failure to update test doubles means tests pass with the real queue but features appear untested via the double.
- **Investigation needed**: Locate all job queue test doubles and verify they implement the same interface.
- **Current assumption**: There is at least one test double that needs updating. UNVERIFIED — exact location not confirmed in Phase 1 research.

## Unknown: Additional ASYNC rule violations beyond health.py

- **Severity**: low
- **Description**: Enabling the full ASYNC rule set (ASYNC210, ASYNC221, ASYNC230) may flag violations beyond the known `health.py` and `probe.py` cases — for example, blocking `open()` calls in async functions (ASYNC230) or blocking HTTP calls (ASYNC210).
- **Investigation needed**: Run `uv run ruff check src/ --select ASYNC` on the current codebase before BL-077 implementation to identify all violations.
- **Current assumption**: Only `health.py:96` and `probe.py:65` will be flagged. `probe.py:65` is fixed by BL-072. UNVERIFIED — no full ASYNC scan has been run.
