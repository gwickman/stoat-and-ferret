//! Speed control filter builders for FFmpeg video and audio speed adjustment.
//!
//! This module provides [`SpeedControl`] for constructing FFmpeg `setpts` (video)
//! and `atempo` (audio) filters. The atempo builder automatically chains instances
//! for speeds above 2.0x or below 0.5x, keeping each within the [0.5, 2.0] quality
//! range.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::speed::SpeedControl;
//!
//! // 2x speed: video and audio
//! let ctrl = SpeedControl::new(2.0).unwrap();
//! let video = ctrl.setpts_filter();
//! assert_eq!(video.to_string(), "setpts=0.5*PTS");
//!
//! let audio = ctrl.atempo_filters();
//! assert_eq!(audio.len(), 1);
//! assert_eq!(audio[0].to_string(), "atempo=2");
//! ```
//!
//! ```
//! use stoat_ferret_core::ffmpeg::speed::SpeedControl;
//!
//! // 4x speed: atempo auto-chains two 2.0x instances
//! let ctrl = SpeedControl::new(4.0).unwrap();
//! let audio = ctrl.atempo_filters();
//! assert_eq!(audio.len(), 2);
//! assert_eq!(audio[0].to_string(), "atempo=2");
//! assert_eq!(audio[1].to_string(), "atempo=2");
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::filter::Filter;
use crate::sanitize;

/// Computes a chain of atempo values, each within [0.5, 2.0].
///
/// For speeds > 2.0, decomposes using `floor(log2(speed))` stages of 2.0 plus
/// a remainder. For speeds < 0.5, decomposes into stages of 0.5 plus remainder.
/// Returns an empty vec for speed == 1.0 (no-op).
fn atempo_chain(speed: f64) -> Vec<f64> {
    if (speed - 1.0).abs() < f64::EPSILON {
        return Vec::new();
    }

    if (0.5..=2.0).contains(&speed) {
        return vec![speed];
    }

    let mut values = Vec::new();

    if speed > 2.0 {
        let mut remaining = speed;
        while remaining > 2.0 {
            values.push(2.0);
            remaining /= 2.0;
        }
        if (remaining - 1.0).abs() > f64::EPSILON {
            values.push(remaining);
        }
    } else {
        // speed < 0.5
        let mut remaining = speed;
        while remaining < 0.5 {
            values.push(0.5);
            remaining /= 0.5;
        }
        if (remaining - 1.0).abs() > f64::EPSILON {
            values.push(remaining);
        }
    }

    values
}

/// Type-safe speed control builder for FFmpeg video and audio speed adjustment.
///
/// Generates `setpts` filters for video and `atempo` filters for audio.
/// The atempo builder automatically chains instances to keep each within
/// the [0.5, 2.0] quality range.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::speed::SpeedControl;
///
/// let ctrl = SpeedControl::new(2.0).unwrap()
///     .with_drop_audio(true);
/// let video = ctrl.setpts_filter();
/// assert_eq!(video.to_string(), "setpts=0.5*PTS");
/// assert!(ctrl.atempo_filters().is_empty()); // audio dropped
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct SpeedControl {
    speed_factor: f64,
    drop_audio: bool,
}

impl SpeedControl {
    /// Creates a new speed control with the given factor.
    ///
    /// # Arguments
    ///
    /// * `factor` - Speed multiplier in range [0.25, 4.0]
    ///
    /// # Errors
    ///
    /// Returns an error if factor is outside [0.25, 4.0].
    pub fn new(factor: f64) -> Result<Self, String> {
        sanitize::validate_speed(factor).map_err(|e| e.to_string())?;
        Ok(Self {
            speed_factor: factor,
            drop_audio: false,
        })
    }

    /// Sets whether to drop audio instead of speed-adjusting it.
    #[must_use]
    pub fn with_drop_audio(mut self, drop: bool) -> Self {
        self.drop_audio = drop;
        self
    }

    /// Returns the speed factor.
    #[must_use]
    pub fn speed_factor(&self) -> f64 {
        self.speed_factor
    }

    /// Generates the setpts filter for video speed adjustment.
    ///
    /// Formula: `setpts=(1/speed)*PTS`. For 2x speed, produces `setpts=0.5*PTS`.
    #[must_use]
    pub fn setpts_filter(&self) -> Filter {
        let pts_multiplier = 1.0 / self.speed_factor;
        let expr = format_pts_multiplier(pts_multiplier);
        // Use positional syntax: setpts=<expr> (no named parameter)
        Filter::new(format!("setpts={expr}"))
    }

    /// Generates atempo filter(s) for audio speed adjustment.
    ///
    /// Returns an empty vec if `drop_audio` is enabled or speed is 1.0 (no-op).
    /// Automatically chains multiple atempo instances for speeds outside [0.5, 2.0].
    #[must_use]
    pub fn atempo_filters(&self) -> Vec<Filter> {
        if self.drop_audio {
            return Vec::new();
        }

        atempo_chain(self.speed_factor)
            .into_iter()
            .map(|tempo| {
                let val = format_tempo_value(tempo);
                // Use positional syntax: atempo=<value> (no named parameter)
                Filter::new(format!("atempo={val}"))
            })
            .collect()
    }
}

/// Formats a PTS multiplier value, stripping unnecessary trailing zeros.
/// For example, 0.5 -> "0.5*PTS", 1.0 -> "1*PTS", 2.0 -> "2*PTS".
fn format_pts_multiplier(value: f64) -> String {
    if (value - value.round()).abs() < 1e-9 {
        let int_val = value.round() as i64;
        format!("{int_val}*PTS")
    } else {
        // Use a reasonable number of decimal places, trim trailing zeros
        let s = format!("{value:.10}");
        let s = s.trim_end_matches('0');
        let s = s.trim_end_matches('.');
        format!("{s}*PTS")
    }
}

/// Formats an atempo value, stripping unnecessary trailing zeros.
fn format_tempo_value(value: f64) -> String {
    if (value - value.round()).abs() < 1e-9 {
        format!("{}", value.round() as i64)
    } else {
        let s = format!("{value:.10}");
        let s = s.trim_end_matches('0');
        s.trim_end_matches('.').to_string()
    }
}

// ========== PyO3 bindings ==========

#[pymethods]
impl SpeedControl {
    /// Creates a new speed control with the given factor.
    ///
    /// Args:
    ///     factor: Speed multiplier in range [0.25, 4.0].
    ///
    /// Raises:
    ///     ValueError: If factor is outside [0.25, 4.0].
    #[new]
    fn py_new(factor: f64) -> PyResult<Self> {
        Self::new(factor).map_err(PyValueError::new_err)
    }

    /// Sets whether to drop audio instead of speed-adjusting it.
    ///
    /// When enabled, atempo_filters() returns an empty list.
    /// Useful for timelapse-style effects.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "drop_audio")]
    fn py_drop_audio(mut slf: PyRefMut<'_, Self>, drop: bool) -> PyRefMut<'_, Self> {
        slf.drop_audio = drop;
        slf
    }

    /// Returns the speed factor.
    #[getter]
    #[pyo3(name = "speed_factor")]
    fn py_speed_factor(&self) -> f64 {
        self.speed_factor
    }

    /// Returns whether audio will be dropped.
    #[getter]
    #[pyo3(name = "drop_audio_enabled")]
    fn py_drop_audio_enabled(&self) -> bool {
        self.drop_audio
    }

    /// Generates the setpts filter for video speed adjustment.
    ///
    /// Returns a Filter with the setpts expression.
    #[pyo3(name = "setpts_filter")]
    fn py_setpts_filter(&self) -> Filter {
        self.setpts_filter()
    }

    /// Generates atempo filter(s) for audio speed adjustment.
    ///
    /// Returns a list of Filter instances. Multiple filters are chained
    /// for speeds above 2.0x or below 0.5x to maintain audio quality.
    /// Returns an empty list if drop_audio is enabled or speed is 1.0.
    #[pyo3(name = "atempo_filters")]
    fn py_atempo_filters(&self) -> Vec<Filter> {
        self.atempo_filters()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!(
            "SpeedControl(factor={}, drop_audio={})",
            self.speed_factor, self.drop_audio
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========== Construction and validation tests ==========

    #[test]
    fn test_new_valid_speed() {
        let ctrl = SpeedControl::new(2.0).unwrap();
        assert!((ctrl.speed_factor() - 2.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_new_minimum_speed() {
        let ctrl = SpeedControl::new(0.25).unwrap();
        assert!((ctrl.speed_factor() - 0.25).abs() < f64::EPSILON);
    }

    #[test]
    fn test_new_maximum_speed() {
        let ctrl = SpeedControl::new(4.0).unwrap();
        assert!((ctrl.speed_factor() - 4.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_new_below_range() {
        let result = SpeedControl::new(0.1);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("range"));
    }

    #[test]
    fn test_new_above_range() {
        let result = SpeedControl::new(5.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("range"));
    }

    #[test]
    fn test_drop_audio_flag() {
        let ctrl = SpeedControl::new(2.0).unwrap().with_drop_audio(true);
        assert!(ctrl.drop_audio);
    }

    // ========== setpts filter tests ==========

    #[test]
    fn test_setpts_2x() {
        let ctrl = SpeedControl::new(2.0).unwrap();
        let filter = ctrl.setpts_filter();
        assert_eq!(filter.to_string(), "setpts=0.5*PTS");
    }

    #[test]
    fn test_setpts_half_speed() {
        let ctrl = SpeedControl::new(0.5).unwrap();
        let filter = ctrl.setpts_filter();
        assert_eq!(filter.to_string(), "setpts=2*PTS");
    }

    #[test]
    fn test_setpts_1x_identity() {
        let ctrl = SpeedControl::new(1.0).unwrap();
        let filter = ctrl.setpts_filter();
        assert_eq!(filter.to_string(), "setpts=1*PTS");
    }

    #[test]
    fn test_setpts_4x() {
        let ctrl = SpeedControl::new(4.0).unwrap();
        let filter = ctrl.setpts_filter();
        assert_eq!(filter.to_string(), "setpts=0.25*PTS");
    }

    #[test]
    fn test_setpts_quarter_speed() {
        let ctrl = SpeedControl::new(0.25).unwrap();
        let filter = ctrl.setpts_filter();
        assert_eq!(filter.to_string(), "setpts=4*PTS");
    }

    // ========== atempo chain logic tests ==========

    #[test]
    fn test_atempo_chain_1x_noop() {
        let chain = atempo_chain(1.0);
        assert!(chain.is_empty());
    }

    #[test]
    fn test_atempo_chain_within_range() {
        let chain = atempo_chain(1.5);
        assert_eq!(chain.len(), 1);
        assert!((chain[0] - 1.5).abs() < f64::EPSILON);
    }

    #[test]
    fn test_atempo_chain_2x_single() {
        let chain = atempo_chain(2.0);
        assert_eq!(chain.len(), 1);
        assert!((chain[0] - 2.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_atempo_chain_4x_two_stages() {
        let chain = atempo_chain(4.0);
        assert_eq!(chain.len(), 2);
        assert!((chain[0] - 2.0).abs() < f64::EPSILON);
        assert!((chain[1] - 2.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_atempo_chain_3x_two_stages() {
        let chain = atempo_chain(3.0);
        assert_eq!(chain.len(), 2);
        assert!((chain[0] - 2.0).abs() < f64::EPSILON);
        assert!((chain[1] - 1.5).abs() < f64::EPSILON);
    }

    #[test]
    fn test_atempo_chain_0_5x_single() {
        let chain = atempo_chain(0.5);
        assert_eq!(chain.len(), 1);
        assert!((chain[0] - 0.5).abs() < f64::EPSILON);
    }

    #[test]
    fn test_atempo_chain_0_25x_two_stages() {
        let chain = atempo_chain(0.25);
        assert_eq!(chain.len(), 2);
        assert!((chain[0] - 0.5).abs() < f64::EPSILON);
        assert!((chain[1] - 0.5).abs() < f64::EPSILON);
    }

    #[test]
    fn test_atempo_chain_all_values_in_range() {
        // For any valid speed, all atempo values must be in [0.5, 2.0]
        for &speed in &[0.25, 0.3, 0.5, 0.75, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0] {
            let chain = atempo_chain(speed);
            for val in &chain {
                assert!(
                    *val >= 0.5 && *val <= 2.0,
                    "speed={speed}: atempo value {val} out of [0.5, 2.0]"
                );
            }
        }
    }

    #[test]
    fn test_atempo_chain_product_equals_speed() {
        // The product of all chained atempo values should equal the original speed
        for &speed in &[0.25, 0.3, 0.5, 0.75, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0] {
            let chain = atempo_chain(speed);
            let product: f64 = chain.iter().product();
            assert!(
                (product - speed).abs() < 1e-9,
                "speed={speed}: product {product} != {speed}"
            );
        }
    }

    // ========== atempo_filters output tests ==========

    #[test]
    fn test_atempo_filters_2x() {
        let ctrl = SpeedControl::new(2.0).unwrap();
        let filters = ctrl.atempo_filters();
        assert_eq!(filters.len(), 1);
        assert_eq!(filters[0].to_string(), "atempo=2");
    }

    #[test]
    fn test_atempo_filters_4x_chained() {
        let ctrl = SpeedControl::new(4.0).unwrap();
        let filters = ctrl.atempo_filters();
        assert_eq!(filters.len(), 2);
        assert_eq!(filters[0].to_string(), "atempo=2");
        assert_eq!(filters[1].to_string(), "atempo=2");
    }

    #[test]
    fn test_atempo_filters_3x_chained() {
        let ctrl = SpeedControl::new(3.0).unwrap();
        let filters = ctrl.atempo_filters();
        assert_eq!(filters.len(), 2);
        assert_eq!(filters[0].to_string(), "atempo=2");
        assert_eq!(filters[1].to_string(), "atempo=1.5");
    }

    #[test]
    fn test_atempo_filters_0_25x_chained() {
        let ctrl = SpeedControl::new(0.25).unwrap();
        let filters = ctrl.atempo_filters();
        assert_eq!(filters.len(), 2);
        assert_eq!(filters[0].to_string(), "atempo=0.5");
        assert_eq!(filters[1].to_string(), "atempo=0.5");
    }

    #[test]
    fn test_atempo_filters_1x_noop() {
        let ctrl = SpeedControl::new(1.0).unwrap();
        let filters = ctrl.atempo_filters();
        assert!(filters.is_empty());
    }

    #[test]
    fn test_atempo_filters_drop_audio() {
        let ctrl = SpeedControl::new(2.0).unwrap().with_drop_audio(true);
        let filters = ctrl.atempo_filters();
        assert!(filters.is_empty());
    }

    // ========== Filter string format tests ==========

    #[test]
    fn test_format_pts_multiplier_integer() {
        assert_eq!(format_pts_multiplier(1.0), "1*PTS");
        assert_eq!(format_pts_multiplier(2.0), "2*PTS");
        assert_eq!(format_pts_multiplier(4.0), "4*PTS");
    }

    #[test]
    fn test_format_pts_multiplier_decimal() {
        assert_eq!(format_pts_multiplier(0.5), "0.5*PTS");
        assert_eq!(format_pts_multiplier(0.25), "0.25*PTS");
    }

    #[test]
    fn test_format_tempo_value_integer() {
        assert_eq!(format_tempo_value(2.0), "2");
        assert_eq!(format_tempo_value(1.0), "1");
    }

    #[test]
    fn test_format_tempo_value_decimal() {
        assert_eq!(format_tempo_value(1.5), "1.5");
        assert_eq!(format_tempo_value(0.5), "0.5");
    }

    // ========== Integration with filter chain ==========

    #[test]
    fn test_setpts_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let ctrl = SpeedControl::new(2.0).unwrap();
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .filter(ctrl.setpts_filter())
                .output("fast_v"),
        );
        let s = graph.to_string();
        assert!(s.contains("[0:v]"));
        assert!(s.contains("setpts="));
        assert!(s.contains("[fast_v]"));
    }

    #[test]
    fn test_atempo_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let ctrl = SpeedControl::new(3.0).unwrap();
        let filters = ctrl.atempo_filters();
        let mut chain = FilterChain::new().input("0:a");
        for f in filters {
            chain = chain.filter(f);
        }
        chain = chain.output("fast_a");

        let graph = FilterGraph::new().chain(chain);
        let s = graph.to_string();
        assert!(s.contains("[0:a]"));
        assert!(s.contains("atempo=2"));
        assert!(s.contains("atempo=1.5"));
        assert!(s.contains("[fast_a]"));
    }

    // ========== Proptest ==========

    use proptest::prelude::*;

    proptest! {
        /// Property: all valid speeds produce valid setpts filter strings.
        #[test]
        fn setpts_always_valid(speed in 0.25f64..=4.0) {
            let ctrl = SpeedControl::new(speed).unwrap();
            let filter = ctrl.setpts_filter();
            let s = filter.to_string();
            prop_assert!(s.starts_with("setpts="), "Got: {}", s);
            prop_assert!(s.contains("*PTS"), "Missing PTS: {}", s);
        }

        /// Property: all atempo chain values are within [0.5, 2.0].
        #[test]
        fn atempo_chain_values_in_range(speed in 0.25f64..=4.0) {
            let chain = atempo_chain(speed);
            for val in &chain {
                prop_assert!(
                    *val >= 0.5 - f64::EPSILON && *val <= 2.0 + f64::EPSILON,
                    "speed={}: value {} out of range", speed, val
                );
            }
        }

        /// Property: atempo chain product approximates original speed.
        #[test]
        fn atempo_chain_product_correct(speed in 0.25f64..=4.0) {
            if (speed - 1.0).abs() < f64::EPSILON {
                let chain = atempo_chain(speed);
                prop_assert!(chain.is_empty());
            } else {
                let chain = atempo_chain(speed);
                let product: f64 = chain.iter().product();
                prop_assert!(
                    (product - speed).abs() < 1e-6,
                    "speed={}: product {} != {}", speed, product, speed
                );
            }
        }

        /// Property: out-of-range speeds are rejected.
        #[test]
        fn invalid_speed_rejected(speed in -100.0f64..0.249) {
            let result = SpeedControl::new(speed);
            prop_assert!(result.is_err());
        }
    }
}
