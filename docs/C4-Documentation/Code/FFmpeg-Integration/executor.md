# FFmpeg Executor

**Source:** `src/stoat_ferret/ffmpeg/executor.py`
**Component:** FFmpeg Integration

## Purpose

Provides a protocol-based abstraction for FFmpeg command execution with three implementations: RealFFmpegExecutor (actual subprocess), RecordingFFmpegExecutor (captures interactions for testing), and FakeFFmpegExecutor (replays recorded interactions). Supports deterministic testing and debugging through record/replay patterns.

## Public Interface

### Classes

- `ExecutionResult`: Result of an FFmpeg execution
  - `returncode: int`: Process exit code
  - `stdout: bytes`: Standard output as bytes
  - `stderr: bytes`: Standard error as bytes
  - `command: list[str]`: Full command that was executed
  - `duration_seconds: float`: Time taken to execute

- `FFmpegExecutor`: Protocol for FFmpeg command execution
  - `run(args: list[str], *, stdin: bytes | None = None, timeout: float | None = None) -> ExecutionResult`: Execute FFmpeg with given arguments

- `RealFFmpegExecutor`: Executor that runs FFmpeg via subprocess (production)
  - `__init__(ffmpeg_path: str = "ffmpeg") -> None`: Initialize with path to ffmpeg executable
  - `run(args: list[str], *, stdin: bytes | None = None, timeout: float | None = None) -> ExecutionResult`: Execute FFmpeg

- `RecordingFFmpegExecutor`: Executor that wraps another executor and records interactions
  - `__init__(wrapped: FFmpegExecutor, recording_path: Path) -> None`: Initialize with wrapped executor and recording path
  - `run(args: list[str], *, stdin: bytes | None = None, timeout: float | None = None) -> ExecutionResult`: Execute FFmpeg and record interaction
  - `save() -> None`: Save recorded interactions to JSON file

- `FakeFFmpegExecutor`: Executor that replays recorded FFmpeg interactions
  - `__init__(recordings: list[dict[str, object]], *, strict: bool = False) -> None`: Initialize with recorded interactions
  - `from_file(cls, path: Path, *, strict: bool = False) -> FakeFFmpegExecutor`: Load recordings from JSON file
  - `run(args: list[str], *, stdin: bytes | None = None, timeout: float | None = None) -> ExecutionResult`: Replay next recorded interaction
  - `assert_all_consumed() -> None`: Assert all recordings were used

## Dependencies

### Internal Dependencies

None (standalone FFmpeg execution abstraction)

### External Dependencies

- `json`: Serialization of recordings
- `subprocess`: Process execution in RealFFmpegExecutor
- `time`: Duration measurement via `time.monotonic()`
- `pathlib.Path`: File operations
- `dataclasses`: Dataclass decorator for ExecutionResult

## Key Implementation Details

### Protocol-Based Abstraction

`FFmpegExecutor` is a Protocol (structural subtyping), enabling:
- Multiple implementations (Real, Recording, Fake)
- Type-safe duck typing
- Composability through wrapping

### RealFFmpegExecutor Implementation

- Constructs command as `[ffmpeg_path, *args]`
- Uses `subprocess.run()` with:
  - `input=stdin`: Pass stdin bytes to process
  - `capture_output=True`: Capture both stdout and stderr
  - `timeout=timeout`: Optional timeout in seconds
- Measures duration using `time.monotonic()` for precision
- Returns ExecutionResult with full command reconstruction

### RecordingFFmpegExecutor Wrapper Pattern

Wraps any FFmpegExecutor implementation:
- Delegates execution to wrapped executor
- Intercepts results and records interactions
- Encodes binary stdout/stderr as hex strings for JSON serialization
- Records interaction structure:
  ```json
  {
    "args": [...],
    "stdin": "hex string or null",
    "result": {
      "returncode": 0,
      "stdout": "hex string",
      "stderr": "hex string",
      "duration_seconds": 1.5
    }
  }
  ```

### FakeFFmpegExecutor Replay

Replays recorded interactions in order:
- Maintains internal index to track current position
- Optional strict mode validates args before replay
- Decodes hex strings back to bytes via `bytes.fromhex()`
- Raises RuntimeError if:
  - Index exceeds recording count (called too many times)
  - In strict mode and args don't match recording
- `assert_all_consumed()` validates all recordings were used

## Relationships

- **Used by:** FFmpeg integration layer, observability wrappers, testing infrastructure
- **Uses:** Python stdlib subprocess, time, pathlib
