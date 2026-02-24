# Implementation Plan: execute-command-removal

## Overview

Remove the dead `execute_command()` function and `CommandExecutionError` class from the FFmpeg integration module. This is a straightforward deletion task — zero production callers exist. The function, its error class, exports, and all 13 dedicated tests are removed. A CHANGELOG entry documents the removal with a re-add trigger.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/ffmpeg/integration.py` | Modify | Remove `execute_command()` function and `CommandExecutionError` class |
| `src/stoat_ferret/ffmpeg/__init__.py` | Modify | Remove `execute_command` and `CommandExecutionError` from imports and `__all__` |
| `tests/test_integration.py` | Delete | Remove entire file (all 13 tests are for execute_command) |
| `docs/CHANGELOG.md` | Modify | Add v012 removal entry with re-add trigger |

## Test Files

`tests/ -k "not test_integration"`

Post-removal full suite: `uv run pytest`

## Implementation Stages

### Stage 1: Remove function and class from integration.py

1. Read `src/stoat_ferret/ffmpeg/integration.py`
2. Remove the `execute_command()` function (lines ~43-88)
3. Remove the `CommandExecutionError` class
4. Remove any imports that become unused after removal

**Verification**: `uv run ruff check src/stoat_ferret/ffmpeg/integration.py`

### Stage 2: Update exports

1. Read `src/stoat_ferret/ffmpeg/__init__.py`
2. Remove `execute_command` and `CommandExecutionError` from import statements
3. Remove from `__all__` list

**Verification**: `uv run mypy src/stoat_ferret/ffmpeg/`

### Stage 3: Remove test file

1. Delete `tests/test_integration.py`

**Verification**: `uv run pytest` — all remaining tests pass

### Stage 4: Document removal

1. Add v012 entry to `docs/CHANGELOG.md`:
   - Removed: `execute_command()` and `CommandExecutionError` from `stoat_ferret.ffmpeg`
   - Re-add trigger: Phase 3 Composition Engine or any future render/export endpoint needing Rust command building

**Verification**: Manual review of CHANGELOG entry

## Test Infrastructure Updates

- Remove `tests/test_integration.py` (13 tests)
- No new tests needed — removal feature

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Low risk — zero production callers confirmed via exhaustive grep
- See `comms/outbox/versions/design/v012/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat(v012): remove dead execute_command() bridge function

Remove execute_command() and CommandExecutionError from FFmpeg
integration module. Zero production callers — ThumbnailService
calls executor.run() directly. Re-add trigger documented in
CHANGELOG for Phase 3 Composition Engine.

Closes BL-061
```
