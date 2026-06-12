//! Freeze-frame filter builder for FFmpeg.
//!
//! This module provides [`FreezeFrameBuilder`] for constructing an FFmpeg
//! filter that holds a chosen frame and extends the clip duration using
//! the `freezeframes` and `tpad` filters.
//!
//! # Filter string format
//!
//! `freezeframes=first={F}:last={F}:replace={F},tpad=stop_duration={H}`
//!
//! where F = `frame_number` (0-indexed) and H = `hold_duration_s` (seconds).
//!
//! # Minimum FFmpeg version
//!
//! FFmpeg 4.0+ is required for the `freezeframes` and `tpad` filters.
//!
//! # Mid-clip freeze note
//!
//! This builder uses `tpad`-at-end to extend the clip. For a hold in the middle
//! of the output timeline, use split (BL-445) + freeze composition.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::freeze::FreezeFrameBuilder;
//!
//! // Freeze frame 5 for 2.5 seconds
//! let builder = FreezeFrameBuilder::new(5, 2.5).unwrap();
//! assert_eq!(
//!     builder.build().to_string(),
//!     "freezeframes=first=5:last=5:replace=5,tpad=stop_duration=2.5"
//! );
//!
//! // Integer hold duration strips the decimal
//! let builder = FreezeFrameBuilder::new(0, 2.0).unwrap();
//! assert_eq!(
//!     builder.build().to_string(),
//!     "freezeframes=first=0:last=0:replace=0,tpad=stop_duration=2"
//! );
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::filter::Filter;

/// Format a duration in seconds, stripping unnecessary trailing zeros.
///
/// For example: `2.0` → `"2"`, `2.5` → `"2.5"`, `2.123` → `"2.123"`.
fn format_duration(s: f64) -> String {
    if (s - s.round()).abs() < 1e-9 {
        format!("{}", s.round() as i64)
    } else {
        let st = format!("{s:.10}");
        let st = st.trim_end_matches('0');
        st.trim_end_matches('.').to_string()
    }
}

// ========== FreezeFrameBuilder ==========

/// Builder for FFmpeg freeze-frame filters.
///
/// Generates: `freezeframes=first={F}:last={F}:replace={F},tpad=stop_duration={H}`
///
/// The `tpad` filter extends the clip by `hold_duration_s` seconds. Frame bounds
/// validation (frame_number vs. clip duration) is enforced by the application layer.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct FreezeFrameBuilder {
    frame_number: u64,
    hold_duration_s: f64,
}

impl FreezeFrameBuilder {
    /// Creates a new `FreezeFrameBuilder`.
    ///
    /// # Errors
    ///
    /// Returns an error string if `hold_duration_s <= 0`.
    pub fn new(frame_number: u64, hold_duration_s: f64) -> Result<Self, String> {
        if hold_duration_s <= 0.0 {
            return Err(format!(
                "hold_duration_s must be > 0, got {hold_duration_s}"
            ));
        }
        Ok(Self {
            frame_number,
            hold_duration_s,
        })
    }

    /// Builds the FFmpeg filter string for freeze-frame.
    #[must_use]
    pub fn build(&self) -> Filter {
        Filter::new(format!(
            "freezeframes=first={0}:last={0}:replace={0},tpad=stop_duration={1}",
            self.frame_number,
            format_duration(self.hold_duration_s)
        ))
    }
}

// ========== PyO3 bindings ==========

#[pymethods]
impl FreezeFrameBuilder {
    /// Creates a new FreezeFrameBuilder.
    ///
    /// Args:
    ///     frame_number: 0-indexed frame to freeze. Must be within the clip duration
    ///         (validated by the application layer, not here).
    ///     hold_duration_s: Duration to hold the frozen frame in seconds. Must be > 0.
    ///
    /// Raises:
    ///     ValueError: If hold_duration_s is not > 0.
    #[new]
    fn py_new(frame_number: u64, hold_duration_s: f64) -> PyResult<Self> {
        Self::new(frame_number, hold_duration_s).map_err(PyValueError::new_err)
    }

    /// The 0-indexed frame number to freeze.
    #[getter]
    #[pyo3(name = "frame_number")]
    fn py_frame_number(&self) -> u64 {
        self.frame_number
    }

    /// The hold duration in seconds.
    #[getter]
    #[pyo3(name = "hold_duration_s")]
    fn py_hold_duration_s(&self) -> f64 {
        self.hold_duration_s
    }

    /// Builds the FFmpeg filter for freeze-frame.
    ///
    /// Returns:
    ///     A Filter with the freezeframes+tpad filter string.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    fn __repr__(&self) -> String {
        format!(
            "FreezeFrameBuilder(frame_number={}, hold_duration_s={})",
            self.frame_number,
            format_duration(self.hold_duration_s)
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_filter_string_integer_duration() {
        let b = FreezeFrameBuilder::new(5, 2.0).unwrap();
        assert_eq!(
            b.build().to_string(),
            "freezeframes=first=5:last=5:replace=5,tpad=stop_duration=2"
        );
    }

    #[test]
    fn test_filter_string_fractional_duration() {
        let b = FreezeFrameBuilder::new(5, 2.5).unwrap();
        assert_eq!(
            b.build().to_string(),
            "freezeframes=first=5:last=5:replace=5,tpad=stop_duration=2.5"
        );
    }

    #[test]
    fn test_filter_string_frame_zero() {
        let b = FreezeFrameBuilder::new(0, 1.0).unwrap();
        assert_eq!(
            b.build().to_string(),
            "freezeframes=first=0:last=0:replace=0,tpad=stop_duration=1"
        );
    }

    #[test]
    fn test_filter_string_large_frame_number() {
        let b = FreezeFrameBuilder::new(1200, 3.5).unwrap();
        let s = b.build().to_string();
        assert!(s.starts_with("freezeframes=first=1200:last=1200:replace=1200"));
        assert!(s.contains("tpad=stop_duration=3.5"));
    }

    #[test]
    fn test_invalid_duration_zero() {
        assert!(FreezeFrameBuilder::new(0, 0.0).is_err());
    }

    #[test]
    fn test_invalid_duration_negative() {
        assert!(FreezeFrameBuilder::new(0, -1.0).is_err());
    }

    #[test]
    fn test_format_duration_whole_number() {
        assert_eq!(format_duration(3.0), "3");
    }

    #[test]
    fn test_format_duration_fractional() {
        assert_eq!(format_duration(1.5), "1.5");
    }
}
