# Implementation Plan: fix-blocking-ffprobe

## Overview

Convert `ffprobe_video()` from synchronous `subprocess.run()` to `asyncio.create_subprocess_exec()` with `communicate()`. Update the sole caller `scan_directory()` to await the call. Migrate all ffprobe and scan tests to handle the async function.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/ffmpeg/probe.py` | Modify | Convert ffprobe_video() to async def, replace subprocess.run() with asyncio.create_subprocess_exec() |
| `src/stoat_ferret/api/services/scan.py` | Modify | Add await to ffprobe_video() call in scan_directory() |
| `tests/test_ffprobe.py` | Modify | Convert all test functions to async def, mock asyncio.create_subprocess_exec instead of subprocess.run |
| `tests/test_api/test_videos.py` | Modify | Update ffprobe mocks to async-compatible (return coroutines) |
| `tests/test_api/test_jobs.py` | Modify | Update ffprobe mocks to async-compatible if any scan-related tests reference ffprobe |
| `tests/test_api/test_websocket_broadcasts.py` | Modify | Update ffprobe mocks to async-compatible if any scan-related tests reference ffprobe |

## Test Files

`tests/test_ffprobe.py tests/test_api/test_videos.py tests/test_api/test_jobs.py tests/test_api/test_websocket_broadcasts.py`

## Implementation Stages

### Stage 1: Convert ffprobe_video() to async

1. In `src/stoat_ferret/ffmpeg/probe.py`:
   - Add `import asyncio` at top
   - Change `def ffprobe_video(` to `async def ffprobe_video(`
   - Replace `subprocess.run(...)` with:
     ```python
     proc = await asyncio.create_subprocess_exec(
         ffprobe_path, "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path),
         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
     )
     stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
     ```
   - Update error handling to match async equivalents (TimeoutError from asyncio.wait_for, process returncode check)
   - Preserve all existing error paths (FileNotFoundError, returncode errors, JSON parse errors)

2. In `src/stoat_ferret/api/services/scan.py`:
   - Change `metadata = ffprobe_video(...)` to `metadata = await ffprobe_video(...)`

**Verification:**
```bash
uv run ruff check src/stoat_ferret/ffmpeg/probe.py src/stoat_ferret/api/services/scan.py
uv run mypy src/stoat_ferret/ffmpeg/probe.py src/stoat_ferret/api/services/scan.py
```

### Stage 2: Migrate tests

1. In `tests/test_ffprobe.py`:
   - Convert all test functions to `async def`
   - Replace mocks targeting `subprocess.run` with mocks targeting `asyncio.create_subprocess_exec`
   - Create async mock process object with `communicate()` coroutine returning `(stdout, stderr)`
   - Update timeout tests to expect `asyncio.TimeoutError` (use `asyncio.TimeoutError` not `builtins.TimeoutError` for Python 3.10 compatibility)

2. In `tests/test_api/test_videos.py`, `tests/test_api/test_jobs.py`, `tests/test_api/test_websocket_broadcasts.py`:
   - Update any ffprobe_video mocks to return coroutines (use `AsyncMock` or async wrapper)
   - Only modify files that directly mock or reference ffprobe_video

**Verification:**
```bash
uv run pytest tests/test_ffprobe.py tests/test_api/test_videos.py tests/test_api/test_jobs.py tests/test_api/test_websocket_broadcasts.py -v
```

### Stage 3: Full quality gates

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Test Infrastructure Updates

- All ffprobe tests become async (pytest-asyncio with asyncio_mode = "auto" handles this)
- Mock target changes from `subprocess.run` to `asyncio.create_subprocess_exec`
- Need async mock process helper with `communicate()`, `returncode`, `kill()` methods

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Python 3.10 `asyncio.TimeoutError` vs `builtins.TimeoutError` — use `asyncio.TimeoutError` explicitly. See `006-critical-thinking/risk-assessment.md`
- Windows `ProactorEventLoop` requirement — default since Python 3.8, no action needed

## Commit Message

```
feat: convert ffprobe_video to async subprocess execution (BL-072)
```