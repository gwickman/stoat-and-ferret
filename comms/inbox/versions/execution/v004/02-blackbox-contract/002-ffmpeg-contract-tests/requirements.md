# Requirements — ffmpeg-contract-tests

## Goal

Parametrized tests running same commands against Real, Recording, and Fake executors with args verification.

## Background

`RecordingFFmpegExecutor` and `FakeFFmpegExecutor` exist from v001–v002, but no tests verify they produce behavior identical to `RealFFmpegExecutor`. This was explicitly deferred from v001. The `FakeFFmpegExecutor` replays by index without arg verification (see `004-research/codebase-patterns.md` §FFmpeg Executor). The contract gap was resolved in Task 006 (U3): add optional `strict=True` parameter for args verification.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|--------|
| FR-1 | Parametrized tests run the same commands against Real, Recording, and Fake executors | BL-024 |
| FR-2 | At least 5 representative FFmpeg commands tested across executor implementations | BL-024 |
| FR-3 | Tests marked with `@pytest.mark.requires_ffmpeg` for CI environments without FFmpeg | BL-024 |
| FR-4 | Contract violations between fake and real executor fail the test suite | BL-024 |
| FR-5 | `FakeFFmpegExecutor` supports optional `strict` parameter for args verification | BL-024 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | `requires_ffmpeg` and `contract` markers registered in `pyproject.toml` |
| NFR-2 | Real executor tests skipped gracefully when FFmpeg not available |
| NFR-3 | Recording files stored in `tests/fixtures/recordings/` |

## Out of Scope

- Testing every possible FFmpeg command — 5 representative commands is sufficient
- Modifying `RealFFmpegExecutor` — contract tests verify existing behavior
- Performance comparison between executors — that's BL-026

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Contract | Parametrized: same 5+ FFmpeg commands against Real, Recording, Fake | 5–8 |
| Contract | Arg verification: Fake replays match recorded args (strict mode) | 2–3 |
| Contract | Error behavior: all executors handle invalid input consistently | 2–3 |

Representative commands (per test strategy):
1. Version check: `ffmpeg -version`
2. Probe metadata: `ffprobe -v quiet -print_format json -show_streams input.mp4`
3. Trim clip: `ffmpeg -i input.mp4 -ss 0 -t 1 -c copy output.mp4`
4. Scale video: `ffmpeg -i input.mp4 -vf scale=640:480 output.mp4`
5. Apply audio filter: `ffmpeg -i input.mp4 -af volume=0.5 output.mp4`