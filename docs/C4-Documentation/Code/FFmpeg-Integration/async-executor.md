# FFmpeg Async Executor

**Source:** `src/stoat_ferret/ffmpeg/async_executor.py`
**Component:** FFmpeg Integration

## Purpose

Provides an async protocol-based abstraction for long-running FFmpeg transcoding operations with real-time progress tracking and cooperative cancellation. Supports both real subprocess execution (RealAsyncFFmpegExecutor) and deterministic testing (FakeAsyncFFmpegExecutor) with progress parsing from FFmpeg stderr.

## Public Interface

### Data Classes

#### `ProgressInfo`
Parsed progress information from FFmpeg -progress output.

**Attributes:**
- `out_time_us: int` — Output time in microseconds (default: 0)
- `speed: float` — Encoding speed multiplier, e.g., 2.5x (default: 0.0)
- `fps: float` — Current frames per second (default: 0.0)

**Dataclass Fields:**
- All fields have defaults, allowing incremental updates via `parse_progress_line()`

### Type Aliases

#### `ProgressCallback`
Async callback type for progress updates.

**Type:** `Callable[[ProgressInfo], Awaitable[None]]`

**Usage:** Invoked by executor when progress data parsed from FFmpeg stderr. Application hooks progress_callback to update UI, database, or progress file.

### Protocols

#### `AsyncFFmpegExecutor`
Protocol defining async FFmpeg execution contract.

**Methods:**

- `async run(args: list[str], *, progress_callback: ProgressCallback | None = None, cancel_event: asyncio.Event | None = None) -> ExecutionResult`

  **Purpose:** Execute FFmpeg asynchronously with optional progress tracking and cancellation.

  **Parameters:**
  - `args: list[str]` — Arguments to pass to ffmpeg (not including "ffmpeg" command itself)
  - `progress_callback` — Optional async callback invoked with ProgressInfo when progress parsed
  - `cancel_event` — Optional asyncio.Event; when set, process is terminated

  **Returns:** ExecutionResult containing returncode, stdout, stderr, command, and duration_seconds

  **Raises:** Any exception raised by subprocess creation or progress callback

**Protocol Usage:** Type hints can accept any object implementing this interface, enabling:
- RealAsyncFFmpegExecutor (real subprocess)
- FakeAsyncFFmpegExecutor (test double)
- Custom implementations

### Classes

#### `RealAsyncFFmpegExecutor`
Async executor that runs FFmpeg via asyncio subprocess with progress parsing.

**Constructor:**
```python
def __init__(self, ffmpeg_path: str = "ffmpeg") -> None
```

**Attributes:**
- `ffmpeg_path: str` — Path to ffmpeg executable

**Methods:**

- `async run(args: list[str], *, progress_callback: ProgressCallback | None = None, cancel_event: asyncio.Event | None = None) -> ExecutionResult`

  **Purpose:** Execute FFmpeg asynchronously.

  **Process:**
  1. Constructs command as `[ffmpeg_path, *args]`
  2. Creates subprocess via `asyncio.create_subprocess_exec()` with pipes for stdin, stdout, stderr
  3. Launches two concurrent tasks:
     - `_read_stderr()` — Reads stderr line-by-line, parses progress, invokes callback
     - `_monitor_cancel()` — Waits for cancel_event, terminates process if set
  4. Calls `process.communicate()` to wait for completion
  5. Cleans up cancel monitoring task
  6. Returns ExecutionResult with returncode, stdout, stderr, command, and elapsed duration

  **Error Handling:**
  - Subprocess exceptions propagated to caller
  - Cancel task cancellation suppressed via contextlib.suppress(asyncio.CancelledError)
  - UTF-8 decoding with error replacement for malformed stderr lines

  **Logging:**
  - "async_ffmpeg_started" at INFO level when subprocess created
  - "async_ffmpeg_cancelling" at INFO level when cancel_event triggered
  - "async_ffmpeg_completed" at INFO level on completion with returncode and duration

**Key Implementation Details:**

- **Concurrent Stderr Reading:** Stderr is read in background task, not waited for in communicate(). This prevents deadlock on large stderr buffers.
- **Cancel Monitoring:** Separate task continuously awaits cancel_event, allowing non-blocking termination.
- **Progress Accumulation:** ProgressInfo object maintained across all stderr lines, allowing incremental updates to speed, fps, out_time_us.
- **Duration Measurement:** Uses `time.monotonic()` for wall-clock elapsed time, immune to system clock adjustments.

#### `FakeAsyncFFmpegExecutor`
Dataclass providing deterministic test double for async FFmpeg execution.

**Fields:**
- `returncode: int = 0` — Return code to emit in ExecutionResult
- `stderr_lines: list[str] = field(default_factory=list)` — Pre-configured stderr lines to parse for progress
- `stdout: bytes = b""` — Pre-configured stdout bytes
- `calls: list[list[str]] = field(default_factory=list)` — Record of all args passed to run()

**Methods:**

- `async run(args: list[str], *, progress_callback: ProgressCallback | None = None, cancel_event: asyncio.Event | None = None) -> ExecutionResult`

  **Purpose:** Simulate FFmpeg execution for deterministic testing.

  **Process:**
  1. Records args to self.calls for assertion
  2. Iterates over stderr_lines, parsing each line via `parse_progress_line()`
  3. If progress_callback provided, invokes callback with updated ProgressInfo after each line
  4. Constructs ExecutionResult with:
     - returncode: pre-configured value
     - stdout: pre-configured value
     - stderr: joins stderr_lines with newlines and encodes to UTF-8
     - command: `["ffmpeg", *args]`
     - duration_seconds: 0.0 (instant, not simulated)

  **Behavior:**
  - cancel_event is ignored (no actual cancellation simulation)
  - No logging (unlike RealAsyncFFmpegExecutor)
  - Deterministic: same inputs produce same outputs every time

**Testing Pattern:**
```python
executor = FakeAsyncFFmpegExecutor(
    returncode=0,
    stderr_lines=[
        "out_time_us=1000000",
        "speed=1.5x",
        "fps=30",
        "progress=continue",
    ],
    stdout=b"transcoding output"
)

# Call in test
result = await executor.run(["-i", "input.mp4", "-c:v", "libx264", "output.mp4"])

# Assert
assert result.returncode == 0
assert executor.calls == [["-i", "input.mp4", "-c:v", "libx264", "output.mp4"]]
```

### Functions

#### `parse_progress_line(line: str, info: ProgressInfo) -> ProgressInfo`

**Purpose:** Parse a single line from FFmpeg -progress pipe:2 output and update ProgressInfo in place.

**FFmpeg Progress Format:**
- Emits key=value pairs, one per line
- Blocks separated by "progress=continue" or "progress=end"
- Example stderr block:
  ```
  out_time_us=1000000
  speed=2.5x
  fps=30
  progress=continue
  ```

**Algorithm:**
1. Strip line whitespace
2. If no "=" in line, return info unchanged
3. Extract key and value via partition()
4. Match key:
   - "out_time_us" → parse int, store in info.out_time_us
   - "speed" → strip trailing "x", parse float, store in info.speed (handles "N/A")
   - "fps" → parse float, store in info.fps
   - Others → ignored
5. Return updated info

**Error Handling:**
- ValueError suppressed via contextlib.suppress() — invalid values retain previous ProgressInfo state
- Malformed lines silently ignored

**Returns:** Updated ProgressInfo with any newly parsed fields.

**Note:** Function modifies info in place AND returns it for chaining. Calling code typically uses return value.

**Examples:**

```python
info = ProgressInfo()

# Parse out_time_us
info = parse_progress_line("out_time_us=1000000", info)
assert info.out_time_us == 1000000

# Parse speed (handles "x" suffix)
info = parse_progress_line("speed=2.5x", info)
assert info.speed == 2.5

# Parse fps
info = parse_progress_line("fps=30", info)
assert info.fps == 30.0

# Handle N/A speed (ValueError suppressed)
info = parse_progress_line("speed=N/A", info)
assert info.speed == 2.5  # unchanged

# Empty lines and unknown keys ignored
info = parse_progress_line("", info)
info = parse_progress_line("unknown_key=value", info)
```

## Dependencies

### Internal Dependencies

- `stoat_ferret.ffmpeg.executor` — ExecutionResult dataclass (sync executor)

### External Dependencies

- **asyncio** — Async subprocess creation and communication
  - `asyncio.create_subprocess_exec()` — Launch FFmpeg process
  - `asyncio.subprocess.PIPE` — Connect stdin, stdout, stderr to pipes
  - `asyncio.Event` — Cancellation signaling
  - `asyncio.create_task()` — Launch concurrent reader and monitor tasks
  - `asyncio.wait_for()` — (Not used in this module; used in probe.py)
  - `asyncio.CancelledError` — Exception from cancelled tasks
- **contextlib** — `contextlib.suppress()` for error suppression
- **time** — `time.monotonic()` for duration measurement (wall-clock, immune to system clock adjustment)
- **collections.abc** — `Callable`, `Awaitable` type hints
- **dataclasses** — `@dataclass`, `field()` decorators
- **structlog** — Structured logging via `structlog.get_logger(__name__)`

## Key Implementation Details

### Concurrent Stderr Reading

FFmpeg writes stderr in real-time; RealAsyncFFmpegExecutor reads it concurrently with process execution:

**Architecture:**
```
Main Task
  ├─ Subprocess created
  ├─ create_task(_read_stderr) → runs concurrently
  ├─ create_task(_monitor_cancel) → runs concurrently
  └─ await process.communicate() → waits for process end

_read_stderr Task
  └─ Continuously reads lines from stderr
     └─ Parses progress
     └─ Invokes callback

_monitor_cancel Task
  └─ Waits for cancel_event
  └─ If set: calls process.terminate()
```

**Rationale:** Concurrent reading prevents deadlock on large stderr output. If stderr buffer fills and we're not reading, process blocks or crash. This design prevents that.

### Cancel Event Handling

Cancellation is cooperative (not forceful):

1. **Trigger:** User/app sets cancel_event via `cancel_event.set()`
2. **Monitoring:** _monitor_cancel task awaits event
3. **Termination:** When event set, calls `process.terminate()` (SIGTERM on Unix)
4. **Process Cleanup:** Process handles termination (may take time)
5. **Cleanup:** Cancel task cancelled after communicate() returns, suppressing CancelledError

**Benefits:**
- Process has chance to clean up gracefully
- No forceful kill(-9) unless needed
- Application can add timeout after terminate() if needed

### Progress Callback Invocation

Progress callbacks are invoked after each stderr line:

```python
async def _read_stderr() -> None:
    while True:
        line_bytes = await process.stderr.readline()
        if not line_bytes:
            break
        stderr_chunks.append(line_bytes)
        line = line_bytes.decode("utf-8", errors="replace")
        parse_progress_line(line, info)  # Update ProgressInfo
        if progress_callback is not None:
            await progress_callback(info)  # Invoke async callback
```

**Frequency:** Callbacks invoked roughly every FFmpeg progress block (default ~1 second for typical transcoding).

**Callback Exceptions:** If callback raises, exception propagates to caller. Reader task not wrapped in try/except, allowing exceptions to terminate reading.

### Duration Measurement

Uses `time.monotonic()` for robustness:

```python
start = time.monotonic()
# ... transcoding ...
duration = time.monotonic() - start
```

**Why monotonic():**
- Immune to system clock adjustments (NTP, daylight saving time)
- Always forward-moving (no negative durations)
- Precise to sub-second resolution

Alternative (time.time()) would fail if system clock adjusted during execution.

### FakeAsyncFFmpegExecutor for Testing

FakeAsyncFFmpegExecutor is dataclass with mutable state:

**Setup Pattern:**
```python
executor = FakeAsyncFFmpegExecutor(
    returncode=0,
    stderr_lines=["out_time_us=1000000", "speed=2.5x", ...],
    stdout=b"expected output",
)
```

**Assertion Pattern:**
```python
result = await executor.run([...])
assert executor.calls[0] == ["-i", "input.mp4", ...]
```

**Benefits:**
- No actual subprocess or I/O
- Deterministic (same inputs → same outputs)
- Full control over return code, progress, duration
- Call recording for assertion

## Relationships

**Used by:**
- Python transcoding pipeline — Execute FFmpeg with progress tracking and cancellation
- Web API endpoints — Async handling of long-running FFmpeg operations
- Progress reporting system — Real-time progress updates to clients
- Batch rendering — Parallel encoding with per-job cancellation

**Uses:**
- `executor` module — ExecutionResult dataclass
- asyncio — Subprocess and event handling
- structlog — Logging

## Testing Patterns

### Unit Testing with FakeAsyncFFmpegExecutor

```python
import pytest
from stoat_ferret.ffmpeg.async_executor import FakeAsyncFFmpegExecutor, ProgressInfo

@pytest.mark.asyncio
async def test_progress_callback_invoked():
    progress_updates = []

    async def on_progress(info: ProgressInfo):
        progress_updates.append(info)

    executor = FakeAsyncFFmpegExecutor(
        returncode=0,
        stderr_lines=["out_time_us=1000000", "speed=2.5x"],
    )

    result = await executor.run(
        ["-i", "input.mp4", "output.mp4"],
        progress_callback=on_progress,
    )

    assert len(progress_updates) == 2
    assert progress_updates[0].out_time_us == 1000000
    assert progress_updates[1].speed == 2.5
```

### Integration Testing with RealAsyncFFmpegExecutor

```python
@pytest.mark.asyncio
async def test_real_executor_success(tmp_path):
    executor = RealAsyncFFmpegExecutor(ffmpeg_path="ffmpeg")

    # Create dummy video (requires ffmpeg installed)
    input_file = tmp_path / "input.mp4"
    output_file = tmp_path / "output.mp4"

    result = await executor.run([
        "-f", "lavfi",
        "-i", "testsrc=s=320x240:d=1",
        "-f", "lavfi",
        "-i", "sine=f=1000:d=1",
        str(output_file),
    ])

    assert result.returncode == 0
    assert output_file.exists()
    assert result.duration_seconds > 0
```

### Cancellation Testing

```python
@pytest.mark.asyncio
async def test_cancellation():
    executor = RealAsyncFFmpegExecutor()
    cancel_event = asyncio.Event()

    async def cancel_after_delay():
        await asyncio.sleep(0.1)
        cancel_event.set()

    asyncio.create_task(cancel_after_delay())

    result = await executor.run(
        ["-f", "lavfi", "-i", "testsrc=d=100", "-f", "null", "-"],
        cancel_event=cancel_event,
    )

    # Process should have been terminated by cancel_event
    assert result.duration_seconds < 100  # Much less than 100 second input
```

## Notes

- **Progress Parsing Robustness:** parse_progress_line() silently ignores unparseable lines via suppress(ValueError). Allows graceful handling of FFmpeg output variations.
- **Async First:** All implementations are async. No sync version; use executor module for sync operations.
- **Protocol Usage:** AsyncFFmpegExecutor is Protocol (structural subtyping), not ABC. Any object with correct run() signature works.
- **Logging Structured:** Uses structlog for semi-structured logging. Integrates with application's logging infrastructure.
- **No Timeouts in Executor:** Timeouts handled by caller via `asyncio.wait_for()`. Executor focuses on execution; caller controls time constraints.
- **Memory Efficiency:** stderr_chunks accumulated in RealAsyncFFmpegExecutor, potentially large for long transcoding. Consider streaming to disk for very large jobs.
- **Thread Safety:** asyncio single-threaded per event loop. Not thread-safe; use from single event loop only.

## Example Usage

```python
import asyncio
from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor, ProgressInfo

async def transcode_with_progress():
    executor = RealAsyncFFmpegExecutor(ffmpeg_path="ffmpeg")

    progress_updates = []

    async def on_progress(info: ProgressInfo):
        progress_updates.append(info)
        print(f"Speed: {info.speed:.1f}x, FPS: {info.fps:.1f}")

    cancel_event = asyncio.Event()

    # Transcode video
    result = await executor.run(
        [
            "-i", "input.mp4",
            "-c:v", "libx264",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "output.mp4",
        ],
        progress_callback=on_progress,
        cancel_event=cancel_event,
    )

    print(f"Completed in {result.duration_seconds:.2f}s")
    print(f"Return code: {result.returncode}")
    print(f"Total progress updates: {len(progress_updates)}")

    return result

# Run
result = asyncio.run(transcode_with_progress())
```

## Web API Integration Example

```python
# Flask/FastAPI endpoint using async executor
from fastapi import FastAPI, BackgroundTasks
from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor, ProgressInfo

app = FastAPI()
executor = RealAsyncFFmpegExecutor()

# Shared state (in production: database/Redis)
jobs = {}

async def transcode_job(job_id: str, input_path: str, output_path: str):
    jobs[job_id] = {"status": "running", "progress": 0.0}

    async def on_progress(info: ProgressInfo):
        # Store progress in job state
        jobs[job_id]["progress"] = info.out_time_us

    cancel_event = asyncio.Event()
    jobs[job_id]["cancel"] = cancel_event

    result = await executor.run(
        ["-i", input_path, "-c:v", "libx264", output_path],
        progress_callback=on_progress,
        cancel_event=cancel_event,
    )

    jobs[job_id]["status"] = "completed" if result.returncode == 0 else "failed"

@app.post("/transcode")
async def start_transcode(input_path: str, output_path: str, background_tasks: BackgroundTasks):
    job_id = "job_123"
    background_tasks.add_task(transcode_job, job_id, input_path, output_path)
    return {"job_id": job_id}

@app.get("/transcode/{job_id}")
async def get_job_status(job_id: str):
    job = jobs.get(job_id)
    return job or {"status": "not_found"}

@app.post("/transcode/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = jobs.get(job_id)
    if job and "cancel" in job:
        job["cancel"].set()
    return {"cancelled": True}
```
