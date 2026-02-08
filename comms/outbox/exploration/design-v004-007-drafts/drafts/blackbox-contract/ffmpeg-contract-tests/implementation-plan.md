# Implementation Plan — ffmpeg-contract-tests

## Overview

Create parametrized contract tests verifying Real, Recording, and Fake FFmpeg executors produce identical behavior. Add strict args verification to FakeFFmpegExecutor.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret/ffmpeg/executor.py` | Add `strict` parameter to FakeFFmpegExecutor |
| Create | `tests/test_contract/test_ffmpeg_contract.py` | Parametrized contract tests |
| Create | `tests/test_contract/__init__.py` | Package init |
| Create | `tests/fixtures/recordings/` | Recording data files for contract tests |
| Modify | `pyproject.toml` | Register `requires_ffmpeg` marker |

## Implementation Stages

### Stage 1: Strict Mode for FakeFFmpegExecutor
Add optional `strict=False` parameter to `FakeFFmpegExecutor`. When `strict=True`, verify `args` match the recording before replaying. Default non-strict preserves backward compatibility.

### Stage 2: Parametrized Fixture
Create parametrized `executor` fixture with `params=["real", "recording", "fake"]`. Real executor tests marked `@pytest.mark.requires_ffmpeg`. Create sample video fixture for tests.

### Stage 3: Contract Tests
Implement 5+ representative command tests running against all three executors. Verify return codes, output existence, and metadata parsing produce consistent results.

### Stage 4: Error and Arg Verification Tests
Test invalid input handling across all executors. Test strict mode arg verification — verify FakeFFmpegExecutor raises when args don't match recording.

## Quality Gates

- Contract tests: 10–14 tests total
- Real executor tests skip gracefully without FFmpeg
- Strict mode verified with dedicated tests
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| Sample video files in repo | Use minimal test fixtures; .gitignore large files |
| Real FFmpeg output varies by version | Test observable behavior (exit code, file created), not exact output |

## Commit Message

```
feat: add FFmpeg contract tests with strict arg verification
```
