//! Frame rate representation using rational numbers.
//!
//! This module provides a [`FrameRate`] type that represents frame rates as
//! rational numbers (numerator/denominator) to avoid floating-point precision
//! issues in timeline calculations.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// A frame rate represented as a rational number (numerator/denominator).
///
/// Using rational representation allows for exact arithmetic without
/// floating-point precision loss. Common frame rates like 23.976 and 29.97
/// are represented exactly as 24000/1001 and 30000/1001 respectively.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::timeline::FrameRate;
///
/// // Use predefined constants for common rates
/// let fps_24 = FrameRate::FPS_24;
/// assert_eq!(fps_24.frames_per_second(), 24.0);
///
/// // Create custom frame rates
/// let custom = FrameRate::new(48, 1).unwrap();
/// assert_eq!(custom.frames_per_second(), 48.0);
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct FrameRate {
    numerator: u32,
    denominator: u32,
}

impl FrameRate {
    /// 23.976 fps (24000/1001) - NTSC film
    pub const FPS_23_976: Self = Self {
        numerator: 24000,
        denominator: 1001,
    };

    /// 24 fps - Cinema standard
    pub const FPS_24: Self = Self {
        numerator: 24,
        denominator: 1,
    };

    /// 25 fps - PAL standard
    pub const FPS_25: Self = Self {
        numerator: 25,
        denominator: 1,
    };

    /// 29.97 fps (30000/1001) - NTSC video
    pub const FPS_29_97: Self = Self {
        numerator: 30000,
        denominator: 1001,
    };

    /// 30 fps - Common web video
    pub const FPS_30: Self = Self {
        numerator: 30,
        denominator: 1,
    };

    /// 50 fps - PAL high frame rate
    pub const FPS_50: Self = Self {
        numerator: 50,
        denominator: 1,
    };

    /// 59.94 fps (60000/1001) - NTSC high frame rate
    pub const FPS_59_94: Self = Self {
        numerator: 60000,
        denominator: 1001,
    };

    /// 60 fps - Common high frame rate
    pub const FPS_60: Self = Self {
        numerator: 60,
        denominator: 1,
    };

    /// Creates a new frame rate from numerator and denominator.
    ///
    /// Returns `None` if denominator is zero.
    ///
    /// # Arguments
    ///
    /// * `numerator` - The numerator of the frame rate ratio
    /// * `denominator` - The denominator of the frame rate ratio (must be non-zero)
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::FrameRate;
    ///
    /// let fps = FrameRate::new(30, 1).unwrap();
    /// assert_eq!(fps.frames_per_second(), 30.0);
    ///
    /// // Zero denominator returns None
    /// assert!(FrameRate::new(30, 0).is_none());
    /// ```
    #[must_use]
    pub fn new(numerator: u32, denominator: u32) -> Option<Self> {
        if denominator == 0 {
            return None;
        }
        Some(Self {
            numerator,
            denominator,
        })
    }

    /// Returns the frame rate as a floating-point value.
    ///
    /// Note: This conversion may lose precision for fractional frame rates.
    /// For precise calculations, use the rational representation directly.
    #[must_use]
    pub fn frames_per_second(&self) -> f64 {
        f64::from(self.numerator) / f64::from(self.denominator)
    }

    /// Returns the numerator of the frame rate ratio.
    #[must_use]
    pub fn numerator(&self) -> u32 {
        self.numerator
    }

    /// Returns the denominator of the frame rate ratio.
    #[must_use]
    pub fn denominator(&self) -> u32 {
        self.denominator
    }
}

#[pymethods]
impl FrameRate {
    /// Creates a new frame rate from numerator and denominator.
    ///
    /// # Arguments
    ///
    /// * `numerator` - The numerator of the frame rate ratio
    /// * `denominator` - The denominator of the frame rate ratio (must be non-zero)
    ///
    /// # Raises
    ///
    /// ValueError: If denominator is zero
    #[new]
    fn py_new(numerator: u32, denominator: u32) -> PyResult<Self> {
        Self::new(numerator, denominator)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("denominator cannot be zero"))
    }

    /// Returns the frame rate as a floating-point value.
    #[getter]
    fn fps(&self) -> f64 {
        self.frames_per_second()
    }

    /// Returns the numerator of the frame rate ratio.
    #[getter]
    fn py_numerator(&self) -> u32 {
        self.numerator
    }

    /// Returns the denominator of the frame rate ratio.
    #[getter]
    fn py_denominator(&self) -> u32 {
        self.denominator
    }

    /// Returns a string representation of the frame rate.
    fn __repr__(&self) -> String {
        format!(
            "FrameRate({}/{} = {:.3} fps)",
            self.numerator,
            self.denominator,
            self.frames_per_second()
        )
    }

    /// Creates the 23.976 fps frame rate constant.
    #[staticmethod]
    fn fps_23_976() -> Self {
        Self::FPS_23_976
    }

    /// Creates the 24 fps frame rate constant.
    #[staticmethod]
    fn fps_24() -> Self {
        Self::FPS_24
    }

    /// Creates the 25 fps frame rate constant.
    #[staticmethod]
    fn fps_25() -> Self {
        Self::FPS_25
    }

    /// Creates the 29.97 fps frame rate constant.
    #[staticmethod]
    fn fps_29_97() -> Self {
        Self::FPS_29_97
    }

    /// Creates the 30 fps frame rate constant.
    #[staticmethod]
    fn fps_30() -> Self {
        Self::FPS_30
    }

    /// Creates the 50 fps frame rate constant.
    #[staticmethod]
    fn fps_50() -> Self {
        Self::FPS_50
    }

    /// Creates the 59.94 fps frame rate constant.
    #[staticmethod]
    fn fps_59_94() -> Self {
        Self::FPS_59_94
    }

    /// Creates the 60 fps frame rate constant.
    #[staticmethod]
    fn fps_60() -> Self {
        Self::FPS_60
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_frame_rate_constants() {
        assert_eq!(FrameRate::FPS_24.frames_per_second(), 24.0);
        assert_eq!(FrameRate::FPS_25.frames_per_second(), 25.0);
        assert_eq!(FrameRate::FPS_30.frames_per_second(), 30.0);
        assert_eq!(FrameRate::FPS_50.frames_per_second(), 50.0);
        assert_eq!(FrameRate::FPS_60.frames_per_second(), 60.0);

        // Fractional rates
        let fps_23_976 = FrameRate::FPS_23_976.frames_per_second();
        assert!((fps_23_976 - 23.976_023_976_023_976).abs() < 1e-10);

        let fps_29_97 = FrameRate::FPS_29_97.frames_per_second();
        assert!((fps_29_97 - 29.97_002_997_002_997).abs() < 1e-10);

        let fps_59_94 = FrameRate::FPS_59_94.frames_per_second();
        assert!((fps_59_94 - 59.94_005_994_005_994).abs() < 1e-10);
    }

    #[test]
    fn test_new_valid() {
        let fps = FrameRate::new(30, 1).unwrap();
        assert_eq!(fps.numerator(), 30);
        assert_eq!(fps.denominator(), 1);
    }

    #[test]
    fn test_new_zero_denominator() {
        assert!(FrameRate::new(30, 0).is_none());
    }

    #[test]
    fn test_custom_frame_rate() {
        let fps = FrameRate::new(48, 1).unwrap();
        assert_eq!(fps.frames_per_second(), 48.0);

        let fps = FrameRate::new(120, 1).unwrap();
        assert_eq!(fps.frames_per_second(), 120.0);
    }

    #[test]
    fn test_equality() {
        let fps1 = FrameRate::new(30, 1).unwrap();
        let fps2 = FrameRate::new(30, 1).unwrap();
        assert_eq!(fps1, fps2);

        // Note: FrameRate doesn't normalize, so 60/2 != 30/1
        let fps3 = FrameRate::new(60, 2).unwrap();
        assert_ne!(fps1, fps3);
    }
}
