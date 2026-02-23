# Investigation Log — v010 Critical Thinking

## Investigation 1: ASYNC Rule Violations Beyond health.py and probe.py

**Hypothesis:** Only `health.py:96` and `probe.py:65` contain blocking subprocess calls in files with `async def`. No other ASYNC210/230 violations exist in `src/`.

**Method:** Grep for all `subprocess.(run|call|check_output|Popen)` in `src/`, cross-reference with files containing `async def`.

**Results:**

Blocking subprocess calls found in 3 files:
- `src/stoat_ferret/ffmpeg/executor.py:96` — `subprocess.run()`
- `src/stoat_ferret/api/routers/health.py:96` — `subprocess.run()`
- `src/stoat_ferret/ffmpeg/probe.py:65` — `subprocess.run()`

Files containing `async def` (16 files):
- `api/routers/projects.py`, `api/services/scan.py`, `api/app.py`, `db/project_repository.py`, `api/routers/ws.py`, `db/schema.py`, `api/routers/effects.py`, `db/clip_repository.py`, `db/async_repository.py`, `api/routers/videos.py`, `api/websocket/manager.py`, `jobs/queue.py`, `api/routers/jobs.py`, `api/routers/health.py`, `api/middleware/metrics.py`, `api/middleware/correlation.py`

**Cross-reference:**
- `executor.py` has NO `async def` — ruff ASYNC221 will NOT flag it (confirmed)
- `health.py` has `async def` AND `subprocess.run()` — ASYNC221 WILL fire (confirmed)
- `probe.py` has no `async def` of its own but is called from async context — ruff ASYNC221 will NOT flag it directly (it flags based on file-level `async def`, not caller context). BL-072 fixes this anyway.

**Additional ASYNC rule checks:**
- ASYNC210 (blocking HTTP): Grep for `requests.(get|post|put|delete)`, `urllib.request`, `http.client` — **zero matches** in `src/`
- ASYNC230 (blocking file I/O): Grep for `open(` in `src/stoat_ferret/` — **zero matches** (no synchronous file opens in async code paths)

**Conclusion:** Task 005's assumption CONFIRMED. Only `health.py:96` triggers ASYNC221 beyond the BL-072 target. No ASYNC210 or ASYNC230 violations exist. The design for BL-077 (feature 002) only needs to handle the `health.py` case.

---

## Investigation 2: asyncio.Event Creation Timing in _AsyncJobEntry

**Hypothesis:** `_AsyncJobEntry` is only instantiated inside `submit()` which runs on the event loop thread, so `asyncio.Event` creation will be safe when added for BL-074.

**Method:** Grep for all `_AsyncJobEntry(` instantiation sites, read surrounding context.

**Results:**

Single instantiation site found at `src/stoat_ferret/jobs/queue.py:323`:
```python
async def submit(self, job_type: str, payload: dict[str, Any]) -> str:
    job_id = str(uuid.uuid4())
    entry = _AsyncJobEntry(job_id=job_id, job_type=job_type, payload=payload)
    self._jobs[job_id] = entry
    await self._queue.put(job_id)
```

The `submit()` method is `async def`, meaning it MUST run on the event loop thread. `_AsyncJobEntry` is created inline within this coroutine.

**Note on Python 3.10 compatibility:** In Python 3.10, `asyncio.Event()` requires a running event loop (deprecated parameter `loop` was removed). Since `submit()` is async, the loop is always running when `_AsyncJobEntry` is created. This is safe.

**Note on current _AsyncJobEntry:** The current dataclass has NO `asyncio.Event` field — it's a plain dataclass with `job_id`, `job_type`, `payload`, `status`, `result`, `error`. The `cancel_event` will be added by BL-074.

**Conclusion:** Risk RESOLVED. `_AsyncJobEntry` is only created inside `async def submit()`, guaranteeing the event loop is running. Adding `asyncio.Event()` as a default field in the dataclass is safe because the dataclass `__init__` runs within the async context of `submit()`.

---

## Investigation 3: InMemoryJobQueue Test Double Scope

**Hypothesis:** There is at least one test double that needs updating when `set_progress()` and `cancel()` are added.

**Method:** Grep for `InMemoryJobQueue` imports and usage across `tests/`.

**Results:**

`InMemoryJobQueue` is imported and used in **8 test files**:
- `tests/test_orphaned_settings.py` (3 usages)
- `tests/test_ws_endpoint.py` (1 usage)
- `tests/test_security/conftest.py` (3 usages)
- `tests/test_api/test_gui_static.py` (2 usages)
- `tests/test_api/test_jobs.py` (1 usage)
- `tests/test_api/conftest.py` (3 usages)
- `tests/test_api/test_spa_routing.py` (2 usages)
- `tests/test_api/test_websocket_broadcasts.py` (2 usages)
- `tests/test_blackbox/conftest.py` (3 usages)
- `tests/test_doubles/test_inmemory_job_queue.py` (11 usages — dedicated test file)

**Key finding:** `InMemoryJobQueue` (at `queue.py:114`) is a SEPARATE class from `AsyncioJobQueue` (at `queue.py:279`). It uses `_JobEntry` (not `_AsyncJobEntry`) and has its own independent storage. It does NOT share a formal Protocol with `AsyncioJobQueue` — the `AsyncJobQueue` Protocol defines only `submit`, `get_status`, `get_result`.

**Impact analysis:**
- BL-073 adds `set_progress()` to `AsyncioJobQueue` — `InMemoryJobQueue` does NOT need it unless the Protocol is extended
- BL-074 adds `cancel()` to `AsyncioJobQueue` — same situation
- However, if tests using `InMemoryJobQueue` need to exercise progress/cancel behavior, stub methods will be needed
- The `AsyncJobQueue` Protocol (line 52) will need updating if `set_progress`/`cancel` become part of the public interface

**Conclusion:** Risk PARTIALLY RESOLVED. `InMemoryJobQueue` is a separate implementation, not a subclass. It won't break when `AsyncioJobQueue` gets new methods. However, the `AsyncJobQueue` Protocol needs updating, and `InMemoryJobQueue` should implement the new methods as no-ops to maintain protocol compliance. This is a design consideration for BL-073/BL-074 implementation.

---

## Investigation 4: executor.py Blocking Subprocess — Future Risk

**Hypothesis:** `executor.py:96` has `subprocess.run()` but is not in an async file, so ruff won't catch it.

**Method:** Grep for `async def` in `executor.py`.

**Results:** Zero `async def` in `executor.py`. Confirmed: ruff ASYNC221 will not flag this file.

**Conclusion:** Confirmed as documented. This is future tech debt, not a v010 issue. When render jobs are wired through the async job queue, this will need conversion. No design change needed for v010.

---

## Investigation 5: Backlog Coverage Validation

**Method:** Cross-reference logical design themes/features with backlog items from `002-backlog/backlog-details.md`.

**Results:**

| Backlog Item | Theme | Feature | Covered |
|---|---|---|---|
| BL-072 (P0) | 01-async-pipeline-fix | 001-fix-blocking-ffprobe | Yes |
| BL-077 (P2) | 01-async-pipeline-fix | 002-async-blocking-ci-gate | Yes |
| BL-078 (P2) | 01-async-pipeline-fix | 003-event-loop-responsiveness-test | Yes |
| BL-073 (P1) | 02-job-controls | 001-progress-reporting | Yes |
| BL-074 (P1) | 02-job-controls | 002-job-cancellation | Yes |

**Conclusion:** All 5 backlog items are covered. No deferrals. No missing items.

---

## Investigation 6: Persistence Coherence Check

**Method:** Check for Task 004 `persistence-analysis.md`.

**Results:** No `persistence-analysis.md` exists in `004-research/`. v010 introduces no new persistent storage — all changes are in-memory (job queue state, asyncio.Event, progress float). This is appropriate: job state is ephemeral and resets on server restart.

**Conclusion:** No persistence concerns for v010. No blocking risks from unverified storage APIs.
