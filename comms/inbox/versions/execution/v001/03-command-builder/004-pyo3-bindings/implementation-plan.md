# Implementation Plan: PyO3 Bindings

## Step 1: Update lib.rs with PyO3 Annotations
```rust
use pyo3::prelude::*;
use pyo3_stub_gen::{define_stub_info_gatherer, derive::*};

mod timeline;
mod ffmpeg;
mod sanitize;
mod clip;

// Export timeline types
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct PyPosition {
    inner: timeline::Position,
}

#[gen_stub_pymethods]
#[pymethods]
impl PyPosition {
    #[new]
    fn new(frames: u64) -> Self {
        Self { inner: timeline::Position::from_frames(frames) }
    }

    #[staticmethod]
    fn from_seconds(seconds: f64, fps: &PyFrameRate) -> Self {
        Self { inner: timeline::Position::from_seconds(seconds, fps.inner) }
    }

    fn to_seconds(&self, fps: &PyFrameRate) -> f64 {
        self.inner.to_seconds(fps.inner)
    }

    #[getter]
    fn frames(&self) -> u64 {
        self.inner.frames()
    }
}
```

## Step 2: Expose FrameRate Constants
```rust
#[gen_stub_pyclass]
#[pyclass]
pub struct PyFrameRate {
    inner: timeline::FrameRate,
}

#[gen_stub_pymethods]
#[pymethods]
impl PyFrameRate {
    #[staticmethod]
    fn fps_24() -> Self {
        Self { inner: timeline::FrameRate::FPS_24 }
    }

    #[staticmethod]
    fn fps_30() -> Self {
        Self { inner: timeline::FrameRate::FPS_30 }
    }

    // etc.
}
```

## Step 3: Expose Command Builder
```rust
#[gen_stub_pyclass]
#[pyclass]
pub struct PyFFmpegCommand {
    inner: ffmpeg::FFmpegCommand,
}

#[gen_stub_pymethods]
#[pymethods]
impl PyFFmpegCommand {
    #[new]
    fn new() -> Self {
        Self { inner: ffmpeg::FFmpegCommand::new() }
    }

    fn overwrite(&mut self, yes: bool) {
        self.inner = self.inner.clone().overwrite(yes);
    }

    fn input(&mut self, path: &str) -> PyInputBuilder {
        // Return builder for chaining
        ...
    }

    fn build(&self) -> PyResult<Vec<String>> {
        self.inner.build().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string())
        })
    }
}
```

## Step 4: Define Python Exceptions
```rust
use pyo3::create_exception;

create_exception!(stoat_ferret_core, ValidationError, pyo3::exceptions::PyException);
create_exception!(stoat_ferret_core, CommandError, pyo3::exceptions::PyException);
create_exception!(stoat_ferret_core, SanitizationError, pyo3::exceptions::PyException);

#[pymodule]
fn _core(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<PyPosition>()?;
    m.add_class::<PyFrameRate>()?;
    m.add_class::<PyFFmpegCommand>()?;
    m.add("ValidationError", m.py().get_type::<ValidationError>())?;
    m.add("CommandError", m.py().get_type::<CommandError>())?;
    Ok(())
}
```

## Step 5: Create Python Wrapper
Create `src/stoat_ferret_core/__init__.py`:

```python
"""stoat_ferret_core - Rust-powered video editing primitives."""
from __future__ import annotations

from stoat_ferret_core._core import (
    PyPosition as Position,
    PyFrameRate as FrameRate,
    PyFFmpegCommand as FFmpegCommand,
    ValidationError,
    CommandError,
)

__all__ = [
    "Position",
    "FrameRate",
    "FFmpegCommand",
    "ValidationError",
    "CommandError",
]
```

## Step 6: Generate Type Stubs
```bash
cargo run --bin stub_gen
# Move generated stubs to stubs/ directory
mv stoat_ferret_core.pyi stubs/stoat_ferret_core/__init__.pyi
```

## Step 7: Configure mypy to Use Stubs
In `pyproject.toml`:
```toml
[tool.mypy]
mypy_path = "stubs"
```

## Step 8: Write Integration Tests
```python
# tests/test_core_integration.py
from stoat_ferret_core import Position, FrameRate, FFmpegCommand

def test_position_roundtrip():
    fps = FrameRate.fps_24()
    pos = Position.from_seconds(1.0, fps)
    assert pos.frames() == 24
    assert abs(pos.to_seconds(fps) - 1.0) < 0.001

def test_command_builder():
    cmd = FFmpegCommand()
    cmd.overwrite(True)
    cmd.input("input.mp4")
    cmd.output("output.mp4")
    args = cmd.build()
    assert "-y" in args
    assert "-i" in args
```

## Verification
- `python -c "from stoat_ferret_core import Position"` works
- `uv run mypy src/` passes with stubs
- Integration tests pass
- IDE shows autocomplete for imported types