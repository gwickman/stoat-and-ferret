# Implementation Plan: Clip Bindings

## Step 1: Add PyO3 to Clip Struct
Edit `rust/stoat_ferret_core/src/clip/mod.rs`:

```rust
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Clip {
    #[pyo3(get)]
    pub source_path: String,
    #[pyo3(get)]
    pub in_point: Position,
    #[pyo3(get)]
    pub out_point: Position,
    #[pyo3(get)]
    pub source_duration: Option<Duration>,
}

#[pymethods]
impl Clip {
    #[new]
    fn py_new(
        source_path: String,
        in_point: Position,
        out_point: Position,
        source_duration: Option<Duration>,
    ) -> Self {
        Self { source_path, in_point, out_point, source_duration }
    }

    #[pyo3(name = "duration")]
    fn py_duration(&self) -> Option<Duration> {
        // existing implementation
    }
}
```

## Step 2: Add PyO3 to ValidationError Struct
Edit `rust/stoat_ferret_core/src/clip/validation.rs`:

```rust
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// Validation error for clip data.
/// 
/// Note: This is distinct from the ValidationError exception type.
/// This struct provides detailed validation failure information.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ValidationError {
    #[pyo3(get)]
    pub field: String,
    #[pyo3(get)]
    pub message: String,
    #[pyo3(get)]
    pub actual: Option<String>,
    #[pyo3(get)]
    pub expected: Option<String>,
}

#[pymethods]
impl ValidationError {
    #[new]
    fn py_new(field: String, message: String) -> Self {
        Self { field, message, actual: None, expected: None }
    }

    #[staticmethod]
    fn with_values(field: String, message: String, actual: String, expected: String) -> Self {
        Self { field, message, actual: Some(actual), expected: Some(expected) }
    }
}
```

## Step 3: Expose Validation Functions
```rust
use pyo3_stub_gen::derive::gen_stub_pyfunction;

#[gen_stub_pyfunction]
#[pyfunction]
fn validate_clip(clip: &Clip) -> Vec<ValidationError> {
    // existing logic adapted
}
```

## Step 4: Register in lib.rs
```rust
// Register clip types
m.add_class::<clip::Clip>()?;
m.add_class::<clip::validation::ValidationError>()?;
m.add_function(wrap_pyfunction!(clip::validation::validate_clip, m)?)?;
```

## Step 5: Regenerate Stubs
```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```

## Step 6: Add Integration Tests
Add to `tests/test_pyo3_bindings.py`:

```python
class TestClip:
    def test_clip_construction(self):
        from stoat_ferret_core import Clip, Position
        clip = Clip("video.mp4", Position(0), Position(100), None)
        assert clip.source_path == "video.mp4"
        assert clip.in_point.frames == 0
        assert clip.out_point.frames == 100

    def test_clip_duration(self):
        from stoat_ferret_core import Clip, Position, Duration
        clip = Clip("video.mp4", Position(10), Position(50), None)
        dur = clip.duration()
        assert dur is not None
        assert dur.frames == 40


class TestValidationErrorStruct:
    """Tests for ValidationError struct (not the exception)."""
    
    def test_validation_error_basic(self):
        from stoat_ferret_core import ValidationError
        err = ValidationError("in_point", "must be non-negative")
        assert err.field == "in_point"
        assert err.message == "must be non-negative"
        assert err.actual is None
        assert err.expected is None

    def test_validation_error_with_values(self):
        from stoat_ferret_core import ValidationError
        err = ValidationError.with_values(
            "in_point", "must be before out_point", "100", "< 50"
        )
        assert err.field == "in_point"
        assert err.actual == "100"
        assert err.expected == "< 50"
```

## Step 7: Update TestModuleExports
Add to expected exports:
- `Clip`
- `ValidationError` (the struct - note this shadows the exception import)
- `validate_clip`

## Verification
- `cargo test` passes
- `uv run pytest tests/test_pyo3_bindings.py -v` passes
- `from stoat_ferret_core import Clip, ValidationError` works