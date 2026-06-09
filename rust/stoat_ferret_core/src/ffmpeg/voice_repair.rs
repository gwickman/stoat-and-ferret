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

use super::filter::Filter;

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
}
