# Risk Assessment — v010 Async Pipeline & Job Controls

## Risk: health.py ASYNC221 violation when enabling ruff ASYNC rules

- **Original severity**: medium
- **Category**: Investigate now
- **Investigation**: Grep for all `subprocess.run|call|check_output|Popen` in `src/`, cross-referenced with files containing `async def`. Also searched for ASYNC210 (blocking HTTP) and ASYNC230 (blocking file I/O) violations.
- **Finding**: Confirmed — only `health.py:96` triggers ASYNC221. Zero ASYNC210 violations (no `requests` library usage). Zero ASYNC230 violations (no blocking `open()` in async files). `executor.py:96` has `subprocess.run()` but no `async def` in the file, so ruff won't flag it.
- **Resolution**: Design confirmed as-is. Feature 002 (BL-077) handles only the `health.py` case by converting `_check_ffmpeg()` to use `asyncio.to_thread(subprocess.run, ...)`. No additional violations to handle.
- **Affected themes/features**: Theme 1 / 002-async-blocking-ci-gate

## Risk: CI runner timing for 2-second responsiveness threshold (BL-078)

- **Original severity**: medium
- **Category**: Accept with mitigation
- **Investigation**: Cannot empirically test CI runner timing without a running test. The 2-second threshold is for a simple JSON GET on an unblocked event loop — network latency is irrelevant since it's in-process via `httpx.AsyncClient`.
- **Finding**: The test uses `httpx.AsyncClient` with ASGI transport (in-process), so there is no real network latency. The 2-second threshold is extremely generous for an in-process async JSON response (typically <10ms). The real risk is only if the event loop is blocked, which is exactly what the test detects.
- **Resolution**: Keep 2-second threshold. Add mitigation: if the test is flaky on CI, increase to 5 seconds as a first step. Document in the test docstring that the threshold is intentionally generous and what values suggest a real failure vs. CI noise.
- **Affected themes/features**: Theme 1 / 003-event-loop-responsiveness-test

## Risk: scan_directory() accumulating callback parameters

- **Original severity**: medium
- **Category**: Accept with mitigation
- **Investigation**: Reviewed the scan_directory() callsite pattern. BL-072 makes ffprobe async (function signature change). BL-073 adds `progress_callback`. BL-074 adds `cancel_event`. Total: 2 new parameters.
- **Finding**: Two new parameters is well within KISS/YAGNI bounds. Python supports keyword-only arguments (`*`) which keeps callsites clean. A context object would be premature abstraction for 2 parameters. The sequential feature implementation (072 → 073 → 074) means each feature cleanly extends the previous signature.
- **Resolution**: No design change. Use keyword-only parameters for `progress_callback` and `cancel_event` with `None` defaults. If a future version adds a third callback, refactor to a context object then.
- **Affected themes/features**: Theme 2 / 001-progress-reporting, 002-job-cancellation

## Risk: executor.py blocking subprocess.run() future impact

- **Original severity**: low
- **Category**: Accept with mitigation (future tech debt)
- **Investigation**: Confirmed `executor.py` has zero `async def` functions. Ruff ASYNC221 will not flag it. The file is synchronous-only today.
- **Finding**: This is a known future risk for when render jobs are wired through the async job queue. Not a v010 concern.
- **Resolution**: No design change for v010. Documented as tech debt. When render pipeline becomes async, `executor.py:96` will need the same `asyncio.create_subprocess_exec()` treatment as `probe.py`.
- **Affected themes/features**: None (future version)

## Risk: asyncio.Event creation timing in _AsyncJobEntry

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Grep for all `_AsyncJobEntry(` instantiation sites. Found single site at `queue.py:323` inside `async def submit()`.
- **Finding**: RESOLVED — `_AsyncJobEntry` is only created inside `async def submit()`, guaranteeing the event loop is running. Python 3.10's `asyncio.Event()` requirement for a running loop is satisfied. No edge cases in test fixtures — test fixtures use `InMemoryJobQueue` which creates `_JobEntry` (not `_AsyncJobEntry`).
- **Resolution**: No design change. The `cancel_event: asyncio.Event` field can be safely added to `_AsyncJobEntry` as a `field(default_factory=asyncio.Event)` dataclass field.
- **Affected themes/features**: Theme 2 / 002-job-cancellation

## Risk: InMemoryJobQueue test double drift

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Grep for all `InMemoryJobQueue` usage in tests (8+ test files, 30+ usages). Read the `InMemoryJobQueue` class at `queue.py:114` and the `AsyncJobQueue` Protocol at `queue.py:52`.
- **Finding**: `InMemoryJobQueue` is a separate class using `_JobEntry` (not `_AsyncJobEntry`). It does NOT formally implement `AsyncJobQueue` Protocol. Adding `set_progress()`/`cancel()` to `AsyncioJobQueue` won't break `InMemoryJobQueue`. However, the `AsyncJobQueue` Protocol should be updated if these become part of the public interface, and `InMemoryJobQueue` should add no-op stubs for protocol compliance.
- **Resolution**: Design update — BL-073 and BL-074 implementation plans should include: (1) update `AsyncJobQueue` Protocol with `set_progress()` and `cancel()` methods, (2) add no-op implementations to `InMemoryJobQueue`. This prevents test double drift. Add to test strategy.
- **Affected themes/features**: Theme 2 / 001-progress-reporting, 002-job-cancellation

## Unknown: Additional ASYNC rule violations beyond health.py

- **Original severity**: low
- **Category**: Investigate now
- **Investigation**: Full grep for ASYNC210, ASYNC221, ASYNC230 trigger patterns across all `src/` files with `async def`.
- **Finding**: RESOLVED — zero additional violations. No blocking HTTP calls, no blocking file I/O, no additional blocking subprocess calls in async files. The unknown is fully resolved.
- **Resolution**: No design change needed. The ASYNC rule enablement in BL-077 is clean.
- **Affected themes/features**: Theme 1 / 002-async-blocking-ci-gate
