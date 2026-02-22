# Requirements: ffmpeg-observability

## Goal

Wire ObservableFFmpegExecutor into the dependency injection chain so FFmpeg operations emit metrics and structured logs.

## Background

Backlog Item: BL-059

`ObservableFFmpegExecutor` was built in v002/04-ffmpeg-integration with full metrics and structured logging instrumentation, but was never instantiated. The application uses `RealFFmpegExecutor` directly, bypassing all observability. This feature connects the existing component to the DI chain.

## Functional Requirements

**FR-001: ObservableFFmpegExecutor DI wiring**
- ObservableFFmpegExecutor is instantiated in the lifespan function, wrapping RealFFmpegExecutor
- Stored on `app.state` as the active FFmpeg executor
- Acceptance: `app.state.ffmpeg_executor` is an instance of `ObservableFFmpegExecutor` after startup

**FR-002: create_app() kwarg support**
- Add `ffmpeg_executor` kwarg to `create_app()` following the existing DI pattern
- When provided, skip lifespan executor creation (via `_deps_injected` flag)
- Acceptance: `create_app(ffmpeg_executor=mock)` stores `mock` on `app.state.ffmpeg_executor`

**FR-003: Structured log emission**
- FFmpeg operations emit structlog calls with duration, command preview, and correlation ID
- Acceptance: After a render operation, structlog output contains `ffmpeg_duration`, `command_preview`, and `correlation_id` fields

**FR-004: Prometheus metrics population**
- FFmpeg execution count and duration metrics are populated after render operations
- Acceptance: `ffmpeg_executions_total` counter increments and `ffmpeg_execution_duration_seconds` histogram records after execution

## Non-Functional Requirements

**NFR-001: Test double compatibility**
- Recording test double remains injectable via `create_app()` kwargs without being wrapped
- Metric: Tests using `create_app(ffmpeg_executor=recording_executor)` continue to pass

## Out of Scope

- Modifying `ObservableFFmpegExecutor` or `RealFFmpegExecutor` internals
- Adding new metrics beyond what already exists in `ffmpeg/metrics.py`
- Dashboard or visualization for FFmpeg metrics

## Test Requirements

- Unit: Verify `ObservableFFmpegExecutor` is the active executor via DI
- Unit: Verify `create_app(ffmpeg_executor=...)` stores executor on `app.state`
- Unit: Verify recording test double remains injectable (AC4)
- Integration: Verify FFmpeg execution emits structlog calls with duration, command preview, and correlation ID
- Integration: Verify Prometheus metrics populated after render operations
- Existing: `tests/test_api/conftest.py` may need update; `tests/test_api/test_di_wiring.py` should verify new DI param

See `comms/outbox/versions/design/v009/005-logical-design/test-strategy.md` for full test strategy.

## Reference

See `comms/outbox/versions/design/v009/004-research/` for supporting evidence.