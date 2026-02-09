---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-ffmpeg-contract-tests

## Summary

Implemented parametrized contract tests verifying Real, Recording, and Fake FFmpeg executors produce identical behavior. Added `strict` mode to `FakeFFmpegExecutor` for args verification.

## Acceptance Criteria

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1 | Parametrized tests run same commands against Real, Recording, and Fake executors | PASS |
| FR-2 | At least 5 representative FFmpeg commands tested | PASS (5 parametrized + 6 real executor tests) |
| FR-3 | Tests marked with `@pytest.mark.requires_ffmpeg` for CI environments | PASS |
| FR-4 | Contract violations between fake and real executor fail the test suite | PASS |
| FR-5 | `FakeFFmpegExecutor` supports optional `strict` parameter | PASS |

## Changes Made

### Modified Files

- **`src/stoat_ferret/ffmpeg/executor.py`** - Added `strict` parameter to `FakeFFmpegExecutor.__init__()` and `from_file()`. When `strict=True`, the `run()` method verifies args match the recording before replaying.
- **`pyproject.toml`** - Registered `requires_ffmpeg` marker.

### Created Files

- **`tests/test_contract/test_ffmpeg_contract.py`** - 21 contract tests in 4 test classes:
  - `TestRecordReplayContract` (5 parametrized): Record-and-replay with mock executor
  - `TestRealExecutorContract` (6 tests): Real FFmpeg record-and-replay (skipped without FFmpeg)
  - `TestStrictModeContract` (7 tests): Strict arg verification
  - `TestErrorConsistency` (3 tests): Error handling across executor types

## Test Results

- 21 new tests: 15 passed, 6 skipped (requires_ffmpeg)
- Full suite: 500 passed, 14 skipped
- Coverage: 93%

## Quality Gates

- ruff check: pass
- ruff format: pass
- mypy: pass (no issues in 37 source files)
- pytest: pass (500 passed, 14 skipped)
