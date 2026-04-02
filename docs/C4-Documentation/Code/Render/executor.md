# Render Executor

**Source:** `src/stoat_ferret/render/executor.py`
**Component:** Render Engine

## Purpose

Manages FFmpeg subprocess lifecycle for render jobs: process spawning with asyncio, real-time progress parsing via Rust bindings, hardware encoder detection, graceful cancellation (Windows-safe stdin 'q'), and temporary file tracking for cleanup.

## Public Interface

### Types

- `ProgressCallback = Callable[[str, float], Awaitable[None]]`: Async callback invoked with (job_id, progress_ratio)

### Classes

- `RenderExecutor`: FFmpeg process manager for render jobs
  - `__init__(settings: Settings) -> None`: Initialize with application settings
  - `execute(job: RenderJob, command: list[str], total_duration_us: int) -> bool`: Start FFmpeg subprocess, parse progress from stdout via Rust, enforce timeout (default 3600s), detect hardware vs software encoder, update speed ratio gauge; returns True on success (returncode=0)
  - `cancel(job_id: str) -> bool`: Send 'q' via stdin for graceful FFmpeg shutdown (Windows-safe), wait up to `cancel_grace_seconds` (default 10s), escalate to `process.kill()` if grace period expires; uses `asyncio.shield` to protect `process.wait()`
  - `cancel_all() -> list[str]`: Send 'q' to all active processes, return list of job IDs that received cancel signal
  - `kill_remaining() -> list[str]`: Kill processes that didn't exit after cancel, return list of forcefully killed job IDs
  - `register_temp_file(job_id: str, path: Path) -> None`: Register temporary file for post-job cleanup
  - `cleanup_all_temp_files() -> list[str]`: Clean up all tracked temporary files, return list of cleaned job IDs

## Dependencies

### Internal Dependencies

- `stoat_ferret.render.models.RenderJob`: Job data model
- `stoat_ferret.render.metrics`: Prometheus metrics (render_speed_ratio, render_encoder_active)
- `stoat_ferret.api.settings.Settings`: Configuration (render_timeout_seconds, render_cancel_grace_seconds)

### External Dependencies

- `stoat_ferret_core.parse_ffmpeg_progress`: Rust binding — parse FFmpeg stdout line into `list[ProgressUpdate]`
- `stoat_ferret_core.calculate_progress`: Rust binding — convert `out_time_us` to 0.0-1.0 progress ratio
- `asyncio`: Subprocess management via `asyncio.create_subprocess_exec()`
- `structlog`: Structured logging
- `pathlib.Path`: Temporary file tracking

## Key Implementation Details

### Async Subprocess Management

Uses `asyncio.create_subprocess_exec()` with `stdout=PIPE` and `stdin=PIPE`. Reads stdout line-by-line, passing each line to Rust `parse_ffmpeg_progress()` for extraction of `out_time_us`, `speed`, and `fps` fields.

### Hardware Encoder Detection

Inspects the FFmpeg command for known hardware encoder names:
- **NVENC:** h264_nvenc, hevc_nvenc
- **QSV:** h264_qsv, hevc_qsv
- **AMF:** h264_amf, hevc_amf
- **VideoToolbox:** h264_videotoolbox, hevc_videotoolbox

Sets `render_encoder_active` Prometheus gauge label when a hardware encoder is detected.

### Graceful Cancellation (Windows-Safe)

Instead of `process.terminate()` (which sends SIGTERM on Unix but is unreliable on Windows), sends `q\n` via stdin — FFmpeg's native quit command. This ensures clean file finalization on all platforms. Falls back to `process.kill()` after the grace period.

### Speed Ratio Tracking

Computes `render_speed_ratio = (total_duration_s * progress) / wall_clock_s` using `time.monotonic()` for the wall clock. Updated on each progress callback and exposed via Prometheus gauge.

### Internal Data Structures

- `_active_processes: dict[str, asyncio.subprocess.Process]` — Running subprocesses keyed by job_id
- `_temp_files: dict[str, list[Path]]` — Temporary files per job for cleanup
- `_job_start_times: dict[str, float]` — Process start timestamps for speed ratio
- `_job_durations_us: dict[str, int]` — Total duration per job for progress calculation

## Relationships

- **Used by:** RenderService (execute, cancel, cancel_all, kill_remaining, cleanup_all_temp_files)
- **Uses:** Rust Core (parse_ffmpeg_progress, calculate_progress), Prometheus metrics
