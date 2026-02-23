# Codebase Patterns — v010 Research

## 1. ffprobe_video() — Current Blocking Implementation

**File:** `src/stoat_ferret/ffmpeg/probe.py:45-94`

```python
def ffprobe_video(path: str, ...) -> VideoMetadata:
    result = subprocess.run(
        [ffprobe_path, "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, timeout=30, check=False,
    )
```

- Synchronous function called from async `scan_directory()` at `src/stoat_ferret/api/services/scan.py:154`
- 30-second timeout per file — blocks event loop entirely during each call
- Returns `VideoMetadata` dataclass; error handling catches `FileNotFoundError`, `TimeoutExpired`, returncode errors, JSON parse errors

## 2. All Blocking subprocess.run() Calls in src/

| File | Line | Timeout | Contains `async def`? | Risk |
|------|------|---------|-----------------------|------|
| `ffmpeg/probe.py` | 65 | 30s | No (but called from async) | **HIGH** — blocks event loop via scan handler |
| `ffmpeg/executor.py` | 96 | configurable | No | LOW — not yet used from async context |
| `api/routers/health.py` | 96 | 5s | YES | MEDIUM — blocks readiness endpoint |

No `time.sleep()` calls found in `src/`.

## 3. AsyncioJobQueue — Foundation Pattern

**File:** `src/stoat_ferret/jobs/queue.py:279-429`

**Entry model** (`_AsyncJobEntry`, line 267):
- Fields: `job_id`, `job_type`, `payload`, `status`, `result`, `error`
- **No progress field** — must be added for BL-073
- **No cancellation flag** — must be added for BL-074

**Handler registration** (line 303):
```python
def register_handler(self, job_type: str, handler: JobHandler) -> None:
    self._handlers[job_type] = handler
```

**Job processing** (line 367):
```python
async def process_jobs(self) -> None:
    while True:
        job_id = await self._queue.get()
        entry.status = JobStatus.RUNNING
        result = await asyncio.wait_for(handler(...), timeout=self._timeout)
```

**Key:** Uses stdlib `asyncio.Queue` with single worker coroutine. No external dependencies (LRN-010 confirmed).

## 4. Scan Handler — make_scan_handler() Factory

**File:** `src/stoat_ferret/api/services/scan.py:55-103`

```python
def make_scan_handler(repository, ws_manager=None) -> JobHandler:
    async def handler(job_type: str, payload: dict) -> Any:
        if ws_manager:
            await ws_manager.broadcast(build_event(EventType.SCAN_STARTED, ...))
        result = await scan_directory(repository, path, recursive)
        if ws_manager:
            await ws_manager.broadcast(build_event(EventType.SCAN_COMPLETED, ...))
        return result.model_dump()
```

**Guard pattern** (LRN-049): `if ws_manager:` before every broadcast — progress callbacks should follow same pattern.

**File loop** (`scan_directory`, line 140):
```python
for file_path in root.glob(pattern):
    if not file_path.is_file(): continue
    if file_path.suffix.lower() not in VIDEO_EXTENSIONS: continue
    scanned += 1
    metadata = ffprobe_video(str_path)  # <-- blocking call
```

**Cancellation insertion point:** Between `scanned += 1` and `ffprobe_video()` — check cancellation flag here.

**Progress insertion point:** After each file processed, call `set_progress(job_id, scanned / total_files)`.

## 5. Job Status API — Schema Already Has Progress Field

**File:** `src/stoat_ferret/api/schemas/job.py:19-30`

```python
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float | None = None  # <-- already exists, never populated
    result: Any = None
    error: str | None = None
```

**Endpoint:** `src/stoat_ferret/api/routers/jobs.py:12-43` — `GET /api/v1/jobs/{job_id}`
- Currently maps `result.status.value` but **does not pass progress** to response.
- Fix: add `progress=result.progress` in the response construction.

## 6. Frontend ScanModal — Already Reads Progress

**File:** `gui/src/components/ScanModal.tsx`

- Polls `/api/v1/jobs/{job_id}` every 1000ms (line 72)
- Sets `progress` from `status.progress` (line 80)
- Renders progress bar with `width: ${(progress ?? 0) * 100}%` (line 157)
- Cancel button **disabled during scanning** (line 184) — needs enabling + API call

## 7. create_app() — Current DI Surface

**File:** `src/stoat_ferret/api/app.py:116-219`

**9 kwargs:** `video_repository`, `project_repository`, `clip_repository`, `job_queue`, `ws_manager`, `effect_registry`, `ffmpeg_executor`, `audit_logger`, `gui_static_path`

v010 does NOT need new kwargs:
- Progress: internal to job queue (set_progress method)
- Cancellation: internal to job queue (cancel method + event)
- Async ffprobe: changes function signature, not DI wiring

## 8. Quality Gates — Where to Add ASYNC Rules

**File:** `pyproject.toml:52-53`

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

Add `"ASYNC"` to enable the flake8-async rule set. This activates:
- ASYNC221: `subprocess.run/call/check_output` in async functions
- ASYNC210: blocking HTTP calls in async functions
- ASYNC230: blocking `open()` in async functions

**CI integration:** Already runs `uv run ruff check src/ tests/` — no CI changes needed.
