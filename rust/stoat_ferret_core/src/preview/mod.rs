//! Preview filter graph simplification.
//!
//! This module provides quality-level-based simplification of FFmpeg filter
//! graphs for real-time preview playback. Expensive filters are removed or
//! simplified at lower quality levels to improve performance.

pub mod simplify;

use pyo3::prelude::*;

/// Preview quality level for filter simplification.
///
/// Controls how aggressively filters are simplified:
/// - **Draft**: Removes all expensive filters for fastest preview
/// - **Medium**: Removes most expensive filters, keeping some visual fidelity
/// - **High**: Preserves all filters unchanged (production quality)
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PreviewQuality {
    /// Fastest preview: removes all expensive filters.
    Draft,
    /// Balanced preview: removes most expensive filters.
    Medium,
    /// Full quality: preserves all filters unchanged.
    High,
}

/// Registers preview module types and functions with the Python module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PreviewQuality>()?;
    m.add_function(wrap_pyfunction!(simplify::py_is_expensive_filter, m)?)?;
    m.add_function(wrap_pyfunction!(simplify::py_simplify_filter_chain, m)?)?;
    m.add_function(wrap_pyfunction!(simplify::py_simplify_filter_graph, m)?)?;
    Ok(())
}
