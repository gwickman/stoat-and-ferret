// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Frame-rate conversion filter builder for FFmpeg.
//!
//! This module provides [`FramerateConvertBuilder`] for constructing FFmpeg
//! `minterpolate` and `framerate` filters that convert a clip to a target
//! frame rate using optical-flow, frame-blend, or duplicate interpolation.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::framerate::{FramerateConvertBuilder, FramerateMode};
//!
//! // Blend interpolation at 60 fps
//! let builder = FramerateConvertBuilder::new(60.0, FramerateMode::Blend).unwrap();
//! let filter = builder.build();
//! assert_eq!(filter.to_string(), "minterpolate=fps=60:mi_mode=blend");
//!
//! // Optical-flow at 30 fps
//! let builder = FramerateConvertBuilder::new(30.0, FramerateMode::OpticalFlow).unwrap();
//! assert_eq!(builder.build().to_string(), "minterpolate=fps=30:mi_mode=mci");
//!
//! // Duplicate (framerate filter) at 24 fps
//! let builder = FramerateConvertBuilder::new(24.0, FramerateMode::Duplicate).unwrap();
//! assert_eq!(builder.build().to_string(), "framerate=fps=24");
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::filter::Filter;

// ========== FramerateMode Enum ==========

/// Interpolation mode for frame-rate conversion.
///
/// - `Blend` — frame-blending via `minterpolate:mi_mode=blend`
/// - `OpticalFlow` — optical-flow motion interpolation via `minterpolate:mi_mode=mci`;
///   requires FFmpeg built with `--enable-libopencv` (~30–100× realtime)
/// - `Duplicate` — simple frame duplication via the `framerate` filter (fastest; no libopencv)
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum FramerateMode {
    /// Frame-blending interpolation (`minterpolate:mi_mode=blend`).
    Blend,
    /// Optical-flow motion interpolation (`minterpolate:mi_mode=mci`).
    /// Requires FFmpeg built with `--enable-libopencv`.
    OpticalFlow,
    /// Simple frame duplication via the `framerate` filter.
    Duplicate,
}

#[pymethods]
impl FramerateMode {
    /// Convert a string name to a FramerateMode variant.
    ///
    /// Args:
    ///     name: One of ``"blend"``, ``"optical_flow"``, or ``"duplicate"``.
    ///
    /// Raises:
    ///     ValueError: If the name is not a recognised mode.
    #[staticmethod]
    #[pyo3(name = "from_str")]
    fn py_from_str(name: &str) -> PyResult<Self> {
        match name {
            "blend" => Ok(FramerateMode::Blend),
            "optical_flow" => Ok(FramerateMode::OpticalFlow),
            "duplicate" => Ok(FramerateMode::Duplicate),
            other => Err(PyValueError::new_err(format!(
                "unknown FramerateMode '{other}'; expected 'blend', 'optical_flow', or 'duplicate'"
            ))),
        }
    }

    /// Returns the string name of this mode.
    fn __str__(&self) -> &'static str {
        match self {
            FramerateMode::Blend => "blend",
            FramerateMode::OpticalFlow => "optical_flow",
            FramerateMode::Duplicate => "duplicate",
        }
    }

    fn __repr__(&self) -> String {
        format!("FramerateMode.{}", self.__str__())
    }
}

// ========== FramerateConvertBuilder ==========

/// Formats a frame-rate value, stripping unnecessary trailing zeros.
///
/// For example, `30.0` → `"30"`, `23.976` → `"23.976"`.
fn format_fps(fps: f64) -> String {
    if (fps - fps.round()).abs() < 1e-9 {
        format!("{}", fps.round() as i64)
    } else {
        let s = format!("{fps:.10}");
        let s = s.trim_end_matches('0');
        s.trim_end_matches('.').to_string()
    }
}

/// Builder for FFmpeg frame-rate conversion filters.
///
/// Generates `minterpolate=fps={target}:mi_mode=blend` (blend),
/// `minterpolate=fps={target}:mi_mode=mci` (optical-flow), or
/// `framerate=fps={target}` (duplicate) filter strings.
///
/// Minimum FFmpeg 4.0+ required for `minterpolate`. OpticalFlow mode requires
/// an FFmpeg build with `--enable-libopencv`.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::framerate::{FramerateConvertBuilder, FramerateMode};
///
/// let builder = FramerateConvertBuilder::new(60.0, FramerateMode::Blend).unwrap();
/// assert_eq!(builder.build().to_string(), "minterpolate=fps=60:mi_mode=blend");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct FramerateConvertBuilder {
    target_fps: f64,
    mode: FramerateMode,
}

impl FramerateConvertBuilder {
    /// Creates a new frame-rate conversion builder.
    ///
    /// # Arguments
    ///
    /// * `target_fps` — Target frame rate in frames per second (must be > 0).
    /// * `mode` — Interpolation mode (`Blend`, `OpticalFlow`, or `Duplicate`).
    ///
    /// # Errors
    ///
    /// Returns an error if `target_fps` is not > 0.
    pub fn new(target_fps: f64, mode: FramerateMode) -> Result<Self, String> {
        if target_fps <= 0.0 {
            return Err(format!("target_fps must be > 0, got {target_fps}"));
        }
        Ok(Self { target_fps, mode })
    }

    /// Builds the FFmpeg filter string for the configured mode.
    #[must_use]
    pub fn build(&self) -> Filter {
        let fps = format_fps(self.target_fps);
        let expr = match self.mode {
            FramerateMode::Blend => format!("minterpolate=fps={fps}:mi_mode=blend"),
            FramerateMode::OpticalFlow => format!("minterpolate=fps={fps}:mi_mode=mci"),
            FramerateMode::Duplicate => format!("framerate=fps={fps}"),
        };
        Filter::new(expr)
    }
}

// ========== PyO3 bindings ==========

#[pymethods]
impl FramerateConvertBuilder {
    /// Creates a new FramerateConvertBuilder.
    ///
    /// Args:
    ///     target_fps: Target frame rate in frames per second (must be > 0).
    ///     mode: Interpolation mode (FramerateMode.Blend, OpticalFlow, or Duplicate).
    ///
    /// Raises:
    ///     ValueError: If target_fps is not > 0.
    #[new]
    fn py_new(target_fps: f64, mode: FramerateMode) -> PyResult<Self> {
        Self::new(target_fps, mode).map_err(PyValueError::new_err)
    }

    /// Returns the target frame rate.
    #[getter]
    #[pyo3(name = "target_fps")]
    fn py_target_fps(&self) -> f64 {
        self.target_fps
    }

    /// Returns the interpolation mode.
    #[getter]
    #[pyo3(name = "mode")]
    fn py_mode(&self) -> FramerateMode {
        self.mode
    }

    /// Builds the FFmpeg filter for frame-rate conversion.
    ///
    /// Returns:
    ///     A Filter with the appropriate minterpolate or framerate filter string.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!(
            "FramerateConvertBuilder(target_fps={}, mode={})",
            self.target_fps,
            self.mode.__str__()
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========== FramerateMode tests ==========

    #[test]
    fn test_framerate_mode_from_str_blend() {
        let mode = FramerateMode::py_from_str("blend").unwrap();
        assert_eq!(mode, FramerateMode::Blend);
    }

    #[test]
    fn test_framerate_mode_from_str_optical_flow() {
        let mode = FramerateMode::py_from_str("optical_flow").unwrap();
        assert_eq!(mode, FramerateMode::OpticalFlow);
    }

    #[test]
    fn test_framerate_mode_from_str_duplicate() {
        let mode = FramerateMode::py_from_str("duplicate").unwrap();
        assert_eq!(mode, FramerateMode::Duplicate);
    }

    #[test]
    fn test_framerate_mode_from_str_invalid() {
        let result = FramerateMode::py_from_str("invalid");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.to_string().contains("unknown FramerateMode"));
    }

    #[test]
    fn test_framerate_mode_str() {
        assert_eq!(FramerateMode::Blend.__str__(), "blend");
        assert_eq!(FramerateMode::OpticalFlow.__str__(), "optical_flow");
        assert_eq!(FramerateMode::Duplicate.__str__(), "duplicate");
    }

    #[test]
    fn test_framerate_mode_repr() {
        assert_eq!(FramerateMode::Blend.__repr__(), "FramerateMode.blend");
        assert_eq!(
            FramerateMode::OpticalFlow.__repr__(),
            "FramerateMode.optical_flow"
        );
        assert_eq!(
            FramerateMode::Duplicate.__repr__(),
            "FramerateMode.duplicate"
        );
    }

    #[test]
    fn test_framerate_mode_clone() {
        let mode = FramerateMode::Blend;
        let cloned = mode;
        assert_eq!(mode, cloned);
    }

    // ========== FramerateConvertBuilder construction tests ==========

    #[test]
    fn test_new_valid_blend() {
        let builder = FramerateConvertBuilder::new(60.0, FramerateMode::Blend).unwrap();
        assert!((builder.target_fps - 60.0).abs() < f64::EPSILON);
        assert_eq!(builder.mode, FramerateMode::Blend);
    }

    #[test]
    fn test_new_valid_optical_flow() {
        let builder = FramerateConvertBuilder::new(30.0, FramerateMode::OpticalFlow).unwrap();
        assert_eq!(builder.mode, FramerateMode::OpticalFlow);
    }

    #[test]
    fn test_new_valid_duplicate() {
        let builder = FramerateConvertBuilder::new(24.0, FramerateMode::Duplicate).unwrap();
        assert_eq!(builder.mode, FramerateMode::Duplicate);
    }

    #[test]
    fn test_new_zero_fps_rejected() {
        let result = FramerateConvertBuilder::new(0.0, FramerateMode::Blend);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("target_fps must be > 0"));
    }

    #[test]
    fn test_new_negative_fps_rejected() {
        let result = FramerateConvertBuilder::new(-1.0, FramerateMode::Blend);
        assert!(result.is_err());
    }

    // ========== build() filter string tests ==========

    #[test]
    fn test_build_blend_30fps() {
        let builder = FramerateConvertBuilder::new(30.0, FramerateMode::Blend).unwrap();
        assert_eq!(
            builder.build().to_string(),
            "minterpolate=fps=30:mi_mode=blend"
        );
    }

    #[test]
    fn test_build_blend_60fps() {
        let builder = FramerateConvertBuilder::new(60.0, FramerateMode::Blend).unwrap();
        assert_eq!(
            builder.build().to_string(),
            "minterpolate=fps=60:mi_mode=blend"
        );
    }

    #[test]
    fn test_build_optical_flow_30fps() {
        let builder = FramerateConvertBuilder::new(30.0, FramerateMode::OpticalFlow).unwrap();
        assert_eq!(
            builder.build().to_string(),
            "minterpolate=fps=30:mi_mode=mci"
        );
    }

    #[test]
    fn test_build_optical_flow_60fps() {
        let builder = FramerateConvertBuilder::new(60.0, FramerateMode::OpticalFlow).unwrap();
        assert_eq!(
            builder.build().to_string(),
            "minterpolate=fps=60:mi_mode=mci"
        );
    }

    #[test]
    fn test_build_duplicate_24fps() {
        let builder = FramerateConvertBuilder::new(24.0, FramerateMode::Duplicate).unwrap();
        assert_eq!(builder.build().to_string(), "framerate=fps=24");
    }

    #[test]
    fn test_build_duplicate_30fps() {
        let builder = FramerateConvertBuilder::new(30.0, FramerateMode::Duplicate).unwrap();
        assert_eq!(builder.build().to_string(), "framerate=fps=30");
    }

    #[test]
    fn test_build_fractional_fps() {
        let builder = FramerateConvertBuilder::new(23.976, FramerateMode::Blend).unwrap();
        let s = builder.build().to_string();
        assert!(s.starts_with("minterpolate=fps=23.976"), "Got: {s}");
        assert!(s.contains("mi_mode=blend"), "Got: {s}");
    }

    // ========== format_fps tests ==========

    #[test]
    fn test_format_fps_integer() {
        assert_eq!(format_fps(30.0), "30");
        assert_eq!(format_fps(60.0), "60");
        assert_eq!(format_fps(24.0), "24");
    }

    #[test]
    fn test_format_fps_decimal() {
        assert_eq!(format_fps(23.976), "23.976");
        assert_eq!(format_fps(29.97), "29.97");
    }

    // ========== repr test ==========

    #[test]
    fn test_repr() {
        let builder = FramerateConvertBuilder::new(30.0, FramerateMode::Blend).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("FramerateConvertBuilder"));
        assert!(repr.contains("30"));
        assert!(repr.contains("blend"));
    }

    // ========== Clone test ==========

    #[test]
    fn test_clone() {
        let builder = FramerateConvertBuilder::new(60.0, FramerateMode::OpticalFlow).unwrap();
        let cloned = builder.clone();
        assert_eq!(cloned.build().to_string(), builder.build().to_string());
    }

    // ========== Direct PyO3 method invocation for coverage ==========

    #[test]
    fn test_pymethods_called_directly() {
        let b = FramerateConvertBuilder::py_new(60.0, FramerateMode::Blend).unwrap();
        assert!((b.py_target_fps() - 60.0).abs() < f64::EPSILON);
        assert_eq!(b.py_mode(), FramerateMode::Blend);
        assert_eq!(
            b.py_build().to_string(),
            "minterpolate=fps=60:mi_mode=blend"
        );
        assert!(b.__repr__().contains("FramerateConvertBuilder"));
    }

    #[test]
    fn test_py_new_invalid_fps() {
        let result = FramerateConvertBuilder::py_new(0.0, FramerateMode::Blend);
        assert!(result.is_err());
    }

    // ========== PyO3 binding tests ==========

    use pyo3::prelude::*;

    #[test]
    fn test_pyo3_framerate_convert_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let b = Bound::new(
                py,
                FramerateConvertBuilder::new(60.0, FramerateMode::Blend).unwrap(),
            )
            .unwrap();

            let fps: f64 = b.getattr("target_fps").unwrap().extract().unwrap();
            assert!((fps - 60.0).abs() < f64::EPSILON);

            let filter: String = b
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(filter, "minterpolate=fps=60:mi_mode=blend");

            let repr: String = b.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("FramerateConvertBuilder"));
        });
    }

    #[test]
    fn test_pyo3_framerate_mode_from_str() {
        // Test from_str via direct Rust call (covers PyO3 static method binding)
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let mode = FramerateMode::py_from_str("optical_flow").unwrap();
            assert_eq!(mode, FramerateMode::OpticalFlow);
            let err = FramerateMode::py_from_str("invalid");
            assert!(err.is_err());
        });
    }
}
