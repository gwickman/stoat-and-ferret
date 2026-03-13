# Observable FFmpeg Executor

**Source:** `src/stoat_ferret/ffmpeg/observable.py`
**Component:** FFmpeg Integration

## Purpose

Provides a wrapper executor that adds structured logging and Prometheus metrics to any FFmpegExecutor implementation. Enables comprehensive observability of FFmpeg command execution with correlation IDs, structured context, and performance tracking.

## Public Interface

### Classes

- `ObservableFFmpegExecutor`: Wraps any FFmpegExecutor with logging and metrics
  - `__init__(wrapped: FFmpegExecutor) -> None`: Initialize with a wrapped executor
  - `run(args: list[str], *, stdin: bytes | None = None, timeout: float | None = None, correlation_id: str | None = None) -> ExecutionResult`: Execute FFmpeg with logging and metrics

## Dependencies

### Internal Dependencies

- `stoat_ferret.ffmpeg.executor`: Imports `ExecutionResult`, `FFmpegExecutor` protocol
- `stoat_ferret.ffmpeg.metrics`: Imports three metrics:
  - `ffmpeg_active_processes`: Gauge for active processes
  - `ffmpeg_execution_duration_seconds`: Histogram for duration tracking
  - `ffmpeg_executions_total`: Counter for execution counts

### External Dependencies

- `uuid`: Generates correlation IDs via `uuid.uuid4()`
- `structlog`: Structured logging via `structlog.get_logger(__name__)`

## Key Implementation Details

### Decorator/Wrapper Pattern

ObservableFFmpegExecutor implements the Decorator pattern:
- Wraps any FFmpegExecutor implementation
- Adds observability without changing wrapped executor behavior
- Protocol-compatible: can wrap RealFFmpegExecutor, RecordingFFmpegExecutor, FakeFFmpegExecutor
- Transparent delegation: result returned unchanged from wrapped executor

### Correlation ID Support

Enables distributed tracing:
- Generates UUID v4 if not provided: `correlation_id or str(uuid.uuid4())`
- Binds correlation ID to all log entries for this execution
- Enables request tracing across components and services
- Supports optional user-provided correlation IDs for integration with existing traces

### Structured Logging

Uses structlog with two primary log events:

**1. Start Event (`ffmpeg_execution_started`):**
- Context: correlation_id, command_args (first 10 args), arg_count
- Truncates args to first 10 to avoid logging sensitive paths
- Signals execution beginning

**2. Completion Event (`ffmpeg_execution_completed`):**
- Status: "success" (returncode == 0) or "failure"
- Context: returncode, duration_seconds (rounded to 3 decimals), status
- Signals execution completion with outcome

**3. Error Event (`ffmpeg_execution_failed`):**
- Exception message and type name captured
- Raised exception propagated after logging

### Metrics Recording

Uses try/finally pattern to ensure metrics are updated:

**Gauge Management:**
- Increment on execution start: `ffmpeg_active_processes.inc()`
- Decrement in finally block: `ffmpeg_active_processes.dec()` (always runs)
- Ensures accurate active process count even on exceptions

**Counter Management:**
- Success/failure status determined: `status = "success" if result.returncode == 0 else "failure"`
- Incremented with label: `ffmpeg_executions_total.labels(status=status).inc()`
- Also incremented on exception: `ffmpeg_executions_total.labels(status="failure").inc()`

**Histogram Recording:**
- Duration observation: `ffmpeg_execution_duration_seconds.observe(result.duration_seconds)`
- Only recorded on successful execution
- Enables SLA and performance monitoring

### Exception Handling

Preserves exception semantics:
- Exceptions from wrapped executor are logged with full context
- Original exception is re-raised unchanged
- Try/finally ensures metrics updated even on exception
- No exception suppression or transformation

## Relationships

- **Used by:** Application code that needs observable FFmpeg execution
- **Uses:** FFmpegExecutor implementations, structlog logging, Prometheus metrics
