# Implementation Plan: Rust Workspace

## Step 1: Create Rust Crate Structure
```bash
mkdir -p rust/stoat_ferret_core/src/bin
```

## Step 2: Create Cargo.toml
`rust/stoat_ferret_core/Cargo.toml`:
```toml
[package]
name = "stoat_ferret_core"
version = "0.1.0"
edition = "2021"

[lib]
name = "stoat_ferret_core"
crate-type = ["cdylib", "rlib"]

[dependencies]
pyo3 = { version = "0.23", features = ["abi3-py310"] }
pyo3-stub-gen = "0.17"

[dev-dependencies]
proptest = "1.0"
```

## Step 3: Create lib.rs
`rust/stoat_ferret_core/src/lib.rs`:
```rust
use pyo3::prelude::*;
use pyo3_stub_gen::{define_stub_info_gatherer, derive::gen_stub_pyfunction};

#[gen_stub_pyfunction]
#[pyfunction]
fn health_check() -> String {
    "stoat_ferret_core OK".to_string()
}

#[pymodule]
fn _core(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(health_check, m)?)?;
    Ok(())
}

define_stub_info_gatherer!(stub_info);
```

## Step 4: Create Stub Generator Binary
`rust/stoat_ferret_core/src/bin/stub_gen.rs`:
```rust
use pyo3_stub_gen::Result;

fn main() -> Result<()> {
    let stub = stoat_ferret_core::stub_info()?;
    stub.generate()?;
    Ok(())
}
```

## Step 5: Update pyproject.toml
Add maturin configuration:
```toml
[tool.maturin]
python-source = "src"
module-name = "stoat_ferret_core._core"
features = ["pyo3/extension-module"]
manifest-path = "rust/stoat_ferret_core/Cargo.toml"
```

## Step 6: Create Python Wrapper
`src/stoat_ferret_core/__init__.py`:
```python
"""stoat_ferret_core - Rust-powered video editing primitives."""
from stoat_ferret_core._core import health_check

__all__ = ["health_check"]
```

## Step 7: Create rustfmt.toml
`rust/stoat_ferret_core/rustfmt.toml`:
```toml
edition = "2021"
max_width = 100
```

## Step 8: Generate Stubs
```bash
mkdir -p stubs/stoat_ferret_core
cd rust/stoat_ferret_core
cargo run --bin stub_gen
mv stoat_ferret_core.pyi ../../stubs/stoat_ferret_core/__init__.pyi
```

## Step 9: Configure mypy to Use Stubs
Add to `pyproject.toml`:
```toml
[tool.mypy]
mypy_path = "stubs"
```

## Step 10: Verify Build
```bash
maturin develop
python -c "from stoat_ferret_core import health_check; print(health_check())"
cargo test --manifest-path rust/stoat_ferret_core/Cargo.toml
cargo clippy --manifest-path rust/stoat_ferret_core/Cargo.toml -- -D warnings
```

## Verification
- Python import succeeds
- health_check() returns "stoat_ferret_core OK"
- Rust tests pass
- Clippy clean