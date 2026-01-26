//! stoat_ferret_core - Rust-powered video editing primitives.
//!
//! This crate provides the computational core for the stoat-and-ferret video editor,
//! exposing functions to Python via PyO3 bindings.
//!
//! # Modules
//!
//! - [`timeline`] - Frame-accurate timeline position and duration calculations
//! - [`clip`] - Video clip representation and validation
//! - [`ffmpeg`] - FFmpeg command building and argument construction
//! - [`sanitize`] - Input sanitization and validation for FFmpeg commands

use pyo3::prelude::*;
use pyo3_stub_gen::{define_stub_info_gatherer, derive::gen_stub_pyfunction};

pub mod clip;
pub mod ffmpeg;
pub mod sanitize;
pub mod timeline;

// Define custom Python exceptions for domain errors
pyo3::create_exception!(
    stoat_ferret_core,
    ValidationError,
    pyo3::exceptions::PyException
);
pyo3::create_exception!(
    stoat_ferret_core,
    CommandError,
    pyo3::exceptions::PyException
);
pyo3::create_exception!(
    stoat_ferret_core,
    SanitizationError,
    pyo3::exceptions::PyException
);

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

    // Register timeline types
    m.add_class::<timeline::FrameRate>()?;
    m.add_class::<timeline::Position>()?;
    m.add_class::<timeline::Duration>()?;
    m.add_class::<timeline::TimeRange>()?;

    // Register FFmpeg command builder types
    m.add_class::<ffmpeg::FFmpegCommand>()?;
    m.add_class::<ffmpeg::filter::Filter>()?;
    m.add_class::<ffmpeg::filter::FilterChain>()?;
    m.add_class::<ffmpeg::filter::FilterGraph>()?;

    // Register FFmpeg filter helper functions
    m.add_function(wrap_pyfunction!(ffmpeg::filter::py_scale_filter, m)?)?;
    m.add_function(wrap_pyfunction!(ffmpeg::filter::py_concat_filter, m)?)?;

    // Register sanitization functions
    m.add_function(wrap_pyfunction!(sanitize::py_escape_filter_text, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize::py_validate_path, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize::py_validate_crf, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize::py_validate_speed, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize::py_validate_volume, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize::py_validate_video_codec, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize::py_validate_audio_codec, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize::py_validate_preset, m)?)?;

    // Register custom exception types
    m.add("ValidationError", m.py().get_type::<ValidationError>())?;
    m.add("CommandError", m.py().get_type::<CommandError>())?;
    m.add("SanitizationError", m.py().get_type::<SanitizationError>())?;

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
