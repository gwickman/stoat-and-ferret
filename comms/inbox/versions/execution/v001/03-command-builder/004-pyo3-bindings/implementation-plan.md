# Implementation Plan: PyO3 Bindings

## Step 1: Add PyO3 Annotations to Timeline Types
Add `#[gen_stub_pyclass]`, `#[gen_stub_pymethods]` to Position, Duration, FrameRate, TimeRange.

## Step 2: Add PyO3 Annotations to FFmpeg Types
Add annotations to FFmpegCommand, Filter, FilterChain, FilterGraph.

## Step 3: Define Python Exceptions
```rust
use pyo3::create_exception;

create_exception!(stoat_ferret_core, ValidationError, pyo3::exceptions::PyException);
create_exception!(stoat_ferret_core, CommandError, pyo3::exceptions::PyException);
create_exception!(stoat_ferret_core, SanitizationError, pyo3::exceptions::PyException);
```

## Step 4: Update Module Registration
```rust
#[pymodule]
fn _core(m: &Bound<PyModule>) -> PyResult<()> {
    // Timeline
    m.add_class::<Position>()?;
    m.add_class::<Duration>()?;
    m.add_class::<FrameRate>()?;
    m.add_class::<TimeRange>()?;
    
    // FFmpeg
    m.add_class::<FFmpegCommand>()?;
    m.add_class::<Filter>()?;
    m.add_class::<FilterChain>()?;
    m.add_class::<FilterGraph>()?;
    
    // Exceptions
    m.add("ValidationError", m.py().get_type::<ValidationError>())?;
    m.add("CommandError", m.py().get_type::<CommandError>())?;
    m.add("SanitizationError", m.py().get_type::<SanitizationError>())?;
    
    // Sanitization functions
    m.add_function(wrap_pyfunction!(escape_filter_text, m)?)?;
    m.add_function(wrap_pyfunction!(validate_path, m)?)?;
    
    Ok(())
}
```

## Step 5: Update Python Wrapper
`src/stoat_ferret_core/__init__.py`:
```python
"""stoat_ferret_core - Rust-powered video editing primitives."""
from stoat_ferret_core._core import (
    # Timeline
    Position,
    Duration,
    FrameRate,
    TimeRange,
    # FFmpeg
    FFmpegCommand,
    Filter,
    FilterChain,
    FilterGraph,
    # Exceptions
    ValidationError,
    CommandError,
    SanitizationError,
    # Functions
    escape_filter_text,
    validate_path,
    health_check,
)

__all__ = [
    "Position",
    "Duration",
    "FrameRate",
    "TimeRange",
    "FFmpegCommand",
    "Filter",
    "FilterChain",
    "FilterGraph",
    "ValidationError",
    "CommandError",
    "SanitizationError",
    "escape_filter_text",
    "validate_path",
    "health_check",
]
```

## Step 6: Regenerate Stubs
```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
cp stoat_ferret_core.pyi ../../stubs/stoat_ferret_core/__init__.pyi
```

## Step 7: Integration Tests
```python
# tests/test_core_integration.py
from stoat_ferret_core import (
    Position, Duration, FrameRate, TimeRange,
    FFmpegCommand, Filter, FilterChain, FilterGraph,
    escape_filter_text, validate_path,
)

def test_position_roundtrip():
    fps = FrameRate.fps_24()
    pos = Position.from_seconds(1.0, fps)
    assert pos.frames() == 24
    assert abs(pos.to_seconds(fps) - 1.0) < 0.001

def test_command_builder():
    cmd = FFmpegCommand()
    cmd = cmd.overwrite(True).input("in.mp4").output("out.mp4")
    args = cmd.build()
    assert "-y" in args
    assert "-i" in args
    assert "in.mp4" in args
    assert "out.mp4" in args

def test_filter_chain():
    chain = FilterChain().input("0:v").filter(Filter.scale(1920, 1080)).output("v")
    result = str(chain)
    assert "[0:v]" in result
    assert "scale" in result
    assert "[v]" in result

def test_escape():
    assert escape_filter_text("hello:world") == "hello\\:world"
```

## Verification
- Python imports succeed
- Method chaining works
- mypy passes
- Integration tests pass