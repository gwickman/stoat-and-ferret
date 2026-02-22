# Implementation Plan: ffmpeg-observability

## Overview

Wire `ObservableFFmpegExecutor` into the dependency injection chain by wrapping `RealFFmpegExecutor` in the lifespan function and adding `ffmpeg_executor` as a `create_app()` kwarg. The component and its metrics/logging instrumentation already exist — this feature only connects them.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/app.py` | Modify | Add `ffmpeg_executor` kwarg to `create_app()`, wrap RealFFmpegExecutor with ObservableFFmpegExecutor in lifespan |
| `tests/test_api/conftest.py` | Modify | Update test fixtures if `create_app()` signature change affects them |
| `tests/test_api/test_di_wiring.py` | Modify | Add test verifying `ffmpeg_executor` stored on `app.state` |
| `tests/test_ffmpeg_observability.py` | Create | Tests for observable executor wiring, metrics, and structlog output |

## Test Files

`tests/test_api/test_di_wiring.py tests/test_ffmpeg_observability.py`

## Implementation Stages

### Stage 1: Add create_app() kwarg and lifespan wiring

1. Add `ffmpeg_executor: FFmpegExecutor | None = None` kwarg to `create_app()`
2. In lifespan (when not `_deps_injected`): create `RealFFmpegExecutor()`, wrap with `ObservableFFmpegExecutor(real_executor)`, store on `app.state.ffmpeg_executor`
3. When `ffmpeg_executor` kwarg is provided: store directly on `app.state.ffmpeg_executor` (no wrapping)
4. Update `ThumbnailService` instantiation to use `app.state.ffmpeg_executor` instead of creating `RealFFmpegExecutor()` directly

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_api/test_di_wiring.py -x
```

### Stage 2: Add tests

1. Test that `app.state.ffmpeg_executor` is `ObservableFFmpegExecutor` after normal startup
2. Test that `create_app(ffmpeg_executor=mock)` stores mock directly (not wrapped)
3. Test that FFmpeg execution emits structlog calls with expected fields
4. Test that Prometheus metrics are populated after execution

**Verification:**
```bash
uv run pytest tests/test_ffmpeg_observability.py tests/test_api/test_di_wiring.py -x
```

## Test Infrastructure Updates

- May need to update `conftest.py` if existing test fixtures pass explicit executor values
- Existing tests using `create_app()` should continue working since new kwarg defaults to `None`

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- `ThumbnailService` currently creates its own executor — must be refactored to use DI. See `006-critical-thinking/risk-assessment.md`.
- Test doubles must bypass ObservableFFmpegExecutor wrapping. Resolved: `_deps_injected` flag skips lifespan.

## Commit Message

```
feat(observability): wire ObservableFFmpegExecutor into DI chain

BL-059: Wrap RealFFmpegExecutor with ObservableFFmpegExecutor in lifespan
so FFmpeg operations emit metrics and structured logs. Add ffmpeg_executor
kwarg to create_app() for test injection.
```