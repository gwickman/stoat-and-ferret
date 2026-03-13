# C4 Code Level: Clip Module

**Source:** `rust/stoat_ferret_core/src/clip/`
**Component:** Rust Core

## Purpose

Provides video clip representation and comprehensive validation. A clip represents a segment of a source media file defined by in/out points. The validation module detects structural errors and temporal bounds violations with actionable error messages.

## Public Interface

### Structs (PyO3 Classes)

#### `Clip`
Represents a video clip segment from a source file.

**Fields:**
- `source_path: String` — Path to source media file (PyO3: `#[pyo3(get)]`)
- `in_point: Position` — Start position within source (inclusive) (PyO3: `#[pyo3(get)]`)
- `out_point: Position` — End position within source (exclusive) (PyO3: `#[pyo3(get)]`)
- `source_duration: Option<Duration>` — Total source file duration (PyO3: `#[pyo3(get)]`)

**Construction:**
- `Clip::new(source_path: String, in_point: Position, out_point: Position, source_duration: Option<Duration>) -> Self`

**Methods:**
- `duration() -> Option<Duration>` — Calculate duration from in_point to out_point; returns None if out_point <= in_point (Python: `duration()` method)

**PyO3 Constructor:**
- `Clip(source_path: str, in_point: Position, out_point: Position, source_duration: Optional[Duration]) -> Clip`

#### `ValidationError` (in validation submodule)
Detailed validation error with field information.

**Note:** This struct (prefixed "Validation" in Python as `ClipValidationError`) is distinct from the `ValidationError` exception type defined in lib.rs.

**Fields:**
- `field: String` — Name of failed field (PyO3: `#[pyo3(get)]`)
- `message: String` — Human-readable error message (PyO3: `#[pyo3(get)]`)
- `actual: Option<String>` — Actual value provided (PyO3: `#[pyo3(get)]`)
- `expected: Option<String>` — Expected value or constraint (PyO3: `#[pyo3(get)]`)

**Constructors:**
- `ValidationError::new(field: impl Into<String>, message: impl Into<String>) -> Self` — Create error with message only
- `ValidationError::with_values(field: impl Into<String>, message: impl Into<String>, actual: impl Into<String>, expected: impl Into<String>) -> Self` — Create error with actual/expected values

**PyO3 Methods:**
- `ClipValidationError(field: str, message: str) -> ClipValidationError` — Constructor
- `ClipValidationError.with_values_py(field: str, message: str, actual: str, expected: str) -> ClipValidationError` — Static factory

### Functions

#### Validation Functions (in clip::validation submodule)

**Rust Functions:**
- `validate_clip(clip: &Clip) -> Vec<ValidationError>` — Validate single clip, returns all errors
- `validate_clips(clips: &[Clip]) -> Vec<ClipValidationError>` — Validate batch of clips; returns only clips with errors

**Python Functions (PyO3):**
- `validate_clip(clip: Clip) -> List[ClipValidationError]` — Python binding
- `validate_clips(clips: List[Clip]) -> List[Tuple[int, ClipValidationError]]` — Flattened to (index, error) tuples for Python consumption

## Validation Rules

### FR-001: Clip Structure Validation

1. **source_path must be non-empty** — Rejects empty strings with field name "source_path"
2. **out_point > in_point** — Rejects out_point <= in_point with:
   - field: "out_point"
   - actual: out_point.frames() as string
   - expected: format!(">{}",in_point.frames())

### FR-002: Temporal Bounds Validation

When `source_duration` is provided:

1. **in_point < source_duration** — Rejects in_point >= source_duration with:
   - field: "in_point"
   - actual: in_point.frames() as string
   - expected: format!("<{}", source_duration.frames())

2. **out_point <= source_duration** — Rejects out_point > source_duration with:
   - field: "out_point"
   - actual: out_point.frames() as string
   - expected: format!("<={}", source_duration.frames())

Note: When source_duration is None, bounds checks are skipped.

### FR-003: Multiple Error Collection

All applicable errors are collected and returned, enabling batch error reporting.

### FR-004: Batch Validation

The `validate_clips` function:
- Processes all clips
- Collects errors only from clips with validation failures
- Returns `Vec<ClipValidationError>` with clip indices
- Python binding flattens to `Vec<(usize, ValidationError)>` tuples

## Dependencies

### Internal Crate Dependencies

- `timeline::{Duration, Position}` — Timeline types for in/out points and duration validation

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings
- **pyo3_stub_gen** — Stub generation support

## Key Implementation Details

### Validation Error Messages

All error messages are:
- **Actionable:** Explain what went wrong and how to fix it
- **Specific:** Include the field name and actual/expected values
- **Consistent:** Use same terminology and structure across all errors

Example error messages:
- "Source path cannot be empty. Provide a valid path to the source media file."
- "Out point must be greater than in point. Adjust out point to be after in point."
- "In point exceeds source duration. Set in point to a frame within the source file."
- "Out point exceeds source duration. Set out point to at most the source duration."

### Batch Validation Pattern

The Rust `validate_clips` function returns `Vec<ClipValidationError>` with:
- `clip_index: usize` — 0-based index in original list
- `errors: Vec<ValidationError>` — All errors for that clip

The Python binding (`py_validate_clips`) flattens this to:
```rust
Vec<(usize, ValidationError)>  // (index, error) tuples
```

This enables Python callers to process errors more naturally:
```python
for clip_index, error in validate_clips(clips):
    print(f"Clip {clip_index}: {error}")
```

### Duration Calculation

The `Clip::duration()` method:
- Returns `Some(Duration)` if out_point > in_point
- Returns `None` otherwise
- Does NOT validate source_duration bounds (bounds are checked only during validation, not in duration calculation)

## Relationships

**Used by:**
- Composition builders — Validate clips before adding to timeline
- Python clip management — Validates user input before creating clips
- FFmpeg filter builders — Use validated clip durations for filter timing

**Uses:**
- `timeline::Duration` — For duration calculation and validation
- `timeline::Position` — For in/out point representation

## Testing

Comprehensive test suite with 40+ tests including:

1. **ValidationError tests** — Construction, display formatting, equality
2. **Single clip validation (FR-001):**
   - Valid clips with all combinations of fields
   - Empty source_path detection
   - Out <= in point rejection with actual/expected values

3. **Temporal bounds validation (FR-002):**
   - In-point exceeding source duration
   - Out-point exceeding source duration
   - Boundary conditions (in_point at source_duration-1, out_point at source_duration)
   - Unknown source_duration skips bounds checks

4. **Multiple errors (FR-003):**
   - Clips with empty path + invalid points + exceeding bounds return all errors

5. **Batch validation (FR-004):**
   - All valid clips return empty result
   - Mix of valid and invalid clips only returns errors
   - All invalid clips return all error entries
   - Empty clip list returns empty result
   - All errors per clip are preserved

## Notes

- **Clip Duration Calculation:** The clip duration is `out_point - in_point` in frame counts. This is the actual duration of the clip segment, independent of source file duration.
- **Source Duration Optional:** If source_duration is None, temporal bounds are not checked. This allows flexibility for files without known duration (streams, etc.).
- **Frame-Based Points:** Both in_point and out_point use frame counts from the timeline module, allowing frame-accurate editing.
- **Immutability:** Rust Clip struct is immutable once created; Python can modify properties via setters if needed (check PyO3 bindings for property definitions).

## Example Workflow

```python
from stoat_ferret_core import Clip, Position, Duration, validate_clip

# Create clip
clip = Clip(
    "input.mp4",
    Position.from_secs(0.0, FrameRate.fps_24()),
    Position.from_secs(10.0, FrameRate.fps_24()),
    Duration.from_secs(20.0, FrameRate.fps_24()),
)

# Validate
errors = validate_clip(clip)
if not errors:
    print("Clip is valid!")
    print(f"Duration: {clip.duration()}")
else:
    for error in errors:
        print(f"{error.field}: {error.message}")
```
