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

use std::collections::HashMap;

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

// ========== ParametricEqBuilder ==========

#[derive(Debug, Clone)]
struct EqBand {
    frequency: f64,
    gain: f64,
    width: f64,
}

/// Type-safe builder for FFmpeg `anequalizer` parametric equalizer filter.
///
/// Generates pipe-separated band specifications:
/// `anequalizer=c0 f={hz} w={width} g={gain_db} t=1|c1 f={hz} w={width} g={gain_db} t=1|...`
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ParametricEqBuilder {
    bands: Vec<EqBand>,
}

impl ParametricEqBuilder {
    /// Creates a new ParametricEqBuilder with the given bands.
    ///
    /// # Arguments
    ///
    /// * `bands` - Vec of (frequency_hz, gain_db, width_hz) tuples.
    ///
    /// # Errors
    ///
    /// Returns an error if bands is empty or any band has an invalid parameter.
    pub fn new(bands: Vec<(f64, f64, f64)>) -> Result<Self, String> {
        if bands.is_empty() {
            return Err("bands must not be empty".to_string());
        }
        let mut eq_bands = Vec::with_capacity(bands.len());
        for (i, (frequency, gain, width)) in bands.iter().enumerate() {
            if *frequency < 20.0 || *frequency > 20000.0 {
                return Err(format!(
                    "band {i}: frequency must be 20.0-20000.0 Hz, got {frequency}"
                ));
            }
            if *gain < -24.0 || *gain > 24.0 {
                return Err(format!("band {i}: gain must be -24.0-24.0 dB, got {gain}"));
            }
            if *width <= 0.0 {
                return Err(format!("band {i}: width must be > 0, got {width}"));
            }
            eq_bands.push(EqBand {
                frequency: *frequency,
                gain: *gain,
                width: *width,
            });
        }
        Ok(Self { bands: eq_bands })
    }

    /// Builds the anequalizer Filter.
    ///
    /// Emits: `anequalizer=c0 f={hz} w={width} g={gain} t=1|c1 f={hz} w={width} g={gain} t=1|...`
    #[must_use]
    pub fn build(&self) -> Filter {
        let band_specs: Vec<String> = self
            .bands
            .iter()
            .enumerate()
            .map(|(i, band)| {
                format!(
                    "c{i} f={} w={} g={} t=1",
                    band.frequency, band.width, band.gain
                )
            })
            .collect();
        let params = band_specs.join("|");
        Filter::new(format!("anequalizer={params}"))
    }
}

// ========== ParametricEqBuilder PyO3 bindings ==========

#[pymethods]
impl ParametricEqBuilder {
    /// Creates a new ParametricEqBuilder from a list of band dicts.
    ///
    /// Args:
    ///     bands: List of band dicts, each with required keys:
    ///         - ``frequency`` (float): Band center frequency in Hz (20–20000).
    ///         - ``gain`` (float): Band gain in dB (−24 to +24).
    ///         - ``width`` (float): Band width in Hz (> 0).
    ///
    /// Raises:
    ///     ValueError: If bands is empty, any frequency is outside 20–20000 Hz,
    ///         any gain is outside ±24 dB, or any width is <= 0.
    #[new]
    fn py_new(bands: Vec<HashMap<String, f64>>) -> PyResult<Self> {
        let band_tuples: Result<Vec<_>, PyErr> = bands
            .iter()
            .map(|band| {
                let frequency = *band.get("frequency").ok_or_else(|| {
                    PyValueError::new_err("each band must have a 'frequency' key")
                })?;
                let gain = *band
                    .get("gain")
                    .ok_or_else(|| PyValueError::new_err("each band must have a 'gain' key"))?;
                let width = *band
                    .get("width")
                    .ok_or_else(|| PyValueError::new_err("each band must have a 'width' key"))?;
                Ok::<_, PyErr>((frequency, gain, width))
            })
            .collect();
        Self::new(band_tuples?).map_err(PyValueError::new_err)
    }

    /// Builds the anequalizer Filter.
    ///
    /// Returns:
    ///     A Filter with anequalizer pipe-separated band specification.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    fn __repr__(&self) -> String {
        format!("ParametricEqBuilder(bands=[{}])", self.bands.len())
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

    // ========== ParametricEqBuilder tests ==========

    #[test]
    fn test_parametric_eq_single_band_builds_correct_filter() {
        let builder = ParametricEqBuilder::new(vec![(1000.0, 6.0, 200.0)]).unwrap();
        let s = builder.build().to_string();
        assert!(
            s.starts_with("anequalizer="),
            "Expected anequalizer=..., got: {s}"
        );
        assert!(s.contains("c0 f=1000"), "Missing c0 f=1000 in: {s}");
        assert!(s.contains("g=6"), "Missing g=6 in: {s}");
        assert!(s.contains("w=200"), "Missing w=200 in: {s}");
        assert!(s.contains("t=1"), "Missing t=1 in: {s}");
    }

    #[test]
    fn test_parametric_eq_multi_band_pipe_separated() {
        let builder =
            ParametricEqBuilder::new(vec![(1000.0, 6.0, 200.0), (5000.0, -3.0, 500.0)]).unwrap();
        let s = builder.build().to_string();
        assert!(s.contains("c0 f=1000"), "Missing c0 in: {s}");
        assert!(s.contains("c1 f=5000"), "Missing c1 in: {s}");
        assert!(s.contains('|'), "Missing pipe separator in: {s}");
    }

    #[test]
    fn test_parametric_eq_empty_bands_rejected() {
        let result = ParametricEqBuilder::new(vec![]);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("bands must not be empty"), "Got: {err}");
    }

    #[test]
    fn test_parametric_eq_frequency_below_range_rejected() {
        let result = ParametricEqBuilder::new(vec![(10.0, 0.0, 100.0)]);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("frequency"), "Got: {err}");
    }

    #[test]
    fn test_parametric_eq_frequency_above_range_rejected() {
        let result = ParametricEqBuilder::new(vec![(25000.0, 0.0, 100.0)]);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("frequency"), "Got: {err}");
    }

    #[test]
    fn test_parametric_eq_gain_out_of_range_rejected() {
        let result = ParametricEqBuilder::new(vec![(1000.0, 30.0, 100.0)]);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("gain"), "Got: {err}");
    }

    #[test]
    fn test_parametric_eq_negative_gain_out_of_range_rejected() {
        let result = ParametricEqBuilder::new(vec![(1000.0, -30.0, 100.0)]);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("gain"), "Got: {err}");
    }

    #[test]
    fn test_parametric_eq_zero_width_rejected() {
        let result = ParametricEqBuilder::new(vec![(1000.0, 0.0, 0.0)]);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("width"), "Got: {err}");
    }

    #[test]
    fn test_parametric_eq_boundary_frequency_accepted() {
        let result = ParametricEqBuilder::new(vec![(20.0, 0.0, 10.0)]);
        assert!(result.is_ok(), "20 Hz should be accepted");
        let result = ParametricEqBuilder::new(vec![(20000.0, 0.0, 10.0)]);
        assert!(result.is_ok(), "20000 Hz should be accepted");
    }

    #[test]
    fn test_parametric_eq_boundary_gain_accepted() {
        let result = ParametricEqBuilder::new(vec![(1000.0, 24.0, 100.0)]);
        assert!(result.is_ok(), "+24 dB should be accepted");
        let result = ParametricEqBuilder::new(vec![(1000.0, -24.0, 100.0)]);
        assert!(result.is_ok(), "-24 dB should be accepted");
    }

    #[test]
    fn test_parametric_eq_repr() {
        let builder = ParametricEqBuilder::new(vec![(1000.0, 6.0, 200.0)]).unwrap();
        let r = builder.__repr__();
        assert!(r.contains("ParametricEqBuilder"), "Got: {r}");
        assert!(r.contains('1'), "Got: {r}");
    }

    // ========== PyO3 GIL tests for ParametricEqBuilder ==========

    #[test]
    fn test_pyo3_parametric_eq_valid() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let mut band = HashMap::new();
            band.insert("frequency".to_string(), 1000.0_f64);
            band.insert("gain".to_string(), 6.0_f64);
            band.insert("width".to_string(), 200.0_f64);
            let builder = ParametricEqBuilder::py_new(vec![band]).unwrap();
            let filter_str = builder.build().to_string();
            assert!(filter_str.starts_with("anequalizer="));
            assert!(filter_str.contains("c0 f=1000"));
        });
    }

    #[test]
    fn test_pyo3_parametric_eq_empty_bands_raises() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let result = ParametricEqBuilder::py_new(vec![]);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_pyo3_parametric_eq_missing_frequency_raises() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let mut band = HashMap::new();
            band.insert("gain".to_string(), 6.0_f64);
            band.insert("width".to_string(), 200.0_f64);
            let result = ParametricEqBuilder::py_new(vec![band]);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_pyo3_parametric_eq_invalid_frequency_raises() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let mut band = HashMap::new();
            band.insert("frequency".to_string(), 10.0_f64);
            band.insert("gain".to_string(), 0.0_f64);
            band.insert("width".to_string(), 100.0_f64);
            let result = ParametricEqBuilder::py_new(vec![band]);
            assert!(result.is_err());
        });
    }
}
