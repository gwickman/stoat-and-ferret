# Impact Analysis — v010

## Dependencies (Code/Tools/Configs Affected)

### BL-072: Async ffprobe

| Component | File | Change |
|-----------|------|--------|
| ffprobe_video() | `src/stoat_ferret/ffmpeg/probe.py` | Convert to `async def`, use `asyncio.create_subprocess_exec()` |
| scan_directory() | `src/stoat_ferret/api/services/scan.py:154` | `await ffprobe_video()` (already in async context) |
| ffprobe tests | `tests/test_ffprobe.py` | Update to async tests, mock `asyncio.create_subprocess_exec` |
| scan tests | `tests/test_api/test_scan*.py` | Update ffprobe mocks to async |

**Does NOT affect:** `executor.py:96` (sync, not in async context), `health.py:96` (low-risk 5s call).

### BL-073: Progress Reporting

| Component | File | Change |
|-----------|------|--------|
| _AsyncJobEntry | `src/stoat_ferret/jobs/queue.py:267` | Add `progress: float | None = None` field |
| AsyncioJobQueue | `src/stoat_ferret/jobs/queue.py:279` | Add `set_progress(job_id, value)` method |
| scan_directory() | `src/stoat_ferret/api/services/scan.py` | Accept progress callback, call after each file |
| make_scan_handler() | `src/stoat_ferret/api/services/scan.py:55` | Pass progress callback from queue to scan |
| get_job_status | `src/stoat_ferret/api/routers/jobs.py` | Pass `progress` to `JobStatusResponse` |
| InMemoryJobQueue | `tests/test_doubles/` | Add `set_progress()` stub |
| Frontend | No changes — already reads `progress` field |

### BL-074: Job Cancellation

| Component | File | Change |
|-----------|------|--------|
| _AsyncJobEntry | `src/stoat_ferret/jobs/queue.py:267` | Add `cancel_event: asyncio.Event` field |
| AsyncioJobQueue | `src/stoat_ferret/jobs/queue.py:279` | Add `cancel(job_id)` method |
| JobStatus enum | `src/stoat_ferret/jobs/queue.py` | Add `CANCELLED` value |
| scan_directory() | `src/stoat_ferret/api/services/scan.py` | Accept cancel event, check in file loop |
| Cancel endpoint | `src/stoat_ferret/api/routers/jobs.py` | New `POST /api/v1/jobs/{id}/cancel` |
| ScanModal | `gui/src/components/ScanModal.tsx` | Enable cancel button, call cancel endpoint |
| InMemoryJobQueue | `tests/test_doubles/` | Add `cancel()` stub |

### BL-077: Ruff ASYNC Rules

| Component | File | Change |
|-----------|------|--------|
| Ruff config | `pyproject.toml:53` | Add `"ASYNC"` to select list |
| No other changes needed | — | Existing `ruff check` CI step handles it |

### BL-078: Responsiveness Integration Test

| Component | File | Change |
|-----------|------|--------|
| New test file | `tests/test_integration/test_event_loop_responsiveness.py` | New integration test |
| pytest markers | `pyproject.toml` | Consider adding `integration` marker |
| conftest | `tests/conftest.py` or new conftest | Fixtures for slow-ffprobe app |

## Breaking Changes

**None identified.** All changes are additive:
- `ffprobe_video()` signature changes from sync to async — but only called from one async location
- New fields on `_AsyncJobEntry` have defaults — no existing code breaks
- New API endpoint — additive, no existing endpoints change
- New enum value `CANCELLED` — additive
- Ruff ASYNC rules may flag `health.py:96` — need `# noqa: ASYNC221` or convert to async

**Potential flag:** `health.py:96` has `subprocess.run()` in a file with `async def`. After enabling ASYNC rules, this will trigger ASYNC221. Options:
1. Add `# noqa: ASYNC221` comment (quick, the 5s health check is low-risk)
2. Convert to `asyncio.to_thread(subprocess.run, ...)` (proper fix)
3. Move `_check_ffmpeg()` to a non-async module (refactor)

**Recommendation:** Option 2 — minimal change, consistent with v010's async-correctness theme.

## Test Infrastructure Needs

### New Tests Required

| BL | Test Type | Description |
|----|-----------|-------------|
| BL-072 | Unit | Async ffprobe with mocked `asyncio.create_subprocess_exec` |
| BL-072 | Unit | Timeout behavior with `asyncio.wait_for` |
| BL-073 | Unit | `set_progress()` updates entry and is retrievable |
| BL-073 | Unit | Scan handler reports progress after each file |
| BL-073 | API | `GET /jobs/{id}` returns populated progress field |
| BL-074 | Unit | `cancel()` sets event, scan handler breaks on flag |
| BL-074 | Unit | Cancelled job has status CANCELLED with partial results |
| BL-074 | API | `POST /jobs/{id}/cancel` endpoint returns correct status |
| BL-074 | Frontend | Cancel button calls endpoint (vitest) |
| BL-077 | CI | Ruff ASYNC rules pass on fixed codebase |
| BL-078 | Integration | Event-loop responsiveness during scan |

### Existing Tests Requiring Update

| Test File | Change Reason |
|-----------|--------------|
| `tests/test_ffprobe.py` | ffprobe_video is now async |
| `tests/test_api/test_scan*.py` | ffprobe mocks must be async |
| `tests/test_jobs/test_asyncio_queue.py` | New fields on entry, new methods |
| `tests/test_doubles/` | InMemoryJobQueue needs progress/cancel stubs |

## Documentation Updates Required

| Document | Update |
|----------|--------|
| `docs/design/05-api-specification.md` | Add `POST /api/v1/jobs/{id}/cancel` endpoint |
| `stubs/stoat_ferret_core/` | No change (Rust bindings unaffected) |
| AGENTS.md | No change |
