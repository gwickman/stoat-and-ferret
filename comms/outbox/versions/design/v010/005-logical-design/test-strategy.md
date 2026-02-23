# Test Strategy — v010 Async Pipeline & Job Controls

## Theme 1: 01-async-pipeline-fix

### 001-fix-blocking-ffprobe (BL-072)

**Unit tests:**
- Async `ffprobe_video()` returns correct `VideoMetadata` with mocked `asyncio.create_subprocess_exec`
- Timeout behavior: `asyncio.wait_for()` fires reliably at 30s threshold
- Error handling: `FileNotFoundError`, non-zero returncode, JSON parse errors preserved in async version
- Edge cases: empty stdout, stderr content, process killed

**Existing tests requiring update:**
- `tests/test_ffprobe.py` — all tests must become `async def`, mocks must target `asyncio.create_subprocess_exec` instead of `subprocess.run`
- `tests/test_api/test_scan*.py` — ffprobe mocks must be async-compatible (return coroutines)

**System/Golden scenarios:** None — ffprobe output parsing is unchanged.

**Parity tests:** None — no API changes.

**Contract tests:** None — `VideoMetadata` model unchanged.

### 002-async-blocking-ci-gate (BL-077)

**Unit tests:**
- Verify `ruff check` with ASYNC rules flags a test file containing `subprocess.run()` inside `async def`
- Verify `ruff check` passes on the fixed codebase (after BL-072)
- Verify `health.py` passes after converting `_check_ffmpeg()` to use `asyncio.to_thread()`

**Quality gate integration:**
- Ruff ASYNC rules run as part of existing `uv run ruff check src/ tests/` — no CI changes needed
- Verify all three ASYNC rules (221, 210, 230) are active

**System/Golden scenarios:** None.

**Parity tests:** None.

### 003-event-loop-responsiveness-test (BL-078)

**Integration test (this IS the test):**
- Create app with simulated-slow async ffprobe (`asyncio.sleep(0.5)` per file)
- Start scan via `POST /api/v1/scan`
- While scan runs, poll `GET /api/v1/jobs/{id}` using `httpx.AsyncClient`
- Assert response received within 2 seconds via explicit `asyncio.wait_for()`
- Negative validation: if someone regresses to blocking `time.sleep()`, the test must fail (event loop starvation)

**Test markers:** `@pytest.mark.slow`, `@pytest.mark.integration`

**CI considerations:**
- Use generous 2-second threshold (LRN-043 — explicit timeouts for CI variability)
- May need tuning after first CI run on GitHub Actions runners

---

## Theme 2: 02-job-controls

### 001-progress-reporting (BL-073)

**Unit tests:**
- `_AsyncJobEntry` initializes with `progress = None`
- `AsyncioJobQueue.set_progress(job_id, 0.5)` updates entry's progress field
- `set_progress()` with invalid job_id is a no-op or raises appropriate error
- Scan handler calls progress callback after each file with `scanned / total_files`
- Progress callback follows guard pattern: no error if callback is None

**API tests:**
- `GET /api/v1/jobs/{id}` response includes populated `progress` field during active job
- `progress` is `None` for queued jobs, `0.0-1.0` for running jobs, preserved for completed jobs

**System/Golden scenarios:**
- End-to-end scan of multi-file directory shows progress incrementing from 0.0 to 1.0

**Test double updates:**
- `InMemoryJobQueue` (if present in test doubles) needs `set_progress()` stub

**Contract tests:**
- `JobStatusResponse` with `progress` field round-trips correctly via Pydantic

### 002-job-cancellation (BL-074)

**Unit tests:**
- `_AsyncJobEntry` initializes with unset `cancel_event`
- `AsyncioJobQueue.cancel(job_id)` sets the cancel event
- `cancel()` with invalid job_id returns appropriate error
- Scan handler breaks file loop when `cancel_event.is_set()`
- Cancelled scan returns partial results (files scanned before cancellation)
- Cancelled job has `status = CANCELLED`
- `JobStatus.CANCELLED` enum value exists and serializes correctly

**API tests:**
- `POST /api/v1/jobs/{id}/cancel` returns 200 with updated status
- `POST /api/v1/jobs/{id}/cancel` for non-existent job returns 404
- `POST /api/v1/jobs/{id}/cancel` for already-completed job returns appropriate error
- `GET /api/v1/jobs/{id}` shows `status: cancelled` and partial `result` after cancellation

**Frontend tests (vitest):**
- Cancel button is enabled during active scan
- Cancel button calls `POST /api/v1/jobs/{id}/cancel`
- UI updates to reflect cancelled state after successful cancel

**System/Golden scenarios:**
- End-to-end: start scan, cancel mid-way, verify partial results preserved and status is cancelled

**Test double updates:**
- `InMemoryJobQueue` needs `cancel()` stub

**End-to-end acceptance (bug fix pattern per task 3a):**
- Not a bug fix — new feature. Standard AC applies.

---

## Cross-Cutting Test Concerns

### Async Test Infrastructure
- All new tests in Theme 1 and Theme 2 that test async functions must use `async def` test functions with `pytest-asyncio` (asyncio_mode = "auto" already configured)
- Mock targets shift from `subprocess.run` to `asyncio.create_subprocess_exec` after BL-072

### Test Ordering
- BL-072 tests must pass before BL-077 tests (ruff ASYNC rules depend on fixed code)
- BL-078 integration test validates BL-072 fix
- BL-073 tests should run before BL-074 tests (cancellation builds on progress infrastructure)

### CI Impact
- BL-077 adds ruff ASYNC rules — may surface pre-existing violations beyond `health.py`
- BL-078 adds a slow integration test — monitor CI time impact
- No new CI jobs or workflows needed — all tests run in existing pytest and ruff steps
