# Stub Generation Analysis

## Binary Setup

Location: `rust/stoat_ferret_core/src/bin/stub_gen.rs`

```rust
use pyo3_stub_gen::Result;

fn main() -> Result<()> {
    let stub = stoat_ferret_core::stub_info()?;
    stub.generate()?;
    Ok(())
}
```

This is the standard pyo3-stub-gen pattern. The binary:
1. Calls `stub_info()` defined by `define_stub_info_gatherer!(stub_info)` in lib.rs
2. Generates `.pyi` files from annotated Rust code

## Configuration

### Cargo.toml

```toml
[dependencies]
pyo3 = { version = "0.26", features = ["abi3-py310"] }
pyo3-stub-gen = "0.17"

[lib]
crate-type = ["cdylib", "rlib"]  # rlib needed for stub generator binary
```

The `rlib` crate type is required for the binary to link against the library.

### lib.rs Annotations

```rust
use pyo3_stub_gen::{define_stub_info_gatherer, derive::gen_stub_pyfunction};

// On module functions:
#[gen_stub_pyfunction]
#[pyfunction]
fn health_check() -> String { ... }

// At module end:
define_stub_info_gatherer!(stub_info);
```

### Type Annotations

Types use `gen_stub_pyclass`:

```rust
use pyo3_stub_gen::derive::gen_stub_pyclass;

#[gen_stub_pyclass]
#[pyclass]
pub struct TimeRange { ... }
```

## Current Stubs

Location: `stubs/stoat_ferret_core/`

Structure:
```
stubs/stoat_ferret_core/
├── __init__.pyi
└── _core.pyi
```

The `_core.pyi` file is **manually maintained**, not auto-generated. It's 632 lines covering:
- Custom exceptions (ValidationError, CommandError, SanitizationError)
- Timeline types (FrameRate, Position, Duration, TimeRange)
- FFmpeg types (FFmpegCommand, Filter, FilterChain, FilterGraph)
- Helper functions (scale_filter, concat_filter)
- Sanitization functions (8 validators)

## Stub vs Rust Discrepancies

The manual stubs have diverged from the actual Rust implementation:

### Methods in stubs that DON'T exist in Rust:

| Stub Method | Actual Rust |
|-------------|-------------|
| `Position.from_timecode()` | Does not exist |
| `Position.__add__(Duration)` | Does not exist |
| `Position.__sub__(Duration)` | Does not exist |
| `Duration.__add__(Duration)` | Does not exist |
| `FrameRate.ntsc_30()` | Use `fps_29_97()` |
| `FrameRate.ntsc_60()` | Use `fps_59_94()` |
| `FrameRate.as_float()` | Use `fps` property |
| `Duration.between(start, end)` | Use `between_positions(start, end)` |
| `Position.from_frames(frames)` | Constructor is `Position(frames)` |
| `Duration.from_frames(frames)` | Constructor is `Duration(frames)` |

### Methods in Rust missing from stubs:

| Rust Method | In Stubs |
|-------------|----------|
| `Position.from_secs(seconds, fps)` | No |
| `Position.as_secs(fps)` | No |
| `Position.zero()` | No |
| `Duration.from_secs(seconds, fps)` | No |
| `Duration.as_secs(fps)` | No |
| `Duration.end_pos(start)` | No |
| `Duration.zero()` | No |
| `FrameRate.fps_23_976()` | No |
| `FrameRate.fps_50()` | No |

## Running Stub Generation

```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```

This generates stubs to the current directory. Output path can be configured.

## CI Verification Requirements

For CI to verify stubs match the Rust API:

### Option 1: Regenerate and Diff

```yaml
- name: Generate stubs
  run: |
    cd rust/stoat_ferret_core
    cargo run --bin stub_gen -- --output-dir /tmp/generated_stubs

- name: Compare stubs
  run: |
    diff -r /tmp/generated_stubs stubs/stoat_ferret_core
```

### Option 2: Check stubs compile with mypy

```yaml
- name: Type check against stubs
  run: |
    uv run mypy tests/ --strict
```

### Option 3: Runtime verification

```python
# tests/test_stub_compliance.py
def test_all_stub_methods_exist():
    """Verify stub methods exist at runtime."""
    from stoat_ferret_core._core import Position

    assert hasattr(Position, 'from_secs')
    assert callable(Position.from_secs)
```

### Recommended Approach

1. Keep stubs auto-generated (not manual)
2. Run `cargo run --bin stub_gen` as build step
3. Commit generated stubs to repo
4. CI verifies stubs are up-to-date via diff
5. mypy uses committed stubs for type checking
