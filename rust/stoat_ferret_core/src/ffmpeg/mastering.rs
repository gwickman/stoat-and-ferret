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

// ========== LoudnormBuilder ==========

/// Pass-1 measurement result from `loudnorm` filter (parsed from stderr JSON).
///
/// Used internally by [`LoudnormBuilder::build_pass2`]. The public Python API uses
/// the `LoudnormPassOneResult` Python dataclass in `definitions.py`, which exposes
/// the same fields plus a `from_stderr()` classmethod.
#[derive(Debug, Clone)]
pub struct LoudnormPassOneResult {
    /// Measured integrated loudness in LUFS.
    pub measured_i: f64,
    /// Measured loudness range in LU.
    pub measured_lra: f64,
    /// Measured true-peak in dBTP.
    pub measured_tp: f64,
    /// Offset applied to reach target LUFS.
    pub offset: f64,
}

/// Type-safe builder for FFmpeg `loudnorm` two-pass LUFS normalization.
///
/// Pass-1 filter: `build_pass1()` → loudnorm with `print_format=json` to capture measurements.
/// Pass-2 filter: `build_pass2(result)` → loudnorm with measured values for linear normalization.
///
/// Default LRA is 11.0 LU (EBU R128 recommendation).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct LoudnormBuilder {
    target_lufs: f64,
    ceiling_dbtp: f64,
    lra: f64,
}

impl LoudnormBuilder {
    /// Creates a new LoudnormBuilder.
    ///
    /// # Arguments
    ///
    /// * `target_lufs` - Target integrated loudness in LUFS (e.g. -16.0 for podcasts).
    /// * `ceiling_dbtp` - True-peak ceiling in dBTP (must be <= 0.0).
    /// * `lra` - Loudness range target in LU (default 11.0).
    ///
    /// # Errors
    ///
    /// Returns an error if `ceiling_dbtp > 0.0`.
    pub fn new(target_lufs: f64, ceiling_dbtp: f64, lra: f64) -> Result<Self, String> {
        if ceiling_dbtp > 0.0 {
            return Err(format!(
                "ceiling_dbtp must be <= 0.0 dBTP, got {ceiling_dbtp}"
            ));
        }
        Ok(Self {
            target_lufs,
            ceiling_dbtp,
            lra,
        })
    }

    /// Builds the pass-1 loudnorm filter (measurement pass).
    ///
    /// Emits: `loudnorm=I=<i>:TP=<tp>:LRA=<lra>:print_format=json`
    #[must_use]
    pub fn build_pass1(&self) -> Filter {
        Filter::new("loudnorm")
            .param("I", format!("{}", self.target_lufs))
            .param("TP", format!("{}", self.ceiling_dbtp))
            .param("LRA", format!("{}", self.lra))
            .param("print_format", "json".to_string())
    }

    /// Builds the pass-2 loudnorm filter using pass-1 measurements.
    ///
    /// Emits: `loudnorm=I=<i>:TP=<tp>:LRA=<lra>:measured_I=<mi>:measured_TP=<mtp>:measured_LRA=<mlra>:offset=<o>:linear=true:print_format=summary`
    #[must_use]
    pub fn build_pass2(&self, result: &LoudnormPassOneResult) -> Filter {
        Filter::new("loudnorm")
            .param("I", format!("{}", self.target_lufs))
            .param("TP", format!("{}", self.ceiling_dbtp))
            .param("LRA", format!("{}", self.lra))
            .param("measured_I", format!("{}", result.measured_i))
            .param("measured_TP", format!("{}", result.measured_tp))
            .param("measured_LRA", format!("{}", result.measured_lra))
            .param("offset", format!("{}", result.offset))
            .param("linear", "true".to_string())
            .param("print_format", "summary".to_string())
    }
}

// ========== LoudnormBuilder PyO3 bindings ==========

#[pymethods]
impl LoudnormBuilder {
    /// Creates a new LoudnormBuilder.
    ///
    /// Args:
    ///     target_lufs: Target integrated loudness in LUFS (e.g. -16.0 for podcasts, -14.0 for streaming).
    ///     ceiling_dbtp: True-peak ceiling in dBTP (must be <= 0.0).
    ///     lra: Loudness range target in LU (default 11.0, EBU R128 recommendation).
    ///
    /// Raises:
    ///     ValueError: If ceiling_dbtp > 0.0.
    #[new]
    fn py_new(target_lufs: f64, ceiling_dbtp: f64, lra: f64) -> PyResult<Self> {
        Self::new(target_lufs, ceiling_dbtp, lra).map_err(PyValueError::new_err)
    }

    /// Returns the target integrated loudness in LUFS.
    #[getter]
    #[pyo3(name = "target_lufs")]
    fn py_target_lufs(&self) -> f64 {
        self.target_lufs
    }

    /// Returns the true-peak ceiling in dBTP.
    #[getter]
    #[pyo3(name = "ceiling_dbtp")]
    fn py_ceiling_dbtp(&self) -> f64 {
        self.ceiling_dbtp
    }

    /// Returns the loudness range target in LU.
    #[getter]
    #[pyo3(name = "lra")]
    fn py_lra(&self) -> f64 {
        self.lra
    }

    /// Builds the pass-1 loudnorm filter (measurement pass).
    ///
    /// Returns:
    ///     A Filter with loudnorm=I=...:TP=...:LRA=...:print_format=json syntax.
    #[pyo3(name = "build_pass1")]
    fn py_build_pass1(&self) -> Filter {
        self.build_pass1()
    }

    /// Builds the pass-2 loudnorm filter using pass-1 measurements.
    ///
    /// Args:
    ///     measured_i: Measured integrated loudness from pass-1 (LUFS).
    ///     measured_lra: Measured loudness range from pass-1 (LU).
    ///     measured_tp: Measured true-peak from pass-1 (dBTP).
    ///     offset: Gain offset from pass-1.
    ///
    /// Returns:
    ///     A Filter with loudnorm linear normalization syntax.
    #[pyo3(name = "build_pass2")]
    fn py_build_pass2(
        &self,
        measured_i: f64,
        measured_lra: f64,
        measured_tp: f64,
        offset: f64,
    ) -> Filter {
        self.build_pass2(&LoudnormPassOneResult {
            measured_i,
            measured_lra,
            measured_tp,
            offset,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "LoudnormBuilder(target_lufs={}, ceiling_dbtp={}, lra={})",
            self.target_lufs, self.ceiling_dbtp, self.lra
        )
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

    // ========== LoudnormBuilder tests ==========

    #[test]
    fn test_loudnorm_build_pass1_emits_correct_filter() {
        let builder = LoudnormBuilder::new(-16.0, -1.0, 11.0).unwrap();
        let s = builder.build_pass1().to_string();
        assert!(s.contains("loudnorm="), "Missing loudnorm: {s}");
        assert!(s.contains("I=-16"), "Missing I=-16 in: {s}");
        assert!(s.contains("TP=-1"), "Missing TP=-1 in: {s}");
        assert!(s.contains("LRA=11"), "Missing LRA=11 in: {s}");
        assert!(
            s.contains("print_format=json"),
            "Missing print_format=json in: {s}"
        );
    }

    #[test]
    fn test_loudnorm_build_pass2_emits_correct_filter() {
        let builder = LoudnormBuilder::new(-16.0, -1.0, 11.0).unwrap();
        let result = LoudnormPassOneResult {
            measured_i: -18.5,
            measured_lra: 9.2,
            measured_tp: -2.0,
            offset: 0.3,
        };
        let s = builder.build_pass2(&result).to_string();
        assert!(s.contains("loudnorm="), "Missing loudnorm: {s}");
        assert!(s.contains("measured_I=-18.5"), "Missing measured_I in: {s}");
        assert!(s.contains("measured_TP=-2"), "Missing measured_TP in: {s}");
        assert!(
            s.contains("measured_LRA=9.2"),
            "Missing measured_LRA in: {s}"
        );
        assert!(s.contains("offset=0.3"), "Missing offset in: {s}");
        assert!(s.contains("linear=true"), "Missing linear=true in: {s}");
        assert!(
            s.contains("print_format=summary"),
            "Missing print_format=summary in: {s}"
        );
    }

    #[test]
    fn test_loudnorm_positive_ceiling_rejected() {
        let result = LoudnormBuilder::new(-16.0, 1.0, 11.0);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(
            err.contains("ceiling_dbtp must be <= 0.0"),
            "Unexpected: {err}"
        );
    }

    #[test]
    fn test_loudnorm_repr() {
        let builder = LoudnormBuilder::new(-16.0, -1.0, 11.0).unwrap();
        let r = builder.__repr__();
        assert!(r.contains("LoudnormBuilder"), "Got: {r}");
        assert!(r.contains("-16"), "Got: {r}");
        assert!(r.contains("-1"), "Got: {r}");
        assert!(r.contains("11"), "Got: {r}");
    }

    // ========== PyO3 GIL tests ==========

    #[test]
    fn test_pyo3_loudnorm_valid() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let builder = Bound::new(py, LoudnormBuilder::new(-16.0, -1.0, 11.0).unwrap()).unwrap();

            let pass1: String = builder
                .call_method0("build_pass1")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(pass1.contains("loudnorm="));
            assert!(pass1.contains("print_format=json"));

            // build_pass2 takes individual float args (measured_i, measured_lra, measured_tp, offset)
            let pass2: String = builder
                .call_method1("build_pass2", (-18.5_f64, 9.2_f64, -2.0_f64, 0.3_f64))
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(pass2.contains("linear=true"));
            assert!(pass2.contains("measured_I=-18.5"));

            let repr: String = builder.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("LoudnormBuilder"));

            let tl: f64 = builder.getattr("target_lufs").unwrap().extract().unwrap();
            assert!((tl - (-16.0)).abs() < 1e-9);
        });
    }

    #[test]
    fn test_pyo3_loudnorm_positive_ceiling_raises() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let result = LoudnormBuilder::py_new(-16.0, 1.0, 11.0);
            assert!(result.is_err());
        });
    }
}
