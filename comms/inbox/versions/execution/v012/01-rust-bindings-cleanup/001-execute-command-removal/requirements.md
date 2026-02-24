# Feature: execute-command-removal

## Goal

Remove the dead `execute_command()` bridge function and `CommandExecutionError` class from the FFmpeg integration module.

## Background

`execute_command()` was built in v002/04-ffmpeg-integration as the bridge between the Rust command builder and the Python FFmpeg executor. It has zero callers in production code — the only production FFmpeg workflow (ThumbnailService) calls `executor.run()` directly at `src/stoat_ferret/api/services/thumbnail.py:69`, bypassing execute_command entirely.

Backlog Item: BL-061

## Functional Requirements

**FR-001**: Remove `execute_command()` function from `src/stoat_ferret/ffmpeg/integration.py`
- Acceptance: Function no longer exists in the module

**FR-002**: Remove `CommandExecutionError` class from `src/stoat_ferret/ffmpeg/integration.py`
- Acceptance: Class no longer exists in the module

**FR-003**: Remove exports from `src/stoat_ferret/ffmpeg/__init__.py`
- Acceptance: `execute_command` and `CommandExecutionError` no longer appear in `__init__.py` imports or `__all__`

**FR-004**: Remove `tests/test_integration.py` entirely
- Acceptance: File deleted — all 13 test methods covered execute_command exclusively

**FR-005**: Document removal in `docs/CHANGELOG.md` with re-add trigger
- Acceptance: CHANGELOG entry documents what was removed and states: re-add if Phase 3 Composition Engine or any future render/export endpoint needs Rust command building (LRN-029)

## Non-Functional Requirements

**NFR-001**: No test regressions
- Metric: All remaining tests pass (`uv run pytest` exits 0)

**NFR-002**: No import breakage
- Metric: `uv run ruff check src/` and `uv run mypy src/` pass with no errors related to removed exports

## Handler Pattern

Not applicable for v012 — no new handlers introduced.

## Out of Scope

- Wiring execute_command into a production workflow (decision is "remove", not "wire")
- Modifying ThumbnailService or any other FFmpeg-consuming code
- C4 documentation updates (tracked as BL-069)

## Test Requirements

- Remove `tests/test_integration.py` (13 tests, entire file)
- Verify no other tests import `execute_command` or `CommandExecutionError`
- Post-removal: `uv run pytest`, `uv run ruff check src/`, `uv run mypy src/`

## Reference

See `comms/outbox/versions/design/v012/004-research/` for supporting evidence.