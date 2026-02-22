# Handoff: 001-ffmpeg-observability

## What Was Done

- `ObservableFFmpegExecutor` is now the active FFmpeg executor in production, wrapping `RealFFmpegExecutor`
- All FFmpeg operations now emit Prometheus metrics and structured logs automatically
- `ThumbnailService` uses the DI-provided executor instead of creating its own

## Key Decisions

- `ffmpeg_executor` kwarg follows the same pattern as `ws_manager` and `effect_registry` (stored directly, not part of `has_injected` / `_deps_injected` logic)
- When injected via `create_app()`, the executor is stored as-is without wrapping, preserving test double compatibility

## For Next Feature

- The metrics (`ffmpeg_executions_total`, `ffmpeg_execution_duration_seconds`, `ffmpeg_active_processes`) are now populated and available at `/metrics`
- Any new service that needs FFmpeg execution should use `app.state.ffmpeg_executor` rather than creating `RealFFmpegExecutor` directly
