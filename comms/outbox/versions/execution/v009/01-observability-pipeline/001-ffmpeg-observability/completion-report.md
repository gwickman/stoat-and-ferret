---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-ffmpeg-observability

## Summary

Wired `ObservableFFmpegExecutor` into the dependency injection chain so FFmpeg operations emit Prometheus metrics and structured logs. The component already existed but was never instantiated; this feature connects it to the DI chain.

## Changes

### `src/stoat_ferret/api/app.py`
- Added `ffmpeg_executor: FFmpegExecutor | None = None` kwarg to `create_app()`
- In lifespan: `RealFFmpegExecutor` is wrapped with `ObservableFFmpegExecutor` and stored on `app.state.ffmpeg_executor`
- `ThumbnailService` now uses `app.state.ffmpeg_executor` instead of creating its own `RealFFmpegExecutor`
- When `ffmpeg_executor` kwarg is provided (test injection), it's stored directly without wrapping

### `tests/test_ffmpeg_observability.py` (new)
- Tests for DI wiring: injected executor stored directly, not wrapped
- Tests for structlog emission: correlation_id, duration, command preview
- Tests for Prometheus metrics: counter increment, histogram recording

### `tests/test_api/test_di_wiring.py`
- Added test for `create_app(ffmpeg_executor=...)` storing executor on `app.state`

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001 | `app.state.ffmpeg_executor` is `ObservableFFmpegExecutor` after startup | Pass |
| FR-002 | `create_app(ffmpeg_executor=mock)` stores mock on `app.state.ffmpeg_executor` | Pass |
| FR-003 | Structlog output contains `correlation_id`, `command_args`, `duration_seconds` | Pass |
| FR-004 | `ffmpeg_executions_total` and `ffmpeg_execution_duration_seconds` populated | Pass |
| NFR-001 | Recording test double injectable via `create_app()` without wrapping | Pass |

## Quality Gates

| Gate | Result |
|------|--------|
| ruff check | Pass |
| ruff format | Pass |
| mypy | Pass (0 issues) |
| pytest | Pass (896 passed, 20 skipped, 92.73% coverage) |
