# Theme 04: ffmpeg-integration

## Overview
Create observable, testable FFmpeg integration connecting Rust command builder to Python execution.

## Context
- Roadmap M1.5 specifies FFprobe wrapper, executor protocol, DI pattern
- EXP-002 established recording fake pattern
- Rust builds commands, Python executes subprocess

## Architecture Decisions

### AD-001: Executor Boundary
```
Python: FFmpegExecutor.run(args) -> ExecutionResult
        └── subprocess.run([ffmpeg] + args)

Rust:   FFmpegCommand.build() -> Vec<String>
        └── Returns args only, no execution
```

### AD-002: Three Executor Implementations
1. RealFFmpegExecutor - actually runs ffmpeg/ffprobe
2. RecordingFFmpegExecutor - wraps real, captures interactions
3. FakeFFmpegExecutor - replays recorded interactions

### AD-003: Observability Layer
ObservableFFmpegExecutor wraps any executor and adds:
- Structured logging with correlation ID
- Prometheus metrics
- Duration tracking

## Dependencies
- v001 Rust FFmpegCommand
- EXP-002 recording fake pattern

## New Dependencies
- structlog>=24.0
- prometheus-client>=0.20

## Evidence
- FFmpeg executor boundary: `comms/outbox/exploration/design-research-gaps/design-clarifications.md`
- Recording fake pattern: `comms/outbox/exploration/recording-fake-pattern/`
- prometheus-client: `docs/design/07-quality-architecture.md`

## Success Criteria
- FFprobe returns structured metadata
- Recording captures real interactions
- Fake replays for fast tests
- Metrics and logging for all executions