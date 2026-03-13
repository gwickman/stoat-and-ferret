# C4 Code Level: Crate Root (_core Module)

**Source:** `rust/stoat_ferret_core/src/lib.rs`
**Component:** Rust Core

## Purpose

Crate root module that defines the PyO3 module interface, registers all Rust types and functions for Python consumption, and declares custom exception types. This is the entry point for all Python-to-Rust bindings.

## Public Interface

### Module Declaration and Exports

The module declares and publicly exports all submodules:
- `pub mod batch` — Batch render progress aggregation
- `pub mod clip` — Video clip representation and validation
- `pub mod compose` — Composition graph and overlay builders
- `pub mod ffmpeg` — FFmpeg command building and filtering
- `pub mod layout` — Layout positioning for composition
- `pub mod sanitize` — Input sanitization for FFmpeg commands
- `pub mod timeline` — Frame-accurate timeline mathematics

### Custom Exception Types (PyO3)

The following custom Python exceptions are created and exposed:

- **ValidationError** - Base exception for validation failures (distinct from ClipValidationError struct)
- **CommandError** - Errors in FFmpeg command building
- **SanitizationError** - Input sanitization failures
- **LayoutError** - Layout position validation failures

All exceptions inherit from `pyo3.exceptions.PyException`.

### Functions

- **`health_check() -> str`**
  - Returns "stoat_ferret_core OK" to verify module is loaded correctly
  - Python binding: `health_check()`

### PyModule Registration (_core)

The `#[pymodule] fn _core(m: &Bound<PyModule>) -> PyResult<()>` function registers all types and functions with Python:

**Timeline types:**
- `FrameRate` — Rational frame rate representation
- `Position` — Timeline position as frame count
- `Duration` — Timeline duration as frame count
- `TimeRange` — Half-open time range [start, end)

**Clip types:**
- `Clip` — Video clip with source path, in/out points
- `ClipValidationError` — Detailed validation error struct

**Clip validation functions:**
- `validate_clip(clip: Clip) -> List[ClipValidationError]`
- `validate_clips(clips: List[Clip]) -> List[Tuple[int, ClipValidationError]]`

**FFmpeg command types:**
- `FFmpegCommand` — Builder for FFmpeg argument arrays
- `Filter` — Single FFmpeg filter
- `FilterChain` — Sequence of filters for one stream
- `FilterGraph` — Complete filter graph with multiple chains
- `DrawtextBuilder` — Text overlay builder
- `SpeedControl` — Video speed/tempo builder

**FFmpeg filter functions:**
- `scale_filter(width: int, height: int) -> Filter`
- `concat_filter(video_count: int, audio_count: int) -> Filter`

**Audio building types:**
- `VolumeBuilder` — Audio volume adjustment builder
- `AfadeBuilder` — Audio fade-in/out builder
- `AmixBuilder` — Audio mixing builder
- `DuckingPattern` — Audio ducking pattern
- `TrackAudioConfig` — Per-track audio configuration
- `AudioMixSpec` — Complete audio mix specification

**Transition types:**
- `TransitionType` — Enum of transition types (Fade, Xfade, etc.)
- `FadeBuilder` — Fade transition builder
- `XfadeBuilder` — Cross-fade transition builder
- `AcrossfadeBuilder` — Audio cross-fade builder

**Layout types:**
- `LayoutPosition` — Normalized (0.0-1.0) position and dimensions
- `LayoutPreset` — Enumerated layout presets (PipTopLeft, SideBySide, Grid2x2, etc.)

**Composition functions (registered via module functions):**
- Via `compose::overlay::register(m)` — Overlay and scale helpers
- Via `compose::timeline::register(m)` — Composition timeline builders
- Via `compose::graph::register(m)` — Graph composition builders
- Via `batch::register(m)` — Batch progress calculation

**Sanitization functions:**
- `escape_filter_text(text: str) -> str` — Escape FFmpeg filter special characters
- `validate_path(path: str) -> None` — Validate file path safety
- `validate_volume(volume: float) -> float` — Validate audio volume (0.0-10.0)
- `validate_video_codec(codec: str) -> str` — Whitelist validate video codec
- `validate_audio_codec(codec: str) -> str` — Whitelist validate audio codec
- `validate_preset(preset: str) -> str` — Whitelist validate encoding preset

**Custom exceptions:**
- `ValidationError` — Raised by clip validation
- `CommandError` — Raised by FFmpeg command building
- `SanitizationError` — Raised by input sanitization
- `LayoutError` — Raised by layout validation

## Dependencies

### Internal Crate Dependencies

- `batch` — Batch render progress types
- `clip` — Clip representation and validation
- `clip::validation` — ClipValidationError struct
- `compose::overlay` — Overlay filter builders
- `compose::timeline` — Composition timeline builders
- `compose::graph` — Composition graph builders
- `ffmpeg` — FFmpeg command building
- `ffmpeg::audio` — Audio building types
- `ffmpeg::drawtext` — Text overlay builders
- `ffmpeg::filter` — Filter and FilterGraph types
- `ffmpeg::speed` — Speed control builders
- `ffmpeg::transitions` — Transition builders
- `layout::position` — LayoutPosition struct
- `layout::preset` — LayoutPreset enum
- `sanitize` — Input sanitization functions
- `timeline` — Timeline type exports

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings framework (prelude module for attributes)
- **pyo3_stub_gen** — Stub generator for .pyi files

## Key Implementation Details

### Module Registration Pattern

The `_core` module follows the standard PyO3 pattern:

1. Global options are added first (`health_check` function)
2. Types are registered with `m.add_class::<T>()`
3. Functions are registered with `m.add_function(wrap_pyfunction!(...))`
4. Functions from submodules are registered via their `register(m)` functions
5. Custom exceptions are registered with `m.add()` to make them Python-accessible

### Custom Exception Creation

Uses the `pyo3::create_exception!` macro to define custom exception types:
```rust
pyo3::create_exception!(stoat_ferret_core, ValidationError, pyo3::exceptions::PyException);
```

Each exception is a Python-level type that can be caught in Python code.

### Stub Generation

The `stub_info()` function provides metadata for the `pyo3_stub_gen` tool to generate type stubs:
- Reads `pyproject.toml` from the project root (not from CARGO_MANIFEST_DIR)
- Navigates: `rust/stoat_ferret_core/` → `rust/` → project root
- Generates `_core.pyi` with complete type signatures

## Relationships

**Used by:**
- Python code that imports from `stoat_ferret_core._core`
- Type stubs in `_core.pyi` generated by `cargo run --bin stub_gen`

**Uses:**
- All submodules listed in Internal Crate Dependencies
- PyO3 for Python binding infrastructure

## Testing

The `health_check()` function includes a unit test:

```rust
#[test]
fn test_health_check() {
    assert_eq!(health_check(), "stoat_ferret_core OK");
}
```

This verifies the module initialization path and is used as a smoke test in CI.

## Notes

- **Exception Distinction:** The `ValidationError` exception (from `pyo3::create_exception!`) is distinct from the `ClipValidationError` struct (a data type with field information). Python code catches the exception type; the struct is used for detailed error reporting.
- **Naming Convention:** Python-visible exception names do not have a "Py" prefix (unlike internal Rust wrapper types). The exception is registered directly as `ValidationError` in Python.
- **Stub Path:** The crate is designed to be built with `maturin develop` from the project root, not with `--manifest-path`, to correctly generate stub files.
