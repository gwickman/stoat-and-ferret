//! Preview filter graph simplification, cost estimation, and scale injection.
//!
//! This module provides quality-level-based simplification of FFmpeg filter
//! graphs for real-time preview playback. Expensive filters are removed or
//! simplified at lower quality levels to improve performance.
//!
//! Also provides cost estimation for auto-quality selection and scale filter
//! injection for resolution control.

pub mod cost;
pub mod scale;
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
    m.add_function(wrap_pyfunction!(cost::py_estimate_filter_cost, m)?)?;
    m.add_function(wrap_pyfunction!(cost::py_select_preview_quality, m)?)?;
    m.add_function(wrap_pyfunction!(scale::py_inject_preview_scale, m)?)?;
    Ok(())
}
