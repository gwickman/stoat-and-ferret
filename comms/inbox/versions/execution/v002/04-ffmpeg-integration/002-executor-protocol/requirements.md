# Executor Protocol

## Goal
Define FFmpegExecutor protocol with Real, Recording, and Fake implementations.

## Requirements

### FR-001: ExecutionResult Dataclass
- returncode: int
- stdout: bytes
- stderr: bytes  
- command: list[str]
- duration_seconds: float

### FR-002: FFmpegExecutor Protocol
- run(args, stdin, timeout) -> ExecutionResult

### FR-003: RealFFmpegExecutor
- Actually runs ffmpeg via subprocess
- Configurable ffmpeg path

### FR-004: RecordingFFmpegExecutor
- Wraps another executor
- Records all interactions to JSON
- save() method to persist recordings
- Uses hex encoding for binary data (per EXP-002)

### FR-005: FakeFFmpegExecutor
- Loads recorded interactions
- Replays responses in order
- Raises if called more times than recorded

## Acceptance Criteria
- [ ] RealFFmpegExecutor runs ffmpeg
- [ ] RecordingExecutor captures interactions
- [ ] FakeExecutor replays without subprocess
- [ ] Recording format is JSON, human-readable

## Evidence
- Recording fake pattern: `comms/outbox/exploration/recording-fake-pattern/`