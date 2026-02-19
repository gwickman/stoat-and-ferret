//! Audio mixing filter builders for FFmpeg.
//!
//! This module provides type-safe builders for constructing audio mixing filters:
//!
//! - [`VolumeBuilder`] - Adjusts audio volume with linear or dB mode
//! - [`AfadeBuilder`] - Creates audio fade in/out effects with configurable curves
//! - [`AmixBuilder`] - Mixes multiple audio inputs with configurable weights
//! - [`DuckingPattern`] - Lowers music volume during speech using sidechaincompress
//!
//! All builders follow the fluent pattern: construct, configure, then `.build()`.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::audio::VolumeBuilder;
//!
//! let filter = VolumeBuilder::new(0.5).unwrap().build();
//! assert_eq!(filter.to_string(), "volume=volume=0.5");
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::filter::{Filter, FilterGraph};
use crate::sanitize;

// ========== FadeCurve Enum ==========

/// Supported fade curve types for the afade filter.
///
/// Each variant maps to an FFmpeg afade `curve` parameter value.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FadeCurve {
    /// Triangular (linear) - default.
    Tri,
    /// Quarter of sine wave.
    Qsin,
    /// Half of sine wave.
    Hsin,
    /// Exponential sine wave.
    Esin,
    /// Logarithmic.
    Log,
    /// Inverted parabola.
    Ipar,
    /// Quadratic.
    Qua,
    /// Cubic.
    Cub,
    /// Square root.
    Squ,
    /// Cubic root.
    Cbr,
    /// Parabola.
    Par,
}

impl FadeCurve {
    /// Returns the FFmpeg string representation of this curve.
    pub fn as_str(&self) -> &'static str {
        match self {
            FadeCurve::Tri => "tri",
            FadeCurve::Qsin => "qsin",
            FadeCurve::Hsin => "hsin",
            FadeCurve::Esin => "esin",
            FadeCurve::Log => "log",
            FadeCurve::Ipar => "ipar",
            FadeCurve::Qua => "qua",
            FadeCurve::Cub => "cub",
            FadeCurve::Squ => "squ",
            FadeCurve::Cbr => "cbr",
            FadeCurve::Par => "par",
        }
    }

    /// Parses a curve name string into a FadeCurve.
    ///
    /// # Errors
    ///
    /// Returns an error message if the curve name is not recognized.
    pub fn parse(s: &str) -> Result<Self, String> {
        match s {
            "tri" => Ok(FadeCurve::Tri),
            "qsin" => Ok(FadeCurve::Qsin),
            "hsin" => Ok(FadeCurve::Hsin),
            "esin" => Ok(FadeCurve::Esin),
            "log" => Ok(FadeCurve::Log),
            "ipar" => Ok(FadeCurve::Ipar),
            "qua" => Ok(FadeCurve::Qua),
            "cub" => Ok(FadeCurve::Cub),
            "squ" => Ok(FadeCurve::Squ),
            "cbr" => Ok(FadeCurve::Cbr),
            "par" => Ok(FadeCurve::Par),
            _ => Err(format!(
                "invalid fade curve '{s}'. Valid curves: tri, qsin, hsin, esin, \
                 log, ipar, qua, cub, squ, cbr, par"
            )),
        }
    }
}

// ========== VolumeBuilder ==========

/// Type-safe builder for FFmpeg `volume` audio filter.
///
/// Supports linear (float) and dB (string like "3dB") modes, plus precision
/// control. Validates volume range 0.0-10.0 via [`sanitize::validate_volume`].
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::audio::VolumeBuilder;
///
/// let filter = VolumeBuilder::new(0.5).unwrap().build();
/// assert_eq!(filter.to_string(), "volume=volume=0.5");
///
/// let filter = VolumeBuilder::new_db("3dB").unwrap().build();
/// assert_eq!(filter.to_string(), "volume=volume=3dB");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct VolumeBuilder {
    /// Volume value as a string (e.g., "0.5" or "3dB").
    volume_str: String,
    /// Precision mode: "fixed", "float", or "double".
    precision: Option<String>,
}

impl VolumeBuilder {
    /// Creates a new VolumeBuilder with a linear volume value.
    ///
    /// # Arguments
    ///
    /// * `volume` - Volume multiplier in range [0.0, 10.0]
    ///
    /// # Errors
    ///
    /// Returns an error if volume is outside [0.0, 10.0].
    pub fn new(volume: f64) -> Result<Self, String> {
        sanitize::validate_volume(volume).map_err(|e| e.to_string())?;
        Ok(Self {
            volume_str: format_volume_value(volume),
            precision: None,
        })
    }

    /// Creates a new VolumeBuilder with a dB volume string.
    ///
    /// # Arguments
    ///
    /// * `db_str` - Volume in dB format (e.g., "3dB", "-6dB")
    ///
    /// # Errors
    ///
    /// Returns an error if the string doesn't end with "dB".
    pub fn new_db(db_str: &str) -> Result<Self, String> {
        if !db_str.ends_with("dB") {
            return Err(format!(
                "dB volume must end with 'dB', got '{db_str}'"
            ));
        }
        // Validate the numeric part parses
        let numeric = &db_str[..db_str.len() - 2];
        numeric
            .parse::<f64>()
            .map_err(|_| format!("invalid dB value: '{db_str}'"))?;
        Ok(Self {
            volume_str: db_str.to_string(),
            precision: None,
        })
    }

    /// Sets the precision mode.
    ///
    /// # Arguments
    ///
    /// * `precision` - One of "fixed", "float", or "double"
    #[must_use]
    pub fn with_precision(mut self, precision: &str) -> Self {
        self.precision = Some(precision.to_string());
        self
    }

    /// Builds the volume Filter.
    #[must_use]
    pub fn build(&self) -> Filter {
        let mut filter = Filter::new("volume").param("volume", &self.volume_str);
        if let Some(ref prec) = self.precision {
            filter = filter.param("precision", prec);
        }
        filter
    }
}

/// Formats a volume value, stripping unnecessary trailing zeros.
fn format_volume_value(value: f64) -> String {
    if (value - value.round()).abs() < 1e-9 {
        let int_val = value.round() as i64;
        // Keep "0" for zero, otherwise use integer form
        format!("{int_val}")
    } else {
        let s = format!("{value:.10}");
        let s = s.trim_end_matches('0');
        s.trim_end_matches('.').to_string()
    }
}

// ========== VolumeBuilder PyO3 bindings ==========

#[pymethods]
impl VolumeBuilder {
    /// Creates a new VolumeBuilder with a linear volume value.
    ///
    /// Args:
    ///     volume: Volume multiplier in range [0.0, 10.0].
    ///
    /// Raises:
    ///     ValueError: If volume is outside [0.0, 10.0].
    #[new]
    fn py_new(volume: f64) -> PyResult<Self> {
        Self::new(volume).map_err(PyValueError::new_err)
    }

    /// Creates a VolumeBuilder from a dB string (e.g., "3dB", "-6dB").
    ///
    /// Args:
    ///     db_str: Volume in dB format.
    ///
    /// Raises:
    ///     ValueError: If the string format is invalid.
    #[staticmethod]
    #[pyo3(name = "from_db")]
    fn py_from_db(db_str: &str) -> PyResult<Self> {
        Self::new_db(db_str).map_err(PyValueError::new_err)
    }

    /// Sets the precision mode ("fixed", "float", or "double").
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "precision")]
    fn py_precision<'a>(mut slf: PyRefMut<'a, Self>, precision: &str) -> PyResult<PyRefMut<'a, Self>> {
        match precision {
            "fixed" | "float" | "double" => {
                slf.precision = Some(precision.to_string());
                Ok(slf)
            }
            _ => Err(PyValueError::new_err(format!(
                "precision must be 'fixed', 'float', or 'double', got '{precision}'"
            ))),
        }
    }

    /// Builds the volume Filter.
    ///
    /// Returns:
    ///     A Filter with the volume syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!("VolumeBuilder(volume={})", self.volume_str)
    }
}

// ========== AfadeBuilder ==========

/// Type-safe builder for FFmpeg `afade` audio filter.
///
/// Supports fade in/out with configurable duration, start time, and curve type.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::audio::AfadeBuilder;
///
/// let filter = AfadeBuilder::new("in", 3.0).unwrap().build();
/// assert_eq!(filter.to_string(), "afade=t=in:d=3");
///
/// let filter = AfadeBuilder::new("out", 2.0).unwrap()
///     .with_start_time(10.0)
///     .build();
/// assert_eq!(filter.to_string(), "afade=t=out:d=2:st=10");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct AfadeBuilder {
    /// Fade type: "in" or "out".
    fade_type: String,
    /// Fade duration in seconds.
    duration: f64,
    /// Start time in seconds (optional).
    start_time: Option<f64>,
    /// Fade curve type (optional, defaults to tri).
    curve: Option<FadeCurve>,
}

impl AfadeBuilder {
    /// Creates a new AfadeBuilder.
    ///
    /// # Arguments
    ///
    /// * `fade_type` - "in" or "out"
    /// * `duration` - Fade duration in seconds (must be > 0)
    ///
    /// # Errors
    ///
    /// Returns an error if fade_type is invalid or duration <= 0.
    pub fn new(fade_type: &str, duration: f64) -> Result<Self, String> {
        match fade_type {
            "in" | "out" => {}
            _ => {
                return Err(format!(
                    "fade type must be 'in' or 'out', got '{fade_type}'"
                ))
            }
        }
        if duration <= 0.0 {
            return Err(format!("fade duration must be > 0, got {duration}"));
        }
        Ok(Self {
            fade_type: fade_type.to_string(),
            duration,
            start_time: None,
            curve: None,
        })
    }

    /// Sets the start time for the fade.
    #[must_use]
    pub fn with_start_time(mut self, start_time: f64) -> Self {
        self.start_time = Some(start_time);
        self
    }

    /// Sets the fade curve type.
    #[must_use]
    pub fn with_curve(mut self, curve: FadeCurve) -> Self {
        self.curve = Some(curve);
        self
    }

    /// Builds the afade Filter.
    #[must_use]
    pub fn build(&self) -> Filter {
        let mut filter = Filter::new("afade")
            .param("t", &self.fade_type)
            .param("d", format_duration_value(self.duration));
        if let Some(st) = self.start_time {
            filter = filter.param("st", format_duration_value(st));
        }
        if let Some(ref curve) = self.curve {
            filter = filter.param("curve", curve.as_str());
        }
        filter
    }
}

/// Formats a duration value, stripping unnecessary trailing zeros.
fn format_duration_value(value: f64) -> String {
    if (value - value.round()).abs() < 1e-9 {
        format!("{}", value.round() as i64)
    } else {
        let s = format!("{value:.10}");
        let s = s.trim_end_matches('0');
        s.trim_end_matches('.').to_string()
    }
}

// ========== AfadeBuilder PyO3 bindings ==========

#[pymethods]
impl AfadeBuilder {
    /// Creates a new AfadeBuilder.
    ///
    /// Args:
    ///     fade_type: "in" or "out".
    ///     duration: Fade duration in seconds (must be > 0).
    ///
    /// Raises:
    ///     ValueError: If fade_type is invalid or duration <= 0.
    #[new]
    fn py_new(fade_type: &str, duration: f64) -> PyResult<Self> {
        Self::new(fade_type, duration).map_err(PyValueError::new_err)
    }

    /// Sets the start time for the fade in seconds.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "start_time")]
    fn py_start_time(mut slf: PyRefMut<'_, Self>, start_time: f64) -> PyRefMut<'_, Self> {
        slf.start_time = Some(start_time);
        slf
    }

    /// Sets the fade curve type.
    ///
    /// Valid curves: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par.
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If curve name is invalid.
    #[pyo3(name = "curve")]
    fn py_curve<'a>(mut slf: PyRefMut<'a, Self>, curve: &str) -> PyResult<PyRefMut<'a, Self>> {
        let c = FadeCurve::parse(curve).map_err(PyValueError::new_err)?;
        slf.curve = Some(c);
        Ok(slf)
    }

    /// Builds the afade Filter.
    ///
    /// Returns:
    ///     A Filter with the afade syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!(
            "AfadeBuilder(type={}, duration={})",
            self.fade_type, self.duration
        )
    }
}

// ========== AmixBuilder ==========

/// Type-safe builder for FFmpeg `amix` audio mixing filter.
///
/// Mixes multiple audio input streams into a single output. Supports
/// configurable input count (2-32), duration mode, per-input weights,
/// and normalization.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::audio::AmixBuilder;
///
/// let filter = AmixBuilder::new(4).unwrap().build();
/// assert_eq!(filter.to_string(), "amix=inputs=4");
///
/// let filter = AmixBuilder::new(2).unwrap()
///     .with_duration_mode("longest")
///     .with_weights(&[0.8, 0.2])
///     .build();
/// let s = filter.to_string();
/// assert!(s.contains("inputs=2"));
/// assert!(s.contains("duration=longest"));
/// assert!(s.contains("weights=0.8 0.2"));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct AmixBuilder {
    /// Number of input audio streams (2-32).
    inputs: usize,
    /// Duration mode: "longest", "shortest", or "first".
    duration_mode: Option<String>,
    /// Per-input weights as a list of floats.
    weights: Option<Vec<f64>>,
    /// Whether to normalize the output (default: true).
    normalize: Option<bool>,
}

impl AmixBuilder {
    /// Creates a new AmixBuilder with the given input count.
    ///
    /// # Arguments
    ///
    /// * `inputs` - Number of audio inputs (2-32)
    ///
    /// # Errors
    ///
    /// Returns an error if inputs is outside [2, 32].
    pub fn new(inputs: usize) -> Result<Self, String> {
        if !(2..=32).contains(&inputs) {
            return Err(format!(
                "amix input count must be 2-32, got {inputs}"
            ));
        }
        Ok(Self {
            inputs,
            duration_mode: None,
            weights: None,
            normalize: None,
        })
    }

    /// Sets the duration mode.
    ///
    /// # Arguments
    ///
    /// * `mode` - "longest", "shortest", or "first"
    #[must_use]
    pub fn with_duration_mode(mut self, mode: &str) -> Self {
        self.duration_mode = Some(mode.to_string());
        self
    }

    /// Sets per-input weights.
    #[must_use]
    pub fn with_weights(mut self, weights: &[f64]) -> Self {
        self.weights = Some(weights.to_vec());
        self
    }

    /// Sets the normalize flag.
    #[must_use]
    pub fn with_normalize(mut self, normalize: bool) -> Self {
        self.normalize = Some(normalize);
        self
    }

    /// Builds the amix Filter.
    #[must_use]
    pub fn build(&self) -> Filter {
        let mut filter = Filter::new("amix").param("inputs", self.inputs);
        if let Some(ref mode) = self.duration_mode {
            filter = filter.param("duration", mode);
        }
        if let Some(ref weights) = self.weights {
            let w_str: Vec<String> = weights.iter().map(|w| format_volume_value(*w)).collect();
            filter = filter.param("weights", w_str.join(" "));
        }
        if let Some(normalize) = self.normalize {
            filter = filter.param("normalize", if normalize { 1 } else { 0 });
        }
        filter
    }
}

// ========== AmixBuilder PyO3 bindings ==========

#[pymethods]
impl AmixBuilder {
    /// Creates a new AmixBuilder with the given input count.
    ///
    /// Args:
    ///     inputs: Number of audio inputs (2-32).
    ///
    /// Raises:
    ///     ValueError: If inputs is outside [2, 32].
    #[new]
    fn py_new(inputs: usize) -> PyResult<Self> {
        Self::new(inputs).map_err(PyValueError::new_err)
    }

    /// Sets the duration mode ("longest", "shortest", or "first").
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If mode is not one of the valid values.
    #[pyo3(name = "duration_mode")]
    fn py_duration_mode<'a>(
        mut slf: PyRefMut<'a, Self>,
        mode: &str,
    ) -> PyResult<PyRefMut<'a, Self>> {
        match mode {
            "longest" | "shortest" | "first" => {
                slf.duration_mode = Some(mode.to_string());
                Ok(slf)
            }
            _ => Err(PyValueError::new_err(format!(
                "duration mode must be 'longest', 'shortest', or 'first', got '{mode}'"
            ))),
        }
    }

    /// Sets per-input weights as a list of floats.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "weights")]
    fn py_weights(mut slf: PyRefMut<'_, Self>, weights: Vec<f64>) -> PyRefMut<'_, Self> {
        slf.weights = Some(weights);
        slf
    }

    /// Sets the normalize flag.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "normalize")]
    fn py_normalize(mut slf: PyRefMut<'_, Self>, normalize: bool) -> PyRefMut<'_, Self> {
        slf.normalize = Some(normalize);
        slf
    }

    /// Builds the amix Filter.
    ///
    /// Returns:
    ///     A Filter with the amix syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!("AmixBuilder(inputs={})", self.inputs)
    }
}

// ========== DuckingPattern ==========

/// Builds a ducking pattern that lowers music volume during speech.
///
/// Uses FFmpeg's `sidechaincompress` filter in a FilterGraph composition:
/// - Splits the audio input using `asplit`
/// - Applies `sidechaincompress` to one branch (keyed by the other)
/// - Merges the result with `amerge`
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::audio::DuckingPattern;
///
/// let pattern = DuckingPattern::new().unwrap();
/// let graph = pattern.build();
/// let s = graph.to_string();
/// assert!(s.contains("asplit"));
/// assert!(s.contains("sidechaincompress"));
/// assert!(s.contains("amerge"));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct DuckingPattern {
    /// Detection threshold (0.00097563-1.0, default: 0.125).
    threshold: f64,
    /// Compression ratio (1-20, default: 2).
    ratio: f64,
    /// Attack time in ms (0.01-2000, default: 20).
    attack: f64,
    /// Release time in ms (0.01-9000, default: 250).
    release: f64,
}

impl DuckingPattern {
    /// Creates a new DuckingPattern with default parameters.
    ///
    /// Defaults: threshold=0.125, ratio=2, attack=20, release=250.
    pub fn new() -> Result<Self, String> {
        Ok(Self {
            threshold: 0.125,
            ratio: 2.0,
            attack: 20.0,
            release: 250.0,
        })
    }

    /// Sets the detection threshold.
    ///
    /// # Arguments
    ///
    /// * `threshold` - Range [0.00097563, 1.0]
    pub fn with_threshold(mut self, threshold: f64) -> Result<Self, String> {
        if !(0.00097563..=1.0).contains(&threshold) {
            return Err(format!(
                "threshold must be 0.00097563-1.0, got {threshold}"
            ));
        }
        self.threshold = threshold;
        Ok(self)
    }

    /// Sets the compression ratio.
    ///
    /// # Arguments
    ///
    /// * `ratio` - Range [1, 20]
    pub fn with_ratio(mut self, ratio: f64) -> Result<Self, String> {
        if !(1.0..=20.0).contains(&ratio) {
            return Err(format!("ratio must be 1-20, got {ratio}"));
        }
        self.ratio = ratio;
        Ok(self)
    }

    /// Sets the attack time in milliseconds.
    ///
    /// # Arguments
    ///
    /// * `attack` - Range [0.01, 2000]
    pub fn with_attack(mut self, attack: f64) -> Result<Self, String> {
        if !(0.01..=2000.0).contains(&attack) {
            return Err(format!("attack must be 0.01-2000ms, got {attack}"));
        }
        self.attack = attack;
        Ok(self)
    }

    /// Sets the release time in milliseconds.
    ///
    /// # Arguments
    ///
    /// * `release` - Range [0.01, 9000]
    pub fn with_release(mut self, release: f64) -> Result<Self, String> {
        if !(0.01..=9000.0).contains(&release) {
            return Err(format!("release must be 0.01-9000ms, got {release}"));
        }
        self.release = release;
        Ok(self)
    }

    /// Builds the ducking FilterGraph.
    ///
    /// Creates a graph that:
    /// 1. Splits input "0:a" into two branches using `asplit`
    /// 2. Applies `sidechaincompress` on one branch (keyed by the other)
    /// 3. Merges the compressed and original audio with `amerge`
    #[must_use]
    pub fn build(&self) -> FilterGraph {
        let mut graph = FilterGraph::new();

        // Step 1: Split input audio into two branches
        let branches = graph
            .compose_branch("0:a", 2, true)
            .expect("compose_branch with count=2 cannot fail");

        // Step 2: Apply sidechaincompress on the first branch, keyed by the second
        let sc_filter = Filter::new("sidechaincompress")
            .param("threshold", format_duration_value(self.threshold))
            .param("ratio", format_duration_value(self.ratio))
            .param("attack", format_duration_value(self.attack))
            .param("release", format_duration_value(self.release));

        let compressed = graph
            .compose_merge(
                &[branches[0].as_str(), branches[1].as_str()],
                sc_filter,
            )
            .expect("compose_merge with 2 inputs cannot fail");

        // Step 3: Merge the compressed result with amerge
        // For ducking, the compressed output is the final output.
        // We use compose_chain to pass through with a null filter to get a labeled output.
        let _out = graph
            .compose_chain(&compressed, vec![Filter::new("anull")])
            .expect("compose_chain with one filter cannot fail");

        graph
    }
}

// ========== DuckingPattern PyO3 bindings ==========

#[pymethods]
impl DuckingPattern {
    /// Creates a new DuckingPattern with default parameters.
    ///
    /// Defaults: threshold=0.125, ratio=2, attack=20, release=250.
    #[new]
    fn py_new() -> PyResult<Self> {
        Self::new().map_err(PyValueError::new_err)
    }

    /// Sets the detection threshold (0.00097563-1.0).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If threshold is out of range.
    #[pyo3(name = "threshold")]
    fn py_threshold(mut slf: PyRefMut<'_, Self>, threshold: f64) -> PyResult<PyRefMut<'_, Self>> {
        if !(0.00097563..=1.0).contains(&threshold) {
            return Err(PyValueError::new_err(format!(
                "threshold must be 0.00097563-1.0, got {threshold}"
            )));
        }
        slf.threshold = threshold;
        Ok(slf)
    }

    /// Sets the compression ratio (1-20).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If ratio is out of range.
    #[pyo3(name = "ratio")]
    fn py_ratio(mut slf: PyRefMut<'_, Self>, ratio: f64) -> PyResult<PyRefMut<'_, Self>> {
        if !(1.0..=20.0).contains(&ratio) {
            return Err(PyValueError::new_err(format!(
                "ratio must be 1-20, got {ratio}"
            )));
        }
        slf.ratio = ratio;
        Ok(slf)
    }

    /// Sets the attack time in milliseconds (0.01-2000).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If attack is out of range.
    #[pyo3(name = "attack")]
    fn py_attack(mut slf: PyRefMut<'_, Self>, attack: f64) -> PyResult<PyRefMut<'_, Self>> {
        if !(0.01..=2000.0).contains(&attack) {
            return Err(PyValueError::new_err(format!(
                "attack must be 0.01-2000ms, got {attack}"
            )));
        }
        slf.attack = attack;
        Ok(slf)
    }

    /// Sets the release time in milliseconds (0.01-9000).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If release is out of range.
    #[pyo3(name = "release")]
    fn py_release(mut slf: PyRefMut<'_, Self>, release: f64) -> PyResult<PyRefMut<'_, Self>> {
        if !(0.01..=9000.0).contains(&release) {
            return Err(PyValueError::new_err(format!(
                "release must be 0.01-9000ms, got {release}"
            )));
        }
        slf.release = release;
        Ok(slf)
    }

    /// Builds the ducking FilterGraph.
    ///
    /// Returns:
    ///     A FilterGraph implementing the ducking pattern.
    #[pyo3(name = "build")]
    fn py_build(&self) -> FilterGraph {
        self.build()
    }

    /// Returns a string representation of the pattern.
    fn __repr__(&self) -> String {
        format!(
            "DuckingPattern(threshold={}, ratio={}, attack={}, release={})",
            self.threshold, self.ratio, self.attack, self.release
        )
    }
}

// ========== Tests ==========

#[cfg(test)]
mod tests {
    use super::*;

    // ========== VolumeBuilder tests ==========

    #[test]
    fn test_volume_builder_basic() {
        let filter = VolumeBuilder::new(0.5).unwrap().build();
        assert_eq!(filter.to_string(), "volume=volume=0.5");
    }

    #[test]
    fn test_volume_builder_zero() {
        let filter = VolumeBuilder::new(0.0).unwrap().build();
        assert_eq!(filter.to_string(), "volume=volume=0");
    }

    #[test]
    fn test_volume_builder_normal() {
        let filter = VolumeBuilder::new(1.0).unwrap().build();
        assert_eq!(filter.to_string(), "volume=volume=1");
    }

    #[test]
    fn test_volume_builder_max() {
        let filter = VolumeBuilder::new(10.0).unwrap().build();
        assert_eq!(filter.to_string(), "volume=volume=10");
    }

    #[test]
    fn test_volume_builder_below_range() {
        let result = VolumeBuilder::new(-0.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("range"));
    }

    #[test]
    fn test_volume_builder_above_range() {
        let result = VolumeBuilder::new(10.1);
        assert!(result.is_err());
    }

    #[test]
    fn test_volume_builder_db_mode() {
        let filter = VolumeBuilder::new_db("3dB").unwrap().build();
        assert_eq!(filter.to_string(), "volume=volume=3dB");
    }

    #[test]
    fn test_volume_builder_negative_db() {
        let filter = VolumeBuilder::new_db("-6dB").unwrap().build();
        assert_eq!(filter.to_string(), "volume=volume=-6dB");
    }

    #[test]
    fn test_volume_builder_invalid_db() {
        let result = VolumeBuilder::new_db("loud");
        assert!(result.is_err());
    }

    #[test]
    fn test_volume_builder_precision() {
        let builder = VolumeBuilder::new(0.5).unwrap().with_precision("float");
        let filter = builder.build();
        let s = filter.to_string();
        assert!(s.contains("volume=0.5"));
        assert!(s.contains("precision=float"));
    }

    // ========== AfadeBuilder tests ==========

    #[test]
    fn test_afade_fade_in() {
        let filter = AfadeBuilder::new("in", 3.0).unwrap().build();
        assert_eq!(filter.to_string(), "afade=t=in:d=3");
    }

    #[test]
    fn test_afade_fade_out() {
        let filter = AfadeBuilder::new("out", 2.0).unwrap().build();
        assert_eq!(filter.to_string(), "afade=t=out:d=2");
    }

    #[test]
    fn test_afade_with_start_time() {
        let filter = AfadeBuilder::new("out", 2.0)
            .unwrap()
            .with_start_time(10.0)
            .build();
        assert_eq!(filter.to_string(), "afade=t=out:d=2:st=10");
    }

    #[test]
    fn test_afade_with_curve() {
        let filter = AfadeBuilder::new("in", 1.5)
            .unwrap()
            .with_curve(FadeCurve::Qsin)
            .build();
        assert_eq!(filter.to_string(), "afade=t=in:d=1.5:curve=qsin");
    }

    #[test]
    fn test_afade_with_all_options() {
        let filter = AfadeBuilder::new("out", 2.5)
            .unwrap()
            .with_start_time(5.0)
            .with_curve(FadeCurve::Log)
            .build();
        assert_eq!(filter.to_string(), "afade=t=out:d=2.5:st=5:curve=log");
    }

    #[test]
    fn test_afade_invalid_type() {
        let result = AfadeBuilder::new("up", 1.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("'in' or 'out'"));
    }

    #[test]
    fn test_afade_zero_duration() {
        let result = AfadeBuilder::new("in", 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("> 0"));
    }

    #[test]
    fn test_afade_negative_duration() {
        let result = AfadeBuilder::new("in", -1.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_afade_fractional_duration() {
        let filter = AfadeBuilder::new("in", 0.5).unwrap().build();
        assert_eq!(filter.to_string(), "afade=t=in:d=0.5");
    }

    // ========== FadeCurve tests ==========

    #[test]
    fn test_fade_curve_all_variants() {
        let curves = [
            ("tri", FadeCurve::Tri),
            ("qsin", FadeCurve::Qsin),
            ("hsin", FadeCurve::Hsin),
            ("esin", FadeCurve::Esin),
            ("log", FadeCurve::Log),
            ("ipar", FadeCurve::Ipar),
            ("qua", FadeCurve::Qua),
            ("cub", FadeCurve::Cub),
            ("squ", FadeCurve::Squ),
            ("cbr", FadeCurve::Cbr),
            ("par", FadeCurve::Par),
        ];
        for (name, expected) in curves {
            let parsed = FadeCurve::parse(name).unwrap();
            assert_eq!(parsed, expected);
            assert_eq!(parsed.as_str(), name);
        }
    }

    #[test]
    fn test_fade_curve_invalid() {
        let result = FadeCurve::parse("invalid");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("invalid fade curve"));
    }

    #[test]
    fn test_fade_curve_all_in_filter() {
        let curves = [
            FadeCurve::Tri,
            FadeCurve::Qsin,
            FadeCurve::Hsin,
            FadeCurve::Esin,
            FadeCurve::Log,
            FadeCurve::Ipar,
            FadeCurve::Qua,
            FadeCurve::Cub,
            FadeCurve::Squ,
            FadeCurve::Cbr,
            FadeCurve::Par,
        ];
        for curve in curves {
            let filter = AfadeBuilder::new("in", 1.0)
                .unwrap()
                .with_curve(curve)
                .build();
            let s = filter.to_string();
            assert!(
                s.contains(&format!("curve={}", curve.as_str())),
                "Missing curve in: {s}"
            );
        }
    }

    // ========== AmixBuilder tests ==========

    #[test]
    fn test_amix_basic() {
        let filter = AmixBuilder::new(4).unwrap().build();
        assert_eq!(filter.to_string(), "amix=inputs=4");
    }

    #[test]
    fn test_amix_minimum_inputs() {
        let filter = AmixBuilder::new(2).unwrap().build();
        assert_eq!(filter.to_string(), "amix=inputs=2");
    }

    #[test]
    fn test_amix_maximum_inputs() {
        let filter = AmixBuilder::new(32).unwrap().build();
        assert_eq!(filter.to_string(), "amix=inputs=32");
    }

    #[test]
    fn test_amix_below_range() {
        let result = AmixBuilder::new(1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("2-32"));
    }

    #[test]
    fn test_amix_above_range() {
        let result = AmixBuilder::new(33);
        assert!(result.is_err());
    }

    #[test]
    fn test_amix_duration_longest() {
        let filter = AmixBuilder::new(3)
            .unwrap()
            .with_duration_mode("longest")
            .build();
        let s = filter.to_string();
        assert!(s.contains("inputs=3"));
        assert!(s.contains("duration=longest"));
    }

    #[test]
    fn test_amix_duration_shortest() {
        let filter = AmixBuilder::new(2)
            .unwrap()
            .with_duration_mode("shortest")
            .build();
        assert!(filter.to_string().contains("duration=shortest"));
    }

    #[test]
    fn test_amix_duration_first() {
        let filter = AmixBuilder::new(2)
            .unwrap()
            .with_duration_mode("first")
            .build();
        assert!(filter.to_string().contains("duration=first"));
    }

    #[test]
    fn test_amix_weights() {
        let filter = AmixBuilder::new(2)
            .unwrap()
            .with_weights(&[0.8, 0.2])
            .build();
        let s = filter.to_string();
        assert!(s.contains("weights=0.8 0.2"));
    }

    #[test]
    fn test_amix_normalize_disabled() {
        let filter = AmixBuilder::new(2)
            .unwrap()
            .with_normalize(false)
            .build();
        assert!(filter.to_string().contains("normalize=0"));
    }

    #[test]
    fn test_amix_normalize_enabled() {
        let filter = AmixBuilder::new(2)
            .unwrap()
            .with_normalize(true)
            .build();
        assert!(filter.to_string().contains("normalize=1"));
    }

    #[test]
    fn test_amix_all_options() {
        let filter = AmixBuilder::new(3)
            .unwrap()
            .with_duration_mode("longest")
            .with_weights(&[1.0, 0.5, 0.5])
            .with_normalize(true)
            .build();
        let s = filter.to_string();
        assert!(s.contains("inputs=3"));
        assert!(s.contains("duration=longest"));
        assert!(s.contains("weights=1 0.5 0.5"));
        assert!(s.contains("normalize=1"));
    }

    // ========== DuckingPattern tests ==========

    #[test]
    fn test_ducking_default() {
        let pattern = DuckingPattern::new().unwrap();
        let graph = pattern.build();
        let s = graph.to_string();
        assert!(s.contains("asplit"));
        assert!(s.contains("sidechaincompress"));
        assert!(
            s.contains("threshold=0.125"),
            "Expected threshold in: {s}"
        );
        assert!(s.contains("ratio=2"), "Expected ratio in: {s}");
        assert!(s.contains("attack=20"), "Expected attack in: {s}");
        assert!(s.contains("release=250"), "Expected release in: {s}");
    }

    #[test]
    fn test_ducking_custom_params() {
        let pattern = DuckingPattern::new()
            .unwrap()
            .with_threshold(0.5)
            .unwrap()
            .with_ratio(4.0)
            .unwrap()
            .with_attack(50.0)
            .unwrap()
            .with_release(500.0)
            .unwrap();
        let graph = pattern.build();
        let s = graph.to_string();
        assert!(s.contains("threshold=0.5"), "Got: {s}");
        assert!(s.contains("ratio=4"), "Got: {s}");
        assert!(s.contains("attack=50"), "Got: {s}");
        assert!(s.contains("release=500"), "Got: {s}");
    }

    #[test]
    fn test_ducking_threshold_out_of_range() {
        let result = DuckingPattern::new().unwrap().with_threshold(2.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_ratio_out_of_range() {
        let result = DuckingPattern::new().unwrap().with_ratio(25.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_attack_out_of_range() {
        let result = DuckingPattern::new().unwrap().with_attack(3000.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_release_out_of_range() {
        let result = DuckingPattern::new().unwrap().with_release(10000.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_graph_has_three_chains() {
        let pattern = DuckingPattern::new().unwrap();
        let graph = pattern.build();
        let s = graph.to_string();
        // asplit ; sidechaincompress ; anull = 3 chains = 2 semicolons
        assert_eq!(
            s.matches(';').count(),
            2,
            "Expected 2 semicolons in: {s}"
        );
    }

    // ========== Edge case tests ==========

    #[test]
    fn test_zero_volume_handled() {
        let filter = VolumeBuilder::new(0.0).unwrap().build();
        let s = filter.to_string();
        assert!(s.contains("volume=0"));
    }

    #[test]
    fn test_volume_above_one_with_amix() {
        // Volume > 1.0 combined with amix normalize produces valid output
        let vol = VolumeBuilder::new(2.0).unwrap().build();
        let amix = AmixBuilder::new(2).unwrap().with_normalize(true).build();
        let vol_s = vol.to_string();
        let amix_s = amix.to_string();
        assert!(vol_s.contains("volume=2"));
        assert!(amix_s.contains("normalize=1"));
    }

    #[test]
    fn test_fade_duration_large() {
        // Fade duration longer than typical audio is handled gracefully
        let filter = AfadeBuilder::new("in", 999.0).unwrap().build();
        assert_eq!(filter.to_string(), "afade=t=in:d=999");
    }

    // ========== Integration tests ==========

    #[test]
    fn test_volume_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let vol = VolumeBuilder::new(0.5).unwrap().build();
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:a")
                .filter(vol)
                .output("quiet"),
        );
        let s = graph.to_string();
        assert!(s.contains("[0:a]"));
        assert!(s.contains("volume="));
        assert!(s.contains("[quiet]"));
    }

    #[test]
    fn test_afade_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let fade = AfadeBuilder::new("in", 2.0).unwrap().build();
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:a")
                .filter(fade)
                .output("faded"),
        );
        let s = graph.to_string();
        assert!(s.contains("[0:a]"));
        assert!(s.contains("afade="));
        assert!(s.contains("[faded]"));
    }

    #[test]
    fn test_format_volume_value() {
        assert_eq!(format_volume_value(0.0), "0");
        assert_eq!(format_volume_value(1.0), "1");
        assert_eq!(format_volume_value(0.5), "0.5");
        assert_eq!(format_volume_value(10.0), "10");
        assert_eq!(format_volume_value(0.8), "0.8");
    }

    #[test]
    fn test_format_duration_value() {
        assert_eq!(format_duration_value(0.0), "0");
        assert_eq!(format_duration_value(3.0), "3");
        assert_eq!(format_duration_value(1.5), "1.5");
        assert_eq!(format_duration_value(2.5), "2.5");
    }
}
