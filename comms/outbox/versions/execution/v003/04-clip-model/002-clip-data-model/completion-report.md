---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-clip-data-model

## Summary

Implemented the Clip data model with Rust validation delegation. The Clip dataclass represents video clip segments within a project, with validation logic delegated to the Rust core library via `validate_clip()`.

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Clip model defined | PASS |
| Validation delegates to Rust | PASS |
| Invalid clips raise ClipValidationError | PASS |
| Migration creates clips table | PASS |

## Implementation Details

### Clip Model (`src/stoat_ferret/db/models.py`)

- Added `Clip` dataclass with fields: `id`, `project_id`, `source_video_id`, `in_point`, `out_point`, `timeline_position`, `created_at`, `updated_at`
- Added `ClipValidationError` exception class that wraps Rust validation errors as a Python exception
- `Clip.validate()` method creates a Rust `Clip` and calls `validate_clip()` to validate using the Rust core library

### Database Migration (`alembic/versions/39896ab3d0b7_add_clips_table.py`)

- Creates `clips` table with foreign keys:
  - `project_id` -> `projects(id)` with ON DELETE CASCADE
  - `source_video_id` -> `videos(id)` with ON DELETE RESTRICT
- Adds indexes for efficient queries:
  - `idx_clips_project` on `project_id`
  - `idx_clips_timeline` on `(project_id, timeline_position)`

### Schema Update (`src/stoat_ferret/db/schema.py`)

- Added `CLIPS_TABLE`, `CLIPS_PROJECT_INDEX`, `CLIPS_TIMELINE_INDEX` SQL definitions
- Updated `create_tables()` to create clips table and indexes

### Tests (`tests/test_clip_model.py`)

- 9 tests covering:
  - Valid clip validation passing
  - Invalid clips (out before in, zero duration, empty path, exceeds source duration) raising `ClipValidationError`
  - `new_id()` generating unique UUIDs
  - Dataclass field access

## Quality Gate Results

- **ruff check**: All checks passed
- **ruff format**: All files formatted
- **mypy**: No errors (type ignores added for incomplete auto-generated stubs)
- **pytest**: 360 tests passed (351 + 9 new), 93% coverage

## Technical Notes

1. **Type Ignores**: Added `# type: ignore[call-arg]` comments for Rust PyO3 bindings (`Position`, `Duration`, `Clip`) because the auto-generated stubs in `src/stoat_ferret_core/_core.pyi` are incomplete (only have class docstrings, not method signatures). The manually maintained stubs in `stubs/stoat_ferret_core/_core.pyi` have full signatures but mypy finds the auto-generated ones first.

2. **Python Exception Wrapper**: Created `ClipValidationError` as a Python exception class that wraps the Rust `ClipValidationError` data class, since the Rust type is a struct (not an exception) and cannot be raised directly.

## PR Details

- PR #45: https://github.com/gwickman/stoat-and-ferret/pull/45
- Merged via squash to main
