# Rust Types Analysis

## Clip Module

### Status: EXISTS but NOT EXPOSED to Python

Location: `rust/stoat_ferret_core/src/clip/mod.rs`

The `Clip` struct is fully implemented with:

```rust
#[derive(Debug, Clone)]
pub struct Clip {
    pub source_path: String,
    pub in_point: Position,
    pub out_point: Position,
    pub source_duration: Option<Duration>,
}
```

**API:**
- `Clip::new(source_path, in_point, out_point, source_duration)` - Constructor
- `clip.duration()` - Returns `Option<Duration>` between in/out points

**What's MISSING:**
- No `#[pyclass]` attribute
- No `#[pymethods]` block
- No registration in `lib.rs`

The clip validation module is also implemented but not exposed.

## ValidationError

### Status: COMPLETE with expected attributes

Location: `rust/stoat_ferret_core/src/clip/validation.rs`

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationError {
    pub field: String,      // Name of the field that failed
    pub message: String,    // Human-readable explanation
    pub actual: Option<String>,   // The actual value provided
    pub expected: Option<String>, // The expected value/constraint
}
```

**Constructors:**
- `ValidationError::new(field, message)` - Basic error
- `ValidationError::with_values(field, message, actual, expected)` - Full error with context

**Display format:** `"field: message (got: actual, expected: expected)"`

**Usage:**
- `validate_clip(&clip) -> Vec<ValidationError>` - Validates single clip
- `validate_clips(&[clips]) -> Vec<ClipValidationError>` - Batch validation with clip index

This `ValidationError` is a Rust struct, NOT the Python exception `ValidationError` in `lib.rs` which is separate.

## TimeRange List Operations

### Status: EXISTS in Rust, NOT EXPOSED to Python

Location: `rust/stoat_ferret_core/src/timeline/range.rs`

**Functions that exist:**

```rust
pub fn find_gaps(ranges: &[TimeRange]) -> Vec<TimeRange>
```
Finds gaps between non-overlapping portions of ranges. Sorts by start, merges overlaps, returns gaps.

```rust
pub fn merge_ranges(ranges: &[TimeRange]) -> Vec<TimeRange>
```
Merges overlapping and adjacent ranges into minimal non-overlapping set.

```rust
pub fn total_coverage(ranges: &[TimeRange]) -> Duration
```
Calculates total duration covered (overlaps counted once).

**What's MISSING:**
- No `#[pyfunction]` attributes on these functions
- Not registered in `lib.rs` via `m.add_function()`
- Not in the Python stubs

## py_ Prefix Inventory

### Total: 54 methods across 7 files

All `py_` prefixed methods exist to enable PyO3's method chaining pattern where `PyRefMut<'_, Self>` is returned. Without the prefix, the Rust method name would collide with a method returning `Self` (for Rust-native usage).

### Timeline Types (16 methods)

**duration.rs:**
- `py_new(frames)` - Constructor (`#[new]`)
- `py_frames(&self)` - Getter (`#[getter]`)

**position.rs:**
- `py_new(frames)` - Constructor
- `py_frames(&self)` - Getter

**framerate.rs:**
- `py_new(numerator, denominator)` - Constructor
- `py_numerator(&self)` - Getter
- `py_denominator(&self)` - Getter

**range.rs:**
- `py_new(start, end)` - Constructor
- `py_start(&self)` - Getter
- `py_end(&self)` - Getter
- `py_duration(&self)` - Getter
- `py_overlaps(&self, other)` - Method
- `py_adjacent(&self, other)` - Method
- `py_overlap(&self, other)` - Method
- `py_gap(&self, other)` - Method
- `py_intersection(&self, other)` - Method
- `py_union(&self, other)` - Method
- `py_difference(&self, other)` - Method

### FFmpeg Command Builder (18 methods)

**command.rs:**
- `py_new()` - Constructor
- `py_overwrite(yes)` - Returns `PyRefMut`
- `py_loglevel(level)` - Returns `PyRefMut`
- `py_input(path)` - Returns `PyRefMut`
- `py_seek(seconds)` - Returns `PyRefMut`
- `py_duration(seconds)` - Returns `PyRefMut`
- `py_stream_loop(count)` - Returns `PyRefMut`
- `py_output(path)` - Returns `PyRefMut`
- `py_video_codec(codec)` - Returns `PyRefMut`
- `py_audio_codec(codec)` - Returns `PyRefMut`
- `py_preset(preset)` - Returns `PyRefMut`
- `py_crf(crf)` - Returns `PyRefMut`
- `py_format(format)` - Returns `PyRefMut`
- `py_filter_complex(filter)` - Returns `PyRefMut`
- `py_map(stream)` - Returns `PyRefMut`
- `py_build(&self)` - Returns `PyResult<Vec<String>>`

### Filter Types (12 methods)

**filter.rs:**

Filter:
- `py_new(name)` - Constructor
- `py_param(key, value)` - Returns `PyRefMut`

FilterChain:
- `py_new()` - Constructor
- `py_input(label)` - Returns `PyRefMut`
- `py_filter(f)` - Returns `PyRefMut`
- `py_output(label)` - Returns `PyRefMut`

FilterGraph:
- `py_new()` - Constructor
- `py_chain(chain)` - Returns `PyRefMut`

Helper functions:
- `py_scale_filter(width, height)` - Free function
- `py_concat_filter(n, v, a)` - Free function

### Sanitization (8 functions)

**sanitize/mod.rs:**
- `py_escape_filter_text(input)` - Text escaping
- `py_validate_path(path)` - Path validation
- `py_validate_crf(crf)` - CRF range check
- `py_validate_speed(speed)` - Speed range check
- `py_validate_volume(volume)` - Volume range check
- `py_validate_video_codec(codec)` - Codec whitelist
- `py_validate_audio_codec(codec)` - Codec whitelist
- `py_validate_preset(preset)` - Preset whitelist

### Rationale for py_ Prefix

The `py_` prefix pattern is used because:

1. **Method chaining requirement**: PyO3 builder methods must return `PyRefMut<'_, Self>` for Python method chaining, but Rust idiomatically returns `Self` for the same purpose.

2. **Avoiding collision**: The same struct can have both:
   - `fn input(self, path: String) -> Self` - For Rust usage
   - `fn py_input(slf: PyRefMut<'_, Self>, path: String) -> PyRefMut<'_, Self>` - For Python

3. **Name attribute option**: Some methods use `#[pyo3(name = "input")]` to expose `py_input` as `input` in Python, giving the best of both worlds.
