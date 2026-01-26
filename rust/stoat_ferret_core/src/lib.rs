//! stoat_ferret_core - Rust-powered video editing primitives.
//!
//! This crate provides the computational core for the stoat-and-ferret video editor,
//! exposing functions to Python via PyO3 bindings.

use pyo3::prelude::*;
use pyo3_stub_gen::{define_stub_info_gatherer, derive::gen_stub_pyfunction};

/// Performs a health check to verify the Rust module is loaded correctly.
///
/// Returns a status string indicating the module is operational.
#[gen_stub_pyfunction]
#[pyfunction]
fn health_check() -> String {
    "stoat_ferret_core OK".to_string()
}

/// The Python module definition for stoat_ferret_core._core
#[pymodule]
fn _core(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(health_check, m)?)?;
    Ok(())
}

define_stub_info_gatherer!(stub_info);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_health_check() {
        assert_eq!(health_check(), "stoat_ferret_core OK");
    }
}
