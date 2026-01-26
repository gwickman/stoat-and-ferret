//! Stub generator binary for creating Python type stubs.
//!
//! Run with `cargo run --bin stub_gen` to generate type stubs for the module.

use pyo3_stub_gen::Result;

fn main() -> Result<()> {
    let stub = stoat_ferret_core::stub_info()?;
    stub.generate()?;
    Ok(())
}
