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
            return Err(format!("dB volume must end with 'dB', got '{db_str}'"));
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
    fn py_precision<'a>(
        mut slf: PyRefMut<'a, Self>,
        precision: &str,
    ) -> PyResult<PyRefMut<'a, Self>> {
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
            return Err(format!("amix input count must be 2-32, got {inputs}"));
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
/// - Passes the compressed output through `anull` for labeling
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
/// assert!(s.contains("anull"));
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
            return Err(format!("threshold must be 0.00097563-1.0, got {threshold}"));
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
    /// 3. Passes compressed output through `anull` for labeled output
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
            .compose_merge(&[branches[0].as_str(), branches[1].as_str()], sc_filter)
            .expect("compose_merge with 2 inputs cannot fail");

        // Step 3: Pass compressed result through anull for labeled output
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

// ========== TrackAudioConfig ==========

/// Per-track audio configuration for multi-track mixing.
///
/// Specifies volume level and fade durations for a single audio track
/// within an [`AudioMixSpec`] composition.
///
/// # Fields
///
/// * `volume` - Volume multiplier in business range [0.0, 2.0]
/// * `fade_in` - Fade-in duration in seconds (0.0 = no fade)
/// * `fade_out` - Fade-out duration in seconds (0.0 = no fade)
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct TrackAudioConfig {
    /// Volume multiplier in range [0.0, 2.0].
    #[pyo3(get)]
    pub volume: f64,
    /// Fade-in duration in seconds (0.0 = no fade).
    #[pyo3(get)]
    pub fade_in: f64,
    /// Fade-out duration in seconds (0.0 = no fade).
    #[pyo3(get)]
    pub fade_out: f64,
}

#[pymethods]
impl TrackAudioConfig {
    /// Creates a new TrackAudioConfig.
    ///
    /// Args:
    ///     volume: Volume multiplier in range [0.0, 2.0].
    ///     fade_in: Fade-in duration in seconds (>= 0.0).
    ///     fade_out: Fade-out duration in seconds (>= 0.0).
    ///
    /// Raises:
    ///     ValueError: If volume is outside [0.0, 2.0] or fade durations are negative.
    #[new]
    fn py_new(volume: f64, fade_in: f64, fade_out: f64) -> PyResult<Self> {
        Self::new(volume, fade_in, fade_out).map_err(PyValueError::new_err)
    }

    /// Returns a string representation of the config.
    fn __repr__(&self) -> String {
        format!(
            "TrackAudioConfig(volume={}, fade_in={}, fade_out={})",
            format_volume_value(self.volume),
            format_duration_value(self.fade_in),
            format_duration_value(self.fade_out),
        )
    }
}

impl TrackAudioConfig {
    /// Creates a new TrackAudioConfig with validation.
    ///
    /// # Arguments
    ///
    /// * `volume` - Volume multiplier in range [0.0, 2.0]
    /// * `fade_in` - Fade-in duration in seconds (>= 0.0)
    /// * `fade_out` - Fade-out duration in seconds (>= 0.0)
    ///
    /// # Errors
    ///
    /// Returns an error if volume is outside [0.0, 2.0] or fade durations are negative.
    pub fn new(volume: f64, fade_in: f64, fade_out: f64) -> Result<Self, String> {
        if !(0.0..=2.0).contains(&volume) {
            return Err(format!(
                "track volume must be in range [0.0, 2.0], got {volume}"
            ));
        }
        if fade_in < 0.0 {
            return Err(format!("fade_in duration must be >= 0.0, got {fade_in}"));
        }
        if fade_out < 0.0 {
            return Err(format!("fade_out duration must be >= 0.0, got {fade_out}"));
        }
        Ok(Self {
            volume,
            fade_in,
            fade_out,
        })
    }
}

// ========== AudioMixSpec ==========

/// Coordinated multi-track audio mixing specification.
///
/// Wraps existing [`AmixBuilder`], [`VolumeBuilder`], and [`AfadeBuilder`] to
/// compose a complete filter chain for multi-track audio mixing with per-track
/// volume, fade-in, and fade-out.
///
/// # Business Constraints
///
/// * Volume range: [0.0, 2.0] (tighter than VolumeBuilder's [0.0, 10.0])
/// * Track count: [2, 8]
/// * Fade durations: >= 0.0 (0.0 = no fade, skips AfadeBuilder)
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::audio::{AudioMixSpec, TrackAudioConfig};
///
/// let tracks = vec![
///     TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap(),
///     TrackAudioConfig::new(0.5, 0.0, 0.0).unwrap(),
/// ];
/// let spec = AudioMixSpec::new(tracks).unwrap();
/// let chain = spec.build_filter_chain();
/// assert!(chain.contains("volume="));
/// assert!(chain.contains("amix="));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct AudioMixSpec {
    /// Per-track audio configurations.
    tracks: Vec<TrackAudioConfig>,
}

impl AudioMixSpec {
    /// Creates a new AudioMixSpec with validation.
    ///
    /// # Arguments
    ///
    /// * `tracks` - List of per-track audio configurations (2-8 tracks)
    ///
    /// # Errors
    ///
    /// Returns an error if track count is outside [2, 8].
    pub fn new(tracks: Vec<TrackAudioConfig>) -> Result<Self, String> {
        if tracks.len() < 2 {
            return Err(format!(
                "AudioMixSpec requires 2-8 tracks, got {}",
                tracks.len()
            ));
        }
        if tracks.len() > 8 {
            return Err(format!(
                "AudioMixSpec requires 2-8 tracks, got {}",
                tracks.len()
            ));
        }
        Ok(Self { tracks })
    }

    /// Builds a filter chain string for multi-track audio mixing.
    ///
    /// Composes per-track volume and fade filters followed by amix:
    /// - Creates VolumeBuilder per track (skipped if volume == 1.0)
    /// - Creates AfadeBuilder per track for fade_in/fade_out (skipped if duration == 0.0)
    /// - Creates AmixBuilder with the track count
    ///
    /// Returns the composed filter chain as a string.
    #[must_use]
    pub fn build_filter_chain(&self) -> String {
        let mut parts: Vec<String> = Vec::new();

        for (i, track) in self.tracks.iter().enumerate() {
            let mut track_filters: Vec<String> = Vec::new();

            // Volume filter (skip if 1.0 = unity gain)
            if (track.volume - 1.0).abs() > 1e-9 {
                let vol = VolumeBuilder::new(track.volume)
                    .expect("volume pre-validated in TrackAudioConfig");
                track_filters.push(vol.build().to_string());
            }

            // Fade-in filter (skip if 0.0)
            if track.fade_in > 0.0 {
                let fade =
                    AfadeBuilder::new("in", track.fade_in).expect("fade_in pre-validated as > 0");
                track_filters.push(fade.build().to_string());
            }

            // Fade-out filter (skip if 0.0)
            if track.fade_out > 0.0 {
                let fade = AfadeBuilder::new("out", track.fade_out)
                    .expect("fade_out pre-validated as > 0");
                track_filters.push(fade.build().to_string());
            }

            if !track_filters.is_empty() {
                parts.push(format!(
                    "[{i}:a]{filters}[a{i}]",
                    filters = track_filters.join(",")
                ));
            }
        }

        // AmixBuilder for combining all tracks
        let amix =
            AmixBuilder::new(self.tracks.len()).expect("track count pre-validated in range [2, 8]");

        // Build amix input labels
        let amix_inputs: Vec<String> = (0..self.tracks.len())
            .map(|i| {
                // Use labeled output if track had filters, otherwise use raw input
                let has_filters = {
                    let t = &self.tracks[i];
                    (t.volume - 1.0).abs() > 1e-9 || t.fade_in > 0.0 || t.fade_out > 0.0
                };
                if has_filters {
                    format!("[a{i}]")
                } else {
                    format!("[{i}:a]")
                }
            })
            .collect();

        let amix_str = format!("{}{}", amix_inputs.join(""), amix.build());

        if parts.is_empty() {
            amix_str
        } else {
            parts.push(amix_str);
            parts.join(";")
        }
    }
}

// ========== AudioMixSpec PyO3 bindings ==========

#[pymethods]
impl AudioMixSpec {
    /// Creates a new AudioMixSpec from a list of TrackAudioConfig.
    ///
    /// Args:
    ///     tracks: List of TrackAudioConfig (2-8 tracks).
    ///
    /// Raises:
    ///     ValueError: If track count is outside [2, 8].
    #[new]
    fn py_new(tracks: Vec<TrackAudioConfig>) -> PyResult<Self> {
        Self::new(tracks).map_err(PyValueError::new_err)
    }

    /// Builds the filter chain string for multi-track audio mixing.
    ///
    /// Returns:
    ///     A string containing the composed FFmpeg filter chain.
    #[pyo3(name = "build_filter_chain")]
    fn py_build_filter_chain(&self) -> String {
        self.build_filter_chain()
    }

    /// Returns the number of tracks.
    #[pyo3(name = "track_count")]
    fn py_track_count(&self) -> usize {
        self.tracks.len()
    }

    /// Returns a string representation of the spec.
    fn __repr__(&self) -> String {
        format!("AudioMixSpec(tracks={})", self.tracks.len())
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
        let filter = AmixBuilder::new(2).unwrap().with_normalize(false).build();
        assert!(filter.to_string().contains("normalize=0"));
    }

    #[test]
    fn test_amix_normalize_enabled() {
        let filter = AmixBuilder::new(2).unwrap().with_normalize(true).build();
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
        assert!(s.contains("threshold=0.125"), "Expected threshold in: {s}");
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
        assert_eq!(s.matches(';').count(), 2, "Expected 2 semicolons in: {s}");
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
        let graph =
            FilterGraph::new().chain(FilterChain::new().input("0:a").filter(vol).output("quiet"));
        let s = graph.to_string();
        assert!(s.contains("[0:a]"));
        assert!(s.contains("volume="));
        assert!(s.contains("[quiet]"));
    }

    #[test]
    fn test_afade_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let fade = AfadeBuilder::new("in", 2.0).unwrap().build();
        let graph =
            FilterGraph::new().chain(FilterChain::new().input("0:a").filter(fade).output("faded"));
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

    // ========== Additional error path tests ==========

    #[test]
    fn test_volume_builder_db_no_suffix() {
        let result = VolumeBuilder::new_db("3");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("dB"));
    }

    #[test]
    fn test_volume_builder_db_invalid_numeric() {
        let result = VolumeBuilder::new_db("abcdB");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("invalid dB"));
    }

    #[test]
    fn test_ducking_threshold_below_min() {
        let result = DuckingPattern::new().unwrap().with_threshold(0.0001);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_ratio_below_min() {
        let result = DuckingPattern::new().unwrap().with_ratio(0.5);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_attack_below_min() {
        let result = DuckingPattern::new().unwrap().with_attack(0.001);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_release_below_min() {
        let result = DuckingPattern::new().unwrap().with_release(0.001);
        assert!(result.is_err());
    }

    #[test]
    fn test_ducking_boundary_values_valid() {
        // Minimum valid values
        let d = DuckingPattern::new()
            .unwrap()
            .with_threshold(0.00097563)
            .unwrap()
            .with_ratio(1.0)
            .unwrap()
            .with_attack(0.01)
            .unwrap()
            .with_release(0.01)
            .unwrap();
        let graph = d.build();
        assert!(!graph.to_string().is_empty());

        // Maximum valid values
        let d = DuckingPattern::new()
            .unwrap()
            .with_threshold(1.0)
            .unwrap()
            .with_ratio(20.0)
            .unwrap()
            .with_attack(2000.0)
            .unwrap()
            .with_release(9000.0)
            .unwrap();
        let graph = d.build();
        assert!(!graph.to_string().is_empty());
    }

    #[test]
    fn test_volume_repr() {
        let builder = VolumeBuilder::new(0.5).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("VolumeBuilder"));
        assert!(repr.contains("0.5"));
    }

    #[test]
    fn test_afade_repr() {
        let builder = AfadeBuilder::new("in", 2.0).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("AfadeBuilder"));
        assert!(repr.contains("in"));
    }

    #[test]
    fn test_amix_repr() {
        let builder = AmixBuilder::new(3).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("AmixBuilder"));
        assert!(repr.contains("3"));
    }

    #[test]
    fn test_ducking_repr() {
        let pattern = DuckingPattern::new().unwrap();
        let repr = pattern.__repr__();
        assert!(repr.contains("DuckingPattern"));
        assert!(repr.contains("0.125"));
    }

    #[test]
    fn test_amix_zero_inputs() {
        let result = AmixBuilder::new(0);
        assert!(result.is_err());
    }

    #[test]
    fn test_format_volume_value_precision() {
        assert_eq!(format_volume_value(0.333), "0.333");
        assert_eq!(format_volume_value(2.0), "2");
        assert_eq!(format_volume_value(0.125), "0.125");
    }

    // ========== Proptest ==========

    use proptest::prelude::*;

    proptest! {
        /// Property: all valid volumes produce valid filter strings.
        #[test]
        fn volume_builder_valid(volume in 0.0f64..=10.0) {
            let builder = VolumeBuilder::new(volume).unwrap();
            let filter = builder.build();
            let s = filter.to_string();
            prop_assert!(s.starts_with("volume="), "Got: {}", s);
            prop_assert!(s.contains("volume="), "Missing volume param: {}", s);
        }

        /// Property: all valid fade durations produce valid afade filter strings.
        #[test]
        fn afade_builder_valid(duration in 0.01f64..=300.0) {
            let fade_type = if duration.to_bits() % 2 == 0 { "in" } else { "out" };
            let builder = AfadeBuilder::new(fade_type, duration).unwrap();
            let filter = builder.build();
            let s = filter.to_string();
            prop_assert!(s.starts_with("afade="), "Got: {}", s);
            prop_assert!(s.contains("t="), "Missing type param: {}", s);
            prop_assert!(s.contains("d="), "Missing duration param: {}", s);
        }

        /// Property: all valid input counts produce valid amix filter strings.
        #[test]
        fn amix_builder_valid(inputs in 2usize..=8) {
            let builder = AmixBuilder::new(inputs).unwrap();
            let filter = builder.build();
            let s = filter.to_string();
            prop_assert!(s.starts_with("amix="), "Got: {}", s);
            prop_assert!(s.contains("inputs="), "Missing inputs param: {}", s);
        }
    }

    // ========== PyO3 binding tests ==========

    use pyo3::prelude::*;

    #[test]
    fn test_pyo3_volume_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            // Test py_new (valid)
            let vb = Bound::new(py, VolumeBuilder::new(0.5).unwrap()).unwrap();
            vb.call_method1("precision", ("float",)).unwrap();
            let _filter: String = vb
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            let repr: String = vb.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("VolumeBuilder"));

            // Test py_precision error
            let vb2 = Bound::new(py, VolumeBuilder::new(1.0).unwrap()).unwrap();
            assert!(vb2.call_method1("precision", ("invalid",)).is_err());

            // Test from_db
            let vb3 = VolumeBuilder::py_from_db("3dB").unwrap();
            assert!(vb3.__repr__().contains("3dB"));
            assert!(VolumeBuilder::py_from_db("bad").is_err());

            // Test py_new error
            let result = VolumeBuilder::py_new(-1.0);
            assert!(result.is_err());
        });
    }

    #[test]
    fn test_pyo3_afade_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let ab = Bound::new(py, AfadeBuilder::new("in", 2.0).unwrap()).unwrap();
            ab.call_method1("start_time", (5.0f64,)).unwrap();
            ab.call_method1("curve", ("qsin",)).unwrap();
            let _filter: String = ab
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            let repr: String = ab.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("AfadeBuilder"));

            // Test curve error
            let ab2 = Bound::new(py, AfadeBuilder::new("out", 1.0).unwrap()).unwrap();
            assert!(ab2.call_method1("curve", ("invalid",)).is_err());

            // Test py_new error
            assert!(AfadeBuilder::py_new("bad", 1.0).is_err());
            assert!(AfadeBuilder::py_new("in", 0.0).is_err());
        });
    }

    #[test]
    fn test_pyo3_amix_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let am = Bound::new(py, AmixBuilder::new(3).unwrap()).unwrap();
            am.call_method1("duration_mode", ("longest",)).unwrap();
            am.call_method1("weights", (vec![1.0f64, 0.5, 0.5],))
                .unwrap();
            am.call_method1("normalize", (true,)).unwrap();
            let _filter: String = am
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            let repr: String = am.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("AmixBuilder"));

            // Test duration_mode error
            let am2 = Bound::new(py, AmixBuilder::new(2).unwrap()).unwrap();
            assert!(am2.call_method1("duration_mode", ("invalid",)).is_err());

            // Test py_new error
            assert!(AmixBuilder::py_new(1).is_err());
        });
    }

    #[test]
    fn test_pyo3_ducking_pattern() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let dp = Bound::new(py, DuckingPattern::new().unwrap()).unwrap();
            dp.call_method1("threshold", (0.5f64,)).unwrap();
            dp.call_method1("ratio", (4.0f64,)).unwrap();
            dp.call_method1("attack", (50.0f64,)).unwrap();
            dp.call_method1("release", (500.0f64,)).unwrap();
            let _graph: String = dp
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            let repr: String = dp.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("DuckingPattern"));

            // Test error paths
            let dp2 = Bound::new(py, DuckingPattern::new().unwrap()).unwrap();
            assert!(dp2.call_method1("threshold", (2.0f64,)).is_err());
            assert!(dp2.call_method1("ratio", (25.0f64,)).is_err());
            assert!(dp2.call_method1("attack", (3000.0f64,)).is_err());
            assert!(dp2.call_method1("release", (10000.0f64,)).is_err());
        });
    }

    // ========== TrackAudioConfig tests ==========

    #[test]
    fn test_track_config_valid() {
        let config = TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap();
        assert!((config.volume - 0.8).abs() < 1e-9);
        assert!((config.fade_in - 1.0).abs() < 1e-9);
        assert!((config.fade_out - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_track_config_zero_volume() {
        let config = TrackAudioConfig::new(0.0, 0.0, 0.0).unwrap();
        assert!((config.volume).abs() < 1e-9);
    }

    #[test]
    fn test_track_config_max_volume() {
        let config = TrackAudioConfig::new(2.0, 0.0, 0.0).unwrap();
        assert!((config.volume - 2.0).abs() < 1e-9);
    }

    #[test]
    fn test_track_config_volume_below_range() {
        let result = TrackAudioConfig::new(-0.1, 0.0, 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("[0.0, 2.0]"));
    }

    #[test]
    fn test_track_config_volume_above_range() {
        let result = TrackAudioConfig::new(2.1, 0.0, 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("[0.0, 2.0]"));
    }

    #[test]
    fn test_track_config_negative_fade_in() {
        let result = TrackAudioConfig::new(1.0, -0.1, 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("fade_in"));
    }

    #[test]
    fn test_track_config_negative_fade_out() {
        let result = TrackAudioConfig::new(1.0, 0.0, -0.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("fade_out"));
    }

    #[test]
    fn test_track_config_no_fade() {
        let config = TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap();
        assert!((config.fade_in).abs() < 1e-9);
        assert!((config.fade_out).abs() < 1e-9);
    }

    #[test]
    fn test_track_config_repr() {
        let config = TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap();
        let repr = config.__repr__();
        assert!(repr.contains("TrackAudioConfig"));
        assert!(repr.contains("0.8"));
    }

    // ========== AudioMixSpec tests ==========

    #[test]
    fn test_audio_mix_spec_two_tracks() {
        let tracks = vec![
            TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap(),
            TrackAudioConfig::new(0.5, 0.0, 0.0).unwrap(),
        ];
        let spec = AudioMixSpec::new(tracks).unwrap();
        let chain = spec.build_filter_chain();
        assert!(chain.contains("volume="), "Missing volume in: {chain}");
        assert!(chain.contains("amix=inputs=2"), "Missing amix in: {chain}");
    }

    #[test]
    fn test_audio_mix_spec_eight_tracks() {
        let tracks: Vec<TrackAudioConfig> = (0..8)
            .map(|i| TrackAudioConfig::new(0.5 + (i as f64) * 0.1, 0.0, 0.0).unwrap())
            .collect();
        let spec = AudioMixSpec::new(tracks).unwrap();
        let chain = spec.build_filter_chain();
        assert!(chain.contains("amix=inputs=8"), "Missing amix in: {chain}");
    }

    #[test]
    fn test_audio_mix_spec_single_track_rejected() {
        let tracks = vec![TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap()];
        let result = AudioMixSpec::new(tracks);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("2-8"));
    }

    #[test]
    fn test_audio_mix_spec_nine_tracks_rejected() {
        let tracks: Vec<TrackAudioConfig> = (0..9)
            .map(|_| TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap())
            .collect();
        let result = AudioMixSpec::new(tracks);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("2-8"));
    }

    #[test]
    fn test_audio_mix_spec_muted_tracks() {
        let tracks = vec![
            TrackAudioConfig::new(0.0, 0.0, 0.0).unwrap(),
            TrackAudioConfig::new(0.0, 0.0, 0.0).unwrap(),
        ];
        let spec = AudioMixSpec::new(tracks).unwrap();
        let chain = spec.build_filter_chain();
        assert!(
            chain.contains("volume=0"),
            "Missing muted volume in: {chain}"
        );
        assert!(chain.contains("amix="), "Missing amix in: {chain}");
    }

    #[test]
    fn test_audio_mix_spec_unity_volume_skip() {
        // When volume is 1.0, no volume filter should be generated
        let tracks = vec![
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(),
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(),
        ];
        let spec = AudioMixSpec::new(tracks).unwrap();
        let chain = spec.build_filter_chain();
        assert!(
            !chain.contains("volume="),
            "Unity volume should be skipped: {chain}"
        );
        assert!(chain.contains("amix=inputs=2"), "Missing amix in: {chain}");
    }

    #[test]
    fn test_audio_mix_spec_fade_in_out() {
        let tracks = vec![
            TrackAudioConfig::new(1.0, 2.0, 1.5).unwrap(),
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(),
        ];
        let spec = AudioMixSpec::new(tracks).unwrap();
        let chain = spec.build_filter_chain();
        assert!(
            chain.contains("afade=t=in:d=2"),
            "Missing fade-in in: {chain}"
        );
        assert!(
            chain.contains("afade=t=out:d=1.5"),
            "Missing fade-out in: {chain}"
        );
    }

    #[test]
    fn test_audio_mix_spec_zero_fade_skip() {
        // When fade is 0.0, no afade filter should be generated
        let tracks = vec![
            TrackAudioConfig::new(0.8, 0.0, 0.0).unwrap(),
            TrackAudioConfig::new(0.5, 0.0, 0.0).unwrap(),
        ];
        let spec = AudioMixSpec::new(tracks).unwrap();
        let chain = spec.build_filter_chain();
        assert!(
            !chain.contains("afade="),
            "Zero fade should be skipped: {chain}"
        );
    }

    #[test]
    fn test_audio_mix_spec_all_features() {
        let tracks = vec![
            TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap(),
            TrackAudioConfig::new(0.5, 2.0, 1.0).unwrap(),
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(),
        ];
        let spec = AudioMixSpec::new(tracks).unwrap();
        let chain = spec.build_filter_chain();
        // Track 0: volume + fade_in + fade_out
        assert!(
            chain.contains("volume=0.8"),
            "Missing track 0 volume: {chain}"
        );
        assert!(
            chain.contains("afade=t=in:d=1"),
            "Missing track 0 fade-in: {chain}"
        );
        assert!(
            chain.contains("afade=t=out:d=0.5"),
            "Missing track 0 fade-out: {chain}"
        );
        // Track 1: volume + fade_in + fade_out
        assert!(
            chain.contains("volume=0.5"),
            "Missing track 1 volume: {chain}"
        );
        // Track 2: unity volume, no fades — uses raw input
        assert!(
            chain.contains("[2:a]"),
            "Missing raw track 2 input: {chain}"
        );
        // amix
        assert!(chain.contains("amix=inputs=3"), "Missing amix: {chain}");
    }

    #[test]
    fn test_audio_mix_spec_repr() {
        let tracks = vec![
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(),
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(),
        ];
        let spec = AudioMixSpec::new(tracks).unwrap();
        let repr = spec.__repr__();
        assert!(repr.contains("AudioMixSpec"));
        assert!(repr.contains("2"));
    }

    // ========== AudioMixSpec proptest ==========

    proptest! {
        /// Property: valid volumes [0.0, 2.0] always accepted by TrackAudioConfig.
        #[test]
        fn track_config_valid_volume(volume in 0.0f64..=2.0) {
            let config = TrackAudioConfig::new(volume, 0.0, 0.0);
            prop_assert!(config.is_ok(), "Valid volume {} rejected", volume);
        }

        /// Property: volumes outside [0.0, 2.0] always rejected by TrackAudioConfig.
        #[test]
        fn track_config_invalid_volume_below(volume in -100.0f64..0.0) {
            // Exclude exact 0.0 since that's valid
            if volume < 0.0 {
                let config = TrackAudioConfig::new(volume, 0.0, 0.0);
                prop_assert!(config.is_err(), "Invalid volume {} accepted", volume);
            }
        }

        /// Property: volumes above 2.0 always rejected by TrackAudioConfig.
        #[test]
        fn track_config_invalid_volume_above(volume in 2.001f64..100.0) {
            let config = TrackAudioConfig::new(volume, 0.0, 0.0);
            prop_assert!(config.is_err(), "Invalid volume {} accepted", volume);
        }

        /// Property: valid fade durations [0.0, 300.0] always accepted.
        #[test]
        fn track_config_valid_fade(fade_in in 0.0f64..=300.0, fade_out in 0.0f64..=300.0) {
            let config = TrackAudioConfig::new(1.0, fade_in, fade_out);
            prop_assert!(config.is_ok(), "Valid fades ({}, {}) rejected", fade_in, fade_out);
        }

        /// Property: negative fade durations always rejected.
        #[test]
        fn track_config_negative_fade_in(fade_in in -100.0f64..-0.001) {
            let config = TrackAudioConfig::new(1.0, fade_in, 0.0);
            prop_assert!(config.is_err(), "Negative fade_in {} accepted", fade_in);
        }

        /// Property: negative fade_out durations always rejected.
        #[test]
        fn track_config_negative_fade_out(fade_out in -100.0f64..-0.001) {
            let config = TrackAudioConfig::new(1.0, 0.0, fade_out);
            prop_assert!(config.is_err(), "Negative fade_out {} accepted", fade_out);
        }

        /// Property: AudioMixSpec with valid track counts [2, 8] always succeeds.
        #[test]
        fn audio_mix_spec_valid_count(count in 2usize..=8) {
            let tracks: Vec<TrackAudioConfig> = (0..count)
                .map(|_| TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap())
                .collect();
            let spec = AudioMixSpec::new(tracks);
            prop_assert!(spec.is_ok(), "Valid count {} rejected", count);
        }

        /// Property: AudioMixSpec with random valid configs always produces non-empty filter chain.
        #[test]
        fn audio_mix_spec_produces_output(
            vol0 in 0.0f64..=2.0,
            vol1 in 0.0f64..=2.0,
            fade_in0 in 0.0f64..=5.0,
            fade_out0 in 0.0f64..=5.0,
        ) {
            let tracks = vec![
                TrackAudioConfig::new(vol0, fade_in0, fade_out0).unwrap(),
                TrackAudioConfig::new(vol1, 0.0, 0.0).unwrap(),
            ];
            let spec = AudioMixSpec::new(tracks).unwrap();
            let chain = spec.build_filter_chain();
            prop_assert!(!chain.is_empty(), "Empty filter chain");
            prop_assert!(chain.contains("amix="), "Missing amix in: {}", chain);
        }
    }

    // ========== AudioMixSpec PyO3 binding tests ==========

    #[test]
    fn test_pyo3_audio_mix_spec() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            // Create TrackAudioConfigs
            let t0 = Bound::new(py, TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap()).unwrap();
            let t1 = Bound::new(py, TrackAudioConfig::new(0.5, 0.0, 0.0).unwrap()).unwrap();

            // Test TrackAudioConfig getters
            let vol: f64 = t0.getattr("volume").unwrap().extract().unwrap();
            assert!((vol - 0.8).abs() < 1e-9);
            let fi: f64 = t0.getattr("fade_in").unwrap().extract().unwrap();
            assert!((fi - 1.0).abs() < 1e-9);
            let fo: f64 = t0.getattr("fade_out").unwrap().extract().unwrap();
            assert!((fo - 0.5).abs() < 1e-9);

            // Test TrackAudioConfig repr
            let repr: String = t0.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("TrackAudioConfig"));

            // Create AudioMixSpec
            let tracks = vec![
                TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap(),
                TrackAudioConfig::new(0.5, 0.0, 0.0).unwrap(),
            ];
            let spec = Bound::new(py, AudioMixSpec::new(tracks).unwrap()).unwrap();

            // Test build_filter_chain
            let chain: String = spec
                .call_method0("build_filter_chain")
                .unwrap()
                .extract()
                .unwrap();
            assert!(chain.contains("amix="), "Missing amix in: {chain}");

            // Test track_count
            let count: usize = spec.call_method0("track_count").unwrap().extract().unwrap();
            assert_eq!(count, 2);

            // Test repr
            let repr: String = spec.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("AudioMixSpec"));
            assert!(repr.contains("2"));

            // Test py_new error (too few tracks)
            let result = AudioMixSpec::py_new(vec![TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap()]);
            assert!(result.is_err());

            // Test TrackAudioConfig py_new error
            let result = TrackAudioConfig::py_new(3.0, 0.0, 0.0);
            assert!(result.is_err());
        });
    }
}
