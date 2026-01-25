# Implementation Plan: Rust Workspace

## Step 1: Create Rust Crate Structure
```bash
mkdir -p rust/stoat_ferret_core/src/bin
touch rust/stoat_ferret_core/Cargo.toml
touch rust/stoat_ferret_core/src/lib.rs
```

## Step 2: Configure Cargo.toml
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

## Step 3: Create lib.rs with PyO3 Module
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
Create `src/bin/stub_gen.rs` to generate .pyi files.

## Step 5: Update pyproject.toml
Add maturin configuration:
```toml
[tool.maturin]
python-source = "src"
module-name = "stoat_ferret_core._core"
features = ["pyo3/extension-module"]
```

## Step 6: Create Python Wrapper
Create `src/stoat_ferret_core/__init__.py` that imports from `._core`.

## Step 7: Create stubs Directory
```bash
mkdir -p stubs
cargo run --bin stub_gen
```

## Step 8: Verify Build
```bash
maturin develop
python -c "from stoat_ferret_core import health_check; print(health_check())"
cargo test
cargo clippy -- -D warnings
```

## Verification
- Python import succeeds
- health_check() returns expected string
- Rust tests pass
- Clippy clean