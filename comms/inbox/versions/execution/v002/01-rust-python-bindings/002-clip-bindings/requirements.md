# Clip and ValidationError Bindings

## Goal
Expose the Clip struct and ValidationError struct to Python via PyO3.

## Background
- Clip struct exists in rust/stoat_ferret_core/src/clip/mod.rs
- ValidationError struct exists in clip/validation.rs with field, message, actual, expected
- Neither has PyO3 bindings currently
- Note: ValidationError (struct) is distinct from ValidationError (Python exception in lib.rs)

## Requirements

### FR-001: Clip PyO3 Bindings
- Add #[pyclass] to Clip struct
- Add #[pymethods] with:
  - Constructor: new(source_path, in_point, out_point, source_duration)
  - Getters: source_path, in_point, out_point, source_duration
  - Method: duration() -> Option<Duration>
- Register in lib.rs

### FR-002: ValidationError Struct PyO3 Bindings
- Add #[pyclass] to ValidationError struct in clip/validation.rs
- Add #[pymethods] with:
  - Getters: field, message, actual, expected
  - Constructor: new(field, message), with_values(field, message, actual, expected)
- Register in lib.rs
- Document distinction from ValidationError exception

### FR-003: Validation Functions
- Expose validate_clip(clip) -> list[ValidationError]
- Expose validate_clips(clips) -> list[tuple[int, ValidationError]]

### FR-004: Regenerate Stubs
- Run stub generator after adding bindings
- Verify new types appear in stubs

### FR-005: Integration Tests
- Test Clip construction from Python
- Test ValidationError struct creation and attribute access
- Test validate_clip function

## Acceptance Criteria
- [ ] `from stoat_ferret_core import Clip` works
- [ ] `from stoat_ferret_core.clip import ValidationError` exposes struct (or similar import path)
- [ ] Clip attributes accessible: source_path, in_point, out_point
- [ ] ValidationError.field, .message, .actual, .expected work
- [ ] validate_clip returns list of validation errors
- [ ] Stubs include new types
- [ ] Integration tests pass