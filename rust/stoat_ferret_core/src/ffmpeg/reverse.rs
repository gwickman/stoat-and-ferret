//! Reverse filter builder for FFmpeg video and audio reversal.
//!
//! This module provides [`ReverseBuilder`] for constructing FFmpeg `reverse` (video)
//! and `areverse` (audio) filters. Both filters buffer the entire segment in memory,
//! so the effect must be used only on short clips — duration enforcement is handled
//! by the Python application layer.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::reverse::ReverseBuilder;
//!
//! let builder = ReverseBuilder::new();
//! let video = builder.video_filter();
//! assert_eq!(video.to_string(), "reverse");
//!
//! let audio = builder.audio_filter();
//! assert_eq!(audio.to_string(), "areverse");
//! ```

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::filter::Filter;

/// Type-safe builder for FFmpeg video and audio reversal filters.
///
/// Generates the `reverse` filter for video and the `areverse` filter for audio.
/// Both filters buffer the entire clip segment in memory — use only on short clips.
/// Maximum duration enforcement is handled by the application layer via
/// `STOAT_REVERSE_MAX_DURATION_S`.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ReverseBuilder {}

impl ReverseBuilder {
    /// Creates a new `ReverseBuilder`.
    pub fn new() -> Self {
        Self {}
    }

    /// Generates the `reverse` filter for video reversal.
    #[must_use]
    pub fn video_filter(&self) -> Filter {
        Filter::new("reverse".to_string())
    }

    /// Generates the `areverse` filter for audio reversal.
    #[must_use]
    pub fn audio_filter(&self) -> Filter {
        Filter::new("areverse".to_string())
    }
}

impl Default for ReverseBuilder {
    fn default() -> Self {
        Self::new()
    }
}

// ========== PyO3 bindings ==========

#[pymethods]
impl ReverseBuilder {
    /// Creates a new ReverseBuilder.
    ///
    /// No parameters are required — the reverse and areverse filters are
    /// fixed-name filters with no user-configurable options.
    ///
    /// The builder does not enforce the duration limit; that check is performed
    /// by the effect application endpoint using `STOAT_REVERSE_MAX_DURATION_S`.
    #[new]
    fn py_new() -> Self {
        Self::new()
    }

    /// Generates the `reverse` video reversal filter.
    ///
    /// Returns:
    ///     A Filter with the string `reverse`.
    #[pyo3(name = "video_filter")]
    fn py_video_filter(&self) -> Filter {
        self.video_filter()
    }

    /// Generates the `areverse` audio reversal filter.
    ///
    /// Returns:
    ///     A Filter with the string `areverse`.
    #[pyo3(name = "audio_filter")]
    fn py_audio_filter(&self) -> Filter {
        self.audio_filter()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        "ReverseBuilder()".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_video_filter() {
        let builder = ReverseBuilder::new();
        let filter = builder.video_filter();
        assert_eq!(filter.to_string(), "reverse");
    }

    #[test]
    fn test_audio_filter() {
        let builder = ReverseBuilder::new();
        let filter = builder.audio_filter();
        assert_eq!(filter.to_string(), "areverse");
    }

    #[test]
    fn test_default_construction() {
        let builder = ReverseBuilder::default();
        assert_eq!(builder.video_filter().to_string(), "reverse");
        assert_eq!(builder.audio_filter().to_string(), "areverse");
    }

    #[test]
    fn test_clone() {
        let builder = ReverseBuilder::new();
        let cloned = builder.clone();
        assert_eq!(cloned.video_filter().to_string(), "reverse");
    }

    #[test]
    fn test_repr() {
        let builder = ReverseBuilder::new();
        assert_eq!(builder.__repr__(), "ReverseBuilder()");
    }

    // ========== PyO3 binding tests ==========

    use pyo3::prelude::*;

    #[test]
    fn test_pyo3_reverse_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let rb = Bound::new(py, ReverseBuilder::new()).unwrap();

            let video: String = rb
                .call_method0("video_filter")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(video, "reverse");

            let audio: String = rb
                .call_method0("audio_filter")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(audio, "areverse");

            let repr: String = rb.call_method0("__repr__").unwrap().extract().unwrap();
            assert_eq!(repr, "ReverseBuilder()");
        });
    }
}
