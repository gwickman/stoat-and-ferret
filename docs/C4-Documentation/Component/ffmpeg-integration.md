# FFmpeg Integration

## Purpose

The FFmpeg Integration component abstracts all interaction with the FFmpeg and ffprobe processes. It provides protocol-based executors (synchronous and asynchronous) that hide process spawning details from callers, wraps executors with structured logging and Prometheus metrics for production observability, defines Prometheus metrics specific to FFmpeg execution as module-level singletons (LRN-137), and provides an async function for extracting video metadata from ffprobe.

## Responsibilities

- Execute FFmpeg commands as subprocesses (synchronous and asynchronous) and return structured results (stdout, stderr, exit code, duration)
- Provide async FFmpeg execution with real-time progress tracking and cooperative cancellation for long-running transcoding
- Record and replay FFmpeg interactions for deterministic testing via record/replay executors
- Wrap any executor implementation with structured logging and Prometheus metrics (decorator pattern)
- Define the Prometheus metrics namespace for FFmpeg observability: execution count, duration histogram, and active process gauge
- Extract video metadata from ffprobe output: duration, resolution, frame rate, codecs, file size
- Parse ffprobe JSON with comprehensive error handling: missing executable, timeout, non-zero exit code, malformed output, audio-only files

## Interfaces

### Provided Interfaces

**FFmpegExecutor (protocol)**
- `run(args: list[str], *, stdin: bytes | None, timeout: float | None) -> ExecutionResult` — Execute FFmpeg with given arguments

**ExecutionResult (dataclass)**
- `returncode: int`
- `stdout: bytes`
- `stderr: bytes`
- `command: list[str]`
- `duration_seconds: float`

**Implementations**
- `RealFFmpegExecutor` — Wraps `subprocess.run()`; production implementation
- `RecordingFFmpegExecutor` — Delegates to wrapped executor and records all interactions to a JSON file
- `FakeFFmpegExecutor` — Replays recorded interactions in order; supports strict mode for argument matching

**AsyncFFmpegExecutor (protocol)**
- `async run(args: list[str], *, progress_callback: ProgressCallback | None, cancel_event: asyncio.Event | None) -> ExecutionResult` — Execute FFmpeg asynchronously with optional progress tracking and cooperative cancellation

**ProgressInfo (dataclass)**
- `out_time_us: int` — Current output time in microseconds
- `speed: float` — Encoding speed multiplier
- `fps: float` — Current encoding FPS

**Implementations (async)**
- `RealAsyncFFmpegExecutor` — Uses `asyncio.create_subprocess_exec()`; concurrent stderr reading task; progress callback invoked per progress block; SIGTERM on cancellation
- `FakeAsyncFFmpegExecutor` — Test double with call recording

**ObservableFFmpegExecutor**
- `__init__(wrapped: FFmpegExecutor) -> None`
- `run(args, *, stdin, timeout, correlation_id: str | None) -> ExecutionResult` — Delegates to wrapped executor; emits `ffmpeg_execution_started` and `ffmpeg_execution_completed` / `ffmpeg_execution_failed` structlog events; updates all three Prometheus metrics

**Prometheus Metrics (module-level constants)**
- `ffmpeg_executions_total` — Counter labeled by `status` ("success" or "failure")
- `ffmpeg_execution_duration_seconds` — Histogram with buckets from 0.1s to 300s
- `ffmpeg_active_processes` — Gauge for currently running FFmpeg processes

**ffprobe_video (async function)**
- `ffprobe_video(path: str, ffprobe_path: str) -> VideoMetadata` — Run ffprobe on the given video file and return structured metadata

**VideoMetadata (dataclass)**
- `duration_seconds: float`
- `width: int`
- `height: int`
- `frame_rate_numerator: int`
- `frame_rate_denominator: int`
- `video_codec: str`
- `audio_codec: str | None`
- `file_size: int`
- `frame_rate` property → `tuple[int, int]`
- `duration_frames` property → `int` (computed from duration and frame rate)

### Required Interfaces

None — the component depends only on Python standard library modules (`subprocess`, `asyncio`, `json`, `pathlib`, `time`).

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Executor | `src/stoat_ferret/ffmpeg/executor.py` | `FFmpegExecutor` protocol; `RealFFmpegExecutor`, `RecordingFFmpegExecutor`, `FakeFFmpegExecutor`; `ExecutionResult` dataclass |
| Async Executor | `src/stoat_ferret/ffmpeg/async_executor.py` | `AsyncFFmpegExecutor` protocol; `RealAsyncFFmpegExecutor` with progress tracking and cooperative cancellation; `FakeAsyncFFmpegExecutor` for testing; `ProgressInfo` dataclass |
| Observable | `src/stoat_ferret/ffmpeg/observable.py` | `ObservableFFmpegExecutor` — decorator that adds structlog events and Prometheus metrics to any executor |
| Metrics | `src/stoat_ferret/ffmpeg/metrics.py` | Prometheus metric definitions as module-level singletons (LRN-137): `ffmpeg_executions_total`, `ffmpeg_execution_duration_seconds`, `ffmpeg_active_processes` |
| Probe | `src/stoat_ferret/ffmpeg/probe.py` | `ffprobe_video()` async function; `VideoMetadata` dataclass; `FFprobeError` exception; `_parse_ffprobe_output()` internal parser |

## Key Behaviors

**Protocol-Based Abstraction:** `FFmpegExecutor` is a structural `Protocol`, not an abstract class. Any object with a compatible `run()` signature satisfies the protocol, enabling wrapping without inheritance.

**Record/Replay Testing:** `RecordingFFmpegExecutor` wraps any executor and serializes all calls (args, stdin, stdout, stderr as hex) to a JSON file. `FakeFFmpegExecutor.from_file()` loads that file and replays responses in order, providing deterministic FFmpeg behavior in tests without running actual FFmpeg.

**Observable Decorator Pattern:** `ObservableFFmpegExecutor` uses a try/finally block to guarantee the `ffmpeg_active_processes` gauge is decremented even when the wrapped executor raises an exception. The `ffmpeg_executions_total` counter is always incremented, with the label set to "failure" on exception.

**Frame Rate as Rational Number:** `ffprobe_video()` parses the `r_frame_rate` field as "numerator/denominator" to preserve exact representation for NTSC rates (30000/1001, 60000/1001). The `VideoMetadata.duration_frames` property computes frame count via `int(duration_seconds * numerator / denominator)`.

**Async Subprocess with Timeout:** `ffprobe_video()` uses `asyncio.create_subprocess_exec()` and wraps `proc.communicate()` in `asyncio.wait_for(..., timeout=30)`. On timeout, it kills the process before re-raising as `FFprobeError` to avoid zombie processes.

**Async FFmpeg Execution:** `RealAsyncFFmpegExecutor` uses concurrent tasks for stderr reading, cancellation monitoring, and the main process. Progress callbacks are invoked after each progress block (~1s intervals). Cooperative cancellation via `asyncio.Event` sends SIGTERM to the process. Duration is measured with `time.monotonic()` for immunity to system clock changes.

**Metric Singleton Module Pattern (LRN-137):** All Prometheus metrics for FFmpeg are defined as module-level singletons in `metrics.py`. Service files import specific metric objects rather than creating them inline, providing a single inventory of all instrumentation points and avoiding import-time side effects in service code.

## Inter-Component Relationships

```
API Gateway (ThumbnailService)
    |-- uses --> FFmpeg Integration (ObservableFFmpegExecutor)

API Gateway (ScanService)
    |-- uses --> FFmpeg Integration (ffprobe_video)

API Gateway (ProxyService, PreviewManager)
    |-- uses --> FFmpeg Integration (AsyncFFmpegExecutor for transcoding/HLS generation)

API Gateway (WaveformService)
    |-- uses --> FFmpeg Integration (ffprobe for waveform extraction)

API Gateway (HealthRouter)
    |-- checks availability of ffmpeg binary directly via subprocess

Observability
    |-- reads metrics from --> FFmpeg Integration (Prometheus metrics)
```

## Version History

| Version | Changes |
|---------|---------|
| v010 | Initial FFmpeg integration with executor, observable wrapper, probe, and metrics |
| v027 | Added async executor with progress tracking and cooperative cancellation; documented metric singleton module pattern (LRN-137) |
