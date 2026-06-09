//! Mastering filter builders for FFmpeg.
//!
//! This module provides type-safe builders for the mastering chain:
//!
//! - [`LimiterBuilder`] - True-peak limiter (`alimiter`) with dBTP-to-linear conversion
//!
//! All builders follow the fluent pattern: construct, configure, then `.build()`.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::mastering::LimiterBuilder;
//!
//! let limiter = LimiterBuilder::new(-1.0).unwrap();
//! let filter = limiter.build();
//! assert!(filter.to_string().starts_with("alimiter=limit="));
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::filter::Filter;

// ========== dBTP to linear conversion ==========

fn dbtp_to_linear(dbtp: f64) -> f64 {
    10.0_f64.powf(dbtp / 20.0)
}

// ========== LimiterBuilder ==========

/// Type-safe builder for FFmpeg `alimiter` true-peak limiter.
///
/// Converts `ceiling_dbtp` (a non-positive dBTP value) to a linear ratio for the
/// `alimiter` `limit` parameter: `limit = 10^(ceiling_dbtp / 20)`.
///
/// Example: −1 dBTP → limit=0.891251 (verified at interface-contracts.md §3).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct LimiterBuilder {
    ceiling_dbtp: f64,
}

impl LimiterBuilder {
    /// Creates a new LimiterBuilder with the given ceiling in dBTP.
    ///
    /// # Arguments
    ///
    /// * `ceiling_dbtp` - Ceiling level in dBTP. Must be <= 0.0.
    ///
    /// # Errors
    ///
    /// Returns an error if `ceiling_dbtp > 0.0`.
    pub fn new(ceiling_dbtp: f64) -> Result<Self, String> {
        if ceiling_dbtp > 0.0 {
            return Err(format!(
                "ceiling_dbtp must be <= 0.0 dBTP, got {ceiling_dbtp}"
            ));
        }
        Ok(Self { ceiling_dbtp })
    }

    /// Builds the alimiter Filter.
    ///
    /// Emits: `alimiter=limit=<ratio>:level=disabled`
    #[must_use]
    pub fn build(&self) -> Filter {
        let limit = dbtp_to_linear(self.ceiling_dbtp);
        Filter::new("alimiter")
            .param("limit", format!("{limit:.6}"))
            .param("level", "disabled".to_string())
    }
}

// ========== LimiterBuilder PyO3 bindings ==========

#[pymethods]
impl LimiterBuilder {
    /// Creates a new LimiterBuilder.
    ///
    /// Args:
    ///     ceiling_dbtp: Ceiling in dBTP. Must be <= 0.0; positive values would permit
    ///                   gain above 0 dBFS which is non-sensical for a true-peak ceiling.
    ///
    /// Raises:
    ///     ValueError: If ceiling_dbtp > 0.0.
    #[new]
    fn py_new(ceiling_dbtp: f64) -> PyResult<Self> {
        Self::new(ceiling_dbtp).map_err(PyValueError::new_err)
    }

    /// Returns the ceiling in dBTP.
    #[getter]
    #[pyo3(name = "ceiling_dbtp")]
    fn py_ceiling_dbtp(&self) -> f64 {
        self.ceiling_dbtp
    }

    /// Builds the alimiter Filter.
    ///
    /// Returns:
    ///     A Filter with alimiter=limit=<ratio>:level=disabled syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!("LimiterBuilder(ceiling_dbtp={})", self.ceiling_dbtp)
    }
}

// ========== Tests ==========

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dbtp_to_linear_minus_one() {
        let linear = dbtp_to_linear(-1.0);
        let expected = 0.891_251_f64;
        assert!(
            (linear - expected).abs() < 1e-4,
            "Expected ~{expected}, got {linear}"
        );
    }

    #[test]
    fn test_build_emits_alimiter_filter() {
        let limiter = LimiterBuilder::new(-1.0).unwrap();
        let s = limiter.build().to_string();
        assert!(
            s.starts_with("alimiter=limit=0.891"),
            "Expected alimiter=limit=0.891..., got: {s}"
        );
        assert!(
            s.contains("level=disabled"),
            "Missing level=disabled in: {s}"
        );
    }

    #[test]
    fn test_positive_ceiling_rejected() {
        let result = LimiterBuilder::new(1.0);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(
            err.contains("ceiling_dbtp must be <= 0.0"),
            "Unexpected error message: {err}"
        );
    }

    #[test]
    fn test_zero_ceiling_accepted() {
        let limiter = LimiterBuilder::new(0.0).unwrap();
        let s = limiter.build().to_string();
        assert!(s.contains("alimiter=limit=1.000000"), "Got: {s}");
        assert!(s.contains("level=disabled"), "Got: {s}");
    }

    #[test]
    fn test_repr() {
        let limiter = LimiterBuilder::new(-1.0).unwrap();
        assert_eq!(limiter.__repr__(), "LimiterBuilder(ceiling_dbtp=-1)");
    }

    // ========== PyO3 binding tests ==========

    use pyo3::prelude::*;

    #[test]
    fn test_pyo3_limiter_valid() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let lb = Bound::new(py, LimiterBuilder::new(-1.0).unwrap()).unwrap();
            let filter_str: String = lb
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filter_str.starts_with("alimiter=limit=0.891"));
            assert!(filter_str.contains("level=disabled"));

            let repr: String = lb.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("LimiterBuilder"));
            assert!(repr.contains("-1"));

            let ceiling: f64 = lb.getattr("ceiling_dbtp").unwrap().extract().unwrap();
            assert!((ceiling - (-1.0)).abs() < 1e-9);
        });
    }

    #[test]
    fn test_pyo3_positive_ceiling_raises() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let result = LimiterBuilder::py_new(1.0);
            assert!(result.is_err());
        });
    }
}
