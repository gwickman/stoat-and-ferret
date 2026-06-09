//! Voice repair filter builders for FFmpeg.
//!
//! This module provides type-safe builders for noise reduction and click removal:
//!
//! - [`NoiseReductionBuilder`] - Broadband noise reduction (`afftdn`) and click removal (`adeclick`)
//!
//! All builders follow the fluent pattern: construct, configure, then `.build()`.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::voice_repair::NoiseReductionBuilder;
//!
//! let filter = NoiseReductionBuilder::new("broadband").unwrap().build();
//! assert!(filter.to_string().starts_with("afftdn=nr="));
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::filter::{Filter, FilterChain};

// ========== NoiseReductionBuilder ==========

/// Type-safe builder for FFmpeg noise reduction filters.
///
/// Supports two modes:
/// - `"broadband"`: uses `afftdn` (adaptive spectral noise reduction) with configurable strength
/// - `"adeclick"`: uses `adeclick` (impulse/click removal) with configurable threshold
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::voice_repair::NoiseReductionBuilder;
///
/// let filter = NoiseReductionBuilder::new("broadband").unwrap().build();
/// assert!(filter.to_string().starts_with("afftdn=nr="));
///
/// let filter = NoiseReductionBuilder::new("adeclick").unwrap().build();
/// assert_eq!(filter.to_string(), "adeclick");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct NoiseReductionBuilder {
    /// Noise reduction mode: "broadband" or "adeclick".
    mode: String,
    /// Noise reduction strength (0.0–1.0). Used in broadband mode; maps to afftdn nr=0..97.
    strength: f64,
    /// Click detection threshold (0.0–1.0). Used in adeclick mode.
    threshold: f64,
}

impl NoiseReductionBuilder {
    /// Creates a new NoiseReductionBuilder with the given mode.
    ///
    /// # Arguments
    ///
    /// * `mode` - "broadband" (uses afftdn) or "adeclick" (uses adeclick filter)
    ///
    /// # Errors
    ///
    /// Returns an error if mode is not "broadband" or "adeclick".
    pub fn new(mode: &str) -> Result<Self, String> {
        match mode {
            "broadband" | "adeclick" => {}
            _ => {
                return Err(format!(
                    "mode must be 'broadband' or 'adeclick', got '{mode}'"
                ))
            }
        }
        Ok(Self {
            mode: mode.to_string(),
            strength: 0.5,
            threshold: 0.5,
        })
    }

    /// Sets the noise reduction strength (0.0–1.0). Only used in broadband mode.
    ///
    /// # Errors
    ///
    /// Returns an error if strength is outside [0.0, 1.0].
    pub fn with_strength(mut self, strength: f64) -> Result<Self, String> {
        if !(0.0..=1.0).contains(&strength) {
            return Err(format!("strength must be in [0.0, 1.0], got {strength}"));
        }
        self.strength = strength;
        Ok(self)
    }

    /// Sets the click detection threshold (0.0–1.0). Only used in adeclick mode.
    ///
    /// # Errors
    ///
    /// Returns an error if threshold is outside [0.0, 1.0].
    pub fn with_threshold(mut self, threshold: f64) -> Result<Self, String> {
        if !(0.0..=1.0).contains(&threshold) {
            return Err(format!("threshold must be in [0.0, 1.0], got {threshold}"));
        }
        self.threshold = threshold;
        Ok(self)
    }

    /// Builds the noise reduction Filter.
    ///
    /// - `"broadband"` mode: emits `afftdn=nr=<strength>` where strength maps 0.0–1.0 → 0–97
    /// - `"adeclick"` mode: emits `adeclick=` (default FFmpeg parameters)
    #[must_use]
    pub fn build(&self) -> Filter {
        match self.mode.as_str() {
            "broadband" => {
                let nr = (self.strength * 97.0).round() as u32;
                Filter::new("afftdn").param("nr", nr.to_string())
            }
            "adeclick" => Filter::new("adeclick"),
            _ => unreachable!("mode is validated in new()"),
        }
    }
}

// ========== NoiseReductionBuilder PyO3 bindings ==========

#[pymethods]
impl NoiseReductionBuilder {
    /// Creates a new NoiseReductionBuilder.
    ///
    /// Args:
    ///     mode: "broadband" (afftdn adaptive spectral NR) or "adeclick" (click/impulse removal).
    ///
    /// Raises:
    ///     ValueError: If mode is not "broadband" or "adeclick".
    #[new]
    fn py_new(mode: &str) -> PyResult<Self> {
        Self::new(mode).map_err(PyValueError::new_err)
    }

    /// Sets the noise reduction strength (0.0–1.0). Used in broadband mode.
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If strength is outside [0.0, 1.0].
    #[pyo3(name = "strength")]
    fn py_strength<'a>(mut slf: PyRefMut<'a, Self>, strength: f64) -> PyResult<PyRefMut<'a, Self>> {
        if !(0.0..=1.0).contains(&strength) {
            return Err(PyValueError::new_err(format!(
                "strength must be in [0.0, 1.0], got {strength}"
            )));
        }
        slf.strength = strength;
        Ok(slf)
    }

    /// Sets the click detection threshold (0.0–1.0). Used in adeclick mode.
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If threshold is outside [0.0, 1.0].
    #[pyo3(name = "threshold")]
    fn py_threshold<'a>(
        mut slf: PyRefMut<'a, Self>,
        threshold: f64,
    ) -> PyResult<PyRefMut<'a, Self>> {
        if !(0.0..=1.0).contains(&threshold) {
            return Err(PyValueError::new_err(format!(
                "threshold must be in [0.0, 1.0], got {threshold}"
            )));
        }
        slf.threshold = threshold;
        Ok(slf)
    }

    /// Builds the noise reduction Filter.
    ///
    /// Returns:
    ///     A Filter with the appropriate noise reduction syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        match self.mode.as_str() {
            "broadband" => format!(
                "NoiseReductionBuilder(mode='broadband', strength={})",
                self.strength
            ),
            "adeclick" => format!(
                "NoiseReductionBuilder(mode='adeclick', threshold={})",
                self.threshold
            ),
            _ => format!("NoiseReductionBuilder(mode='{}')", self.mode),
        }
    }
}

// ========== DeesserBuilder ==========

/// Type-safe builder for FFmpeg de-esser filter.
///
/// Reduces sibilant energy ("s", "sh") using the FFmpeg `deesser` filter.
/// Configurable frequency and mode ("wide" or "split").
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::voice_repair::DeesserBuilder;
///
/// let filter = DeesserBuilder::new(6000.0).unwrap().build();
/// assert!(filter.to_string().starts_with("deesser=f=6000"));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct DeesserBuilder {
    /// Sibilance detection frequency in Hz (1000–16000).
    frequency: f64,
    /// Filter mode: "wide" (affects full range) or "split" (splits at frequency).
    mode: String,
}

impl DeesserBuilder {
    /// Creates a new DeesserBuilder with the given frequency.
    ///
    /// # Arguments
    ///
    /// * `frequency` - Sibilance detection frequency in Hz (1000–16000)
    ///
    /// # Errors
    ///
    /// Returns an error if frequency is outside [1000, 16000].
    pub fn new(frequency: f64) -> Result<Self, String> {
        if !(1000.0..=16000.0).contains(&frequency) {
            return Err(format!(
                "frequency must be in [1000, 16000] Hz, got {frequency}"
            ));
        }
        Ok(Self {
            frequency,
            mode: "wide".to_string(),
        })
    }

    /// Sets the filter mode ("wide" or "split").
    ///
    /// # Errors
    ///
    /// Returns an error if mode is not "wide" or "split".
    pub fn with_mode(mut self, mode: &str) -> Result<Self, String> {
        match mode {
            "wide" | "split" => {}
            _ => return Err(format!("mode must be 'wide' or 'split', got '{mode}'")),
        }
        self.mode = mode.to_string();
        Ok(self)
    }

    /// Builds the de-esser Filter.
    ///
    /// Emits `deesser=f=<freq>:m=<mode>`.
    #[must_use]
    pub fn build(&self) -> Filter {
        Filter::new("deesser")
            .param("f", format!("{}", self.frequency as u32))
            .param("m", self.mode.clone())
    }
}

// ========== DeesserBuilder PyO3 bindings ==========

#[pymethods]
impl DeesserBuilder {
    /// Creates a new DeesserBuilder.
    ///
    /// Args:
    ///     frequency: Sibilance detection frequency in Hz (1000–16000).
    ///
    /// Raises:
    ///     ValueError: If frequency is outside [1000, 16000].
    #[new]
    fn py_new(frequency: f64) -> PyResult<Self> {
        Self::new(frequency).map_err(PyValueError::new_err)
    }

    /// Sets the filter mode ("wide" or "split").
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If mode is not "wide" or "split".
    #[pyo3(name = "mode")]
    fn py_mode<'a>(mut slf: PyRefMut<'a, Self>, mode: &str) -> PyResult<PyRefMut<'a, Self>> {
        match mode {
            "wide" | "split" => {}
            _ => {
                return Err(PyValueError::new_err(format!(
                    "mode must be 'wide' or 'split', got '{mode}'"
                )))
            }
        }
        slf.mode = mode.to_string();
        Ok(slf)
    }

    /// Builds the de-esser Filter.
    ///
    /// Returns:
    ///     A Filter with deesser=f=<freq>:m=<mode> syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!(
            "DeesserBuilder(frequency={}, mode='{}')",
            self.frequency, self.mode
        )
    }
}

// ========== DeplosiveBuilder ==========

/// Type-safe builder for FFmpeg de-plosive filter chain.
///
/// Attenuates low-frequency plosive bursts ("p", "b") using a composite chain:
/// `highpass` (removes sub-cutoff energy) → `acompressor` (controls burst peaks).
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::voice_repair::DeplosiveBuilder;
///
/// let chain = DeplosiveBuilder::new().build();
/// let s = chain.to_string();
/// assert!(s.contains("highpass"));
/// assert!(s.contains("acompressor"));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct DeplosiveBuilder {
    /// Highpass cutoff frequency in Hz (10–200).
    cutoff: f64,
    /// Acompressor threshold (0.0–1.0).
    threshold: f64,
    /// Acompressor ratio (1.0–20.0).
    ratio: f64,
}

impl DeplosiveBuilder {
    /// Creates a new DeplosiveBuilder with default parameters.
    ///
    /// Defaults: cutoff=60 Hz, threshold=0.1, ratio=4.0.
    #[must_use]
    pub fn new() -> Self {
        Self {
            cutoff: 60.0,
            threshold: 0.1,
            ratio: 4.0,
        }
    }

    /// Sets the highpass cutoff frequency in Hz (10–200).
    ///
    /// # Errors
    ///
    /// Returns an error if cutoff is outside [10, 200].
    pub fn with_cutoff(mut self, cutoff: f64) -> Result<Self, String> {
        if !(10.0..=200.0).contains(&cutoff) {
            return Err(format!("cutoff must be in [10, 200] Hz, got {cutoff}"));
        }
        self.cutoff = cutoff;
        Ok(self)
    }

    /// Sets the acompressor threshold (0.0–1.0).
    ///
    /// # Errors
    ///
    /// Returns an error if threshold is outside [0.0, 1.0].
    pub fn with_threshold(mut self, threshold: f64) -> Result<Self, String> {
        if !(0.0..=1.0).contains(&threshold) {
            return Err(format!("threshold must be in [0.0, 1.0], got {threshold}"));
        }
        self.threshold = threshold;
        Ok(self)
    }

    /// Sets the acompressor ratio (1.0–20.0).
    ///
    /// # Errors
    ///
    /// Returns an error if ratio is outside [1.0, 20.0].
    pub fn with_ratio(mut self, ratio: f64) -> Result<Self, String> {
        if !(1.0..=20.0).contains(&ratio) {
            return Err(format!("ratio must be in [1.0, 20.0], got {ratio}"));
        }
        self.ratio = ratio;
        Ok(self)
    }

    /// Builds the de-plosive FilterChain.
    ///
    /// Emits: `highpass=f=<cutoff>,acompressor=threshold=<t>:ratio=<r>:attack=5:release=50`
    #[must_use]
    pub fn build(&self) -> FilterChain {
        let hp = Filter::new("highpass").param("f", format!("{}", self.cutoff as u32));
        let comp = Filter::new("acompressor")
            .param("threshold", format!("{}", self.threshold))
            .param("ratio", format!("{}", self.ratio))
            .param("attack", "5".to_string())
            .param("release", "50".to_string());
        FilterChain::new().filter(hp).filter(comp)
    }
}

impl Default for DeplosiveBuilder {
    fn default() -> Self {
        Self::new()
    }
}

// ========== DeplosiveBuilder PyO3 bindings ==========

#[pymethods]
impl DeplosiveBuilder {
    /// Creates a new DeplosiveBuilder with default parameters.
    ///
    /// Defaults: cutoff=60 Hz, threshold=0.1, ratio=4.0.
    #[new]
    fn py_new() -> Self {
        Self::new()
    }

    /// Sets the highpass cutoff frequency in Hz (10–200).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If cutoff is outside [10, 200].
    #[pyo3(name = "cutoff")]
    fn py_cutoff<'a>(mut slf: PyRefMut<'a, Self>, cutoff: f64) -> PyResult<PyRefMut<'a, Self>> {
        if !(10.0..=200.0).contains(&cutoff) {
            return Err(PyValueError::new_err(format!(
                "cutoff must be in [10, 200] Hz, got {cutoff}"
            )));
        }
        slf.cutoff = cutoff;
        Ok(slf)
    }

    /// Sets the acompressor threshold (0.0–1.0).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If threshold is outside [0.0, 1.0].
    #[pyo3(name = "threshold")]
    fn py_threshold<'a>(
        mut slf: PyRefMut<'a, Self>,
        threshold: f64,
    ) -> PyResult<PyRefMut<'a, Self>> {
        if !(0.0..=1.0).contains(&threshold) {
            return Err(PyValueError::new_err(format!(
                "threshold must be in [0.0, 1.0], got {threshold}"
            )));
        }
        slf.threshold = threshold;
        Ok(slf)
    }

    /// Sets the acompressor ratio (1.0–20.0).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If ratio is outside [1.0, 20.0].
    #[pyo3(name = "ratio")]
    fn py_ratio<'a>(mut slf: PyRefMut<'a, Self>, ratio: f64) -> PyResult<PyRefMut<'a, Self>> {
        if !(1.0..=20.0).contains(&ratio) {
            return Err(PyValueError::new_err(format!(
                "ratio must be in [1.0, 20.0], got {ratio}"
            )));
        }
        slf.ratio = ratio;
        Ok(slf)
    }

    /// Builds the de-plosive FilterChain.
    ///
    /// Returns:
    ///     A FilterChain with highpass → acompressor stages.
    #[pyo3(name = "build")]
    fn py_build(&self) -> FilterChain {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!(
            "DeplosiveBuilder(cutoff={}, threshold={}, ratio={})",
            self.cutoff, self.threshold, self.ratio
        )
    }
}

// ========== Tests ==========

#[cfg(test)]
mod tests {
    use super::*;

    // ========== NoiseReductionBuilder tests ==========

    #[test]
    fn test_noise_reduction_broadband_default() {
        let filter = NoiseReductionBuilder::new("broadband").unwrap().build();
        assert_eq!(filter.to_string(), "afftdn=nr=49");
    }

    #[test]
    fn test_noise_reduction_broadband_zero_strength() {
        let filter = NoiseReductionBuilder::new("broadband")
            .unwrap()
            .with_strength(0.0)
            .unwrap()
            .build();
        assert_eq!(filter.to_string(), "afftdn=nr=0");
    }

    #[test]
    fn test_noise_reduction_broadband_full_strength() {
        let filter = NoiseReductionBuilder::new("broadband")
            .unwrap()
            .with_strength(1.0)
            .unwrap()
            .build();
        assert_eq!(filter.to_string(), "afftdn=nr=97");
    }

    #[test]
    fn test_noise_reduction_broadband_mid_strength() {
        let filter = NoiseReductionBuilder::new("broadband")
            .unwrap()
            .with_strength(0.5)
            .unwrap()
            .build();
        assert_eq!(filter.to_string(), "afftdn=nr=49");
    }

    #[test]
    fn test_noise_reduction_adeclick_default() {
        let filter = NoiseReductionBuilder::new("adeclick").unwrap().build();
        assert_eq!(filter.to_string(), "adeclick");
    }

    #[test]
    fn test_noise_reduction_invalid_mode() {
        let result = NoiseReductionBuilder::new("invalid");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("mode must be"));
    }

    #[test]
    fn test_noise_reduction_strength_below_range() {
        let result = NoiseReductionBuilder::new("broadband")
            .unwrap()
            .with_strength(-0.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("strength must be in"));
    }

    #[test]
    fn test_noise_reduction_strength_above_range() {
        let result = NoiseReductionBuilder::new("broadband")
            .unwrap()
            .with_strength(1.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("strength must be in"));
    }

    #[test]
    fn test_noise_reduction_threshold_below_range() {
        let result = NoiseReductionBuilder::new("adeclick")
            .unwrap()
            .with_threshold(-0.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("threshold must be in"));
    }

    #[test]
    fn test_noise_reduction_threshold_above_range() {
        let result = NoiseReductionBuilder::new("adeclick")
            .unwrap()
            .with_threshold(1.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("threshold must be in"));
    }

    #[test]
    fn test_noise_reduction_broadband_emits_afftdn() {
        let filter = NoiseReductionBuilder::new("broadband").unwrap().build();
        assert!(filter.to_string().starts_with("afftdn="));
    }

    #[test]
    fn test_noise_reduction_adeclick_emits_adeclick() {
        let filter = NoiseReductionBuilder::new("adeclick").unwrap().build();
        assert_eq!(filter.to_string(), "adeclick");
    }

    // ========== __repr__ tests ==========

    #[test]
    fn test_noise_reduction_repr_broadband() {
        let builder = NoiseReductionBuilder::new("broadband").unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("NoiseReductionBuilder"));
        assert!(repr.contains("broadband"));
        assert!(repr.contains("strength="));
    }

    #[test]
    fn test_noise_reduction_repr_adeclick() {
        let builder = NoiseReductionBuilder::new("adeclick").unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("NoiseReductionBuilder"));
        assert!(repr.contains("adeclick"));
        assert!(repr.contains("threshold="));
    }

    // ========== PyO3 binding tests ==========

    use pyo3::prelude::*;

    #[test]
    fn test_pyo3_noise_reduction_broadband() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let nr = Bound::new(py, NoiseReductionBuilder::new("broadband").unwrap()).unwrap();
            nr.call_method1("strength", (0.8f64,)).unwrap();
            let filter: String = nr
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filter.starts_with("afftdn=nr="));
            let repr: String = nr.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("NoiseReductionBuilder"));

            // Test py_new error
            assert!(NoiseReductionBuilder::py_new("invalid").is_err());

            // Test strength out-of-range error
            assert!(nr.call_method1("strength", (1.5f64,)).is_err());
        });
    }

    #[test]
    fn test_pyo3_noise_reduction_adeclick() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let nr = Bound::new(py, NoiseReductionBuilder::new("adeclick").unwrap()).unwrap();
            nr.call_method1("threshold", (0.3f64,)).unwrap();
            let filter: String = nr
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(filter, "adeclick");
            let repr: String = nr.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("adeclick"));

            // Test threshold out-of-range error
            assert!(nr.call_method1("threshold", (-0.1f64,)).is_err());
        });
    }

    // ========== DeesserBuilder tests ==========

    #[test]
    fn test_deesser_default_mode() {
        let filter = DeesserBuilder::new(3000.0).unwrap().build();
        assert_eq!(filter.to_string(), "deesser=f=3000:m=wide");
    }

    #[test]
    fn test_deesser_split_mode() {
        let filter = DeesserBuilder::new(5000.0)
            .unwrap()
            .with_mode("split")
            .unwrap()
            .build();
        assert_eq!(filter.to_string(), "deesser=f=5000:m=split");
    }

    #[test]
    fn test_deesser_wide_mode_explicit() {
        let filter = DeesserBuilder::new(8000.0)
            .unwrap()
            .with_mode("wide")
            .unwrap()
            .build();
        assert_eq!(filter.to_string(), "deesser=f=8000:m=wide");
    }

    #[test]
    fn test_deesser_frequency_min_boundary() {
        let filter = DeesserBuilder::new(1000.0).unwrap().build();
        assert!(filter.to_string().starts_with("deesser=f=1000"));
    }

    #[test]
    fn test_deesser_frequency_max_boundary() {
        let filter = DeesserBuilder::new(16000.0).unwrap().build();
        assert!(filter.to_string().starts_with("deesser=f=16000"));
    }

    #[test]
    fn test_deesser_frequency_below_range() {
        let result = DeesserBuilder::new(999.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("frequency must be in"));
    }

    #[test]
    fn test_deesser_frequency_above_range() {
        let result = DeesserBuilder::new(16001.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("frequency must be in"));
    }

    #[test]
    fn test_deesser_invalid_mode() {
        let result = DeesserBuilder::new(6000.0).unwrap().with_mode("narrow");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("mode must be"));
    }

    #[test]
    fn test_deesser_repr() {
        let builder = DeesserBuilder::new(6000.0).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("DeesserBuilder"));
        assert!(repr.contains("6000"));
        assert!(repr.contains("wide"));
    }

    // ========== DeplosiveBuilder tests ==========

    #[test]
    fn test_deplosive_default_build() {
        let chain = DeplosiveBuilder::new().build();
        assert_eq!(
            chain.to_string(),
            "highpass=f=60,acompressor=threshold=0.1:ratio=4:attack=5:release=50"
        );
    }

    #[test]
    fn test_deplosive_custom_cutoff() {
        let chain = DeplosiveBuilder::new().with_cutoff(80.0).unwrap().build();
        assert!(chain.to_string().starts_with("highpass=f=80,"));
    }

    #[test]
    fn test_deplosive_custom_threshold() {
        let chain = DeplosiveBuilder::new().with_threshold(0.5).unwrap().build();
        assert!(chain.to_string().contains("threshold=0.5"));
    }

    #[test]
    fn test_deplosive_custom_ratio() {
        let chain = DeplosiveBuilder::new().with_ratio(8.0).unwrap().build();
        assert!(chain.to_string().contains("ratio=8"));
    }

    #[test]
    fn test_deplosive_contains_highpass_and_acompressor() {
        let chain = DeplosiveBuilder::new().build();
        let s = chain.to_string();
        assert!(s.contains("highpass"));
        assert!(s.contains("acompressor"));
    }

    #[test]
    fn test_deplosive_default_instance() {
        let chain = DeplosiveBuilder::default().build();
        assert_eq!(
            chain.to_string(),
            "highpass=f=60,acompressor=threshold=0.1:ratio=4:attack=5:release=50"
        );
    }

    #[test]
    fn test_deplosive_cutoff_below_range() {
        let result = DeplosiveBuilder::new().with_cutoff(9.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("cutoff must be in"));
    }

    #[test]
    fn test_deplosive_cutoff_above_range() {
        let result = DeplosiveBuilder::new().with_cutoff(201.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("cutoff must be in"));
    }

    #[test]
    fn test_deplosive_threshold_below_range() {
        let result = DeplosiveBuilder::new().with_threshold(-0.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("threshold must be in"));
    }

    #[test]
    fn test_deplosive_threshold_above_range() {
        let result = DeplosiveBuilder::new().with_threshold(1.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("threshold must be in"));
    }

    #[test]
    fn test_deplosive_ratio_below_range() {
        let result = DeplosiveBuilder::new().with_ratio(0.9);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("ratio must be in"));
    }

    #[test]
    fn test_deplosive_ratio_above_range() {
        let result = DeplosiveBuilder::new().with_ratio(20.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("ratio must be in"));
    }

    #[test]
    fn test_deplosive_repr() {
        let builder = DeplosiveBuilder::new();
        let repr = builder.__repr__();
        assert!(repr.contains("DeplosiveBuilder"));
        assert!(repr.contains("cutoff="));
        assert!(repr.contains("threshold="));
        assert!(repr.contains("ratio="));
    }

    // ========== DeesserBuilder / DeplosiveBuilder PyO3 binding tests ==========

    #[test]
    fn test_pyo3_deesser() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let ds = Bound::new(py, DeesserBuilder::new(6000.0).unwrap()).unwrap();
            ds.call_method1("mode", ("split",)).unwrap();
            let filter: String = ds
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filter.starts_with("deesser=f=6000"));
            assert!(filter.contains("m=split"));
            let repr: String = ds.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("DeesserBuilder"));

            // Test py_new error for out-of-range frequency
            assert!(DeesserBuilder::py_new(999.0).is_err());

            // Test mode out-of-range error
            assert!(ds.call_method1("mode", ("narrow",)).is_err());
        });
    }

    #[test]
    fn test_pyo3_deplosive() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let dp = Bound::new(py, DeplosiveBuilder::new()).unwrap();
            dp.call_method1("cutoff", (80.0f64,)).unwrap();
            dp.call_method1("threshold", (0.2f64,)).unwrap();
            dp.call_method1("ratio", (6.0f64,)).unwrap();
            let chain: String = dp
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(chain.contains("highpass=f=80"));
            assert!(chain.contains("acompressor"));
            let repr: String = dp.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("DeplosiveBuilder"));

            // Test cutoff out-of-range error
            assert!(dp.call_method1("cutoff", (9.0f64,)).is_err());

            // Test threshold out-of-range error
            assert!(dp.call_method1("threshold", (1.5f64,)).is_err());

            // Test ratio out-of-range error
            assert!(dp.call_method1("ratio", (0.5f64,)).is_err());
        });
    }
}
