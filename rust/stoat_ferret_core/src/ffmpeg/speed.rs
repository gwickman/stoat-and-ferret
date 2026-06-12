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

/// Formats a setpts expression for use after trim, resetting PTS to segment start.
/// Uses (1/speed)*(PTS-STARTPTS) form so each trimmed segment starts at t=0.
fn format_setpts_expr(speed: f64) -> String {
    let pts_mult = 1.0 / speed;
    if (pts_mult - pts_mult.round()).abs() < 1e-9 {
        let int_val = pts_mult.round() as i64;
        format!("setpts={int_val}*(PTS-STARTPTS)")
    } else {
        let s = format!("{pts_mult:.10}");
        let s = s.trim_end_matches('0');
        let s = s.trim_end_matches('.');
        format!("setpts={s}*(PTS-STARTPTS)")
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

// ========== VariableSpeedBuilder ==========

/// A speed segment defining a frame range and its speed factor.
///
/// Used with [`VariableSpeedBuilder`] to specify per-segment speed curves.
/// Each segment covers frames `[start_frame, end_frame)` at a constant `speed_factor`.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct SpeedSegment {
    #[pyo3(get)]
    pub start_frame: u64,
    #[pyo3(get)]
    pub end_frame: u64,
    #[pyo3(get)]
    pub speed_factor: f64,
}

#[pymethods]
impl SpeedSegment {
    /// Creates a new speed segment.
    ///
    /// Args:
    ///     start_frame: First frame of the segment (inclusive).
    ///     end_frame: Last frame of the segment (exclusive).
    ///     speed_factor: Speed multiplier in range (0, 100].
    ///
    /// Raises:
    ///     ValueError: If speed_factor is not in (0, 100].
    #[new]
    fn py_new(start_frame: u64, end_frame: u64, speed_factor: f64) -> PyResult<Self> {
        if speed_factor <= 0.0 || speed_factor > 100.0 {
            return Err(PyValueError::new_err(format!(
                "speed_factor must be in range (0, 100], got {speed_factor}"
            )));
        }
        Ok(Self {
            start_frame,
            end_frame,
            speed_factor,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "SpeedSegment(start_frame={}, end_frame={}, speed_factor={})",
            self.start_frame, self.end_frame, self.speed_factor
        )
    }
}

/// Variable-speed builder using a segmented concat approach.
///
/// Divides a clip into constant-speed sub-ranges and concatenates them, producing
/// a segmented speed curve. Each segment uses `trim+setpts` for video and
/// `atrim+atempo` (with automatic chaining) for audio.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::speed::{SpeedSegment, VariableSpeedBuilder};
///
/// let segments = vec![
///     SpeedSegment { start_frame: 0, end_frame: 30, speed_factor: 2.0 },
///     SpeedSegment { start_frame: 30, end_frame: 60, speed_factor: 0.5 },
/// ];
/// let builder = VariableSpeedBuilder::new(segments).unwrap();
/// let graph = builder.build_filter_graph();
/// assert!(graph.contains("trim=start_frame=0:end_frame=30"));
/// assert!(graph.contains("concat=n=2"));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct VariableSpeedBuilder {
    segments: Vec<SpeedSegment>,
}

impl VariableSpeedBuilder {
    /// Creates a new variable-speed builder with the given segments.
    ///
    /// # Errors
    ///
    /// Returns an error if the segments list is empty or any segment has an
    /// invalid speed_factor (must be in (0, 100]).
    pub fn new(segments: Vec<SpeedSegment>) -> Result<Self, String> {
        if segments.is_empty() {
            return Err("segments list must not be empty".to_string());
        }
        for seg in &segments {
            if seg.speed_factor <= 0.0 || seg.speed_factor > 100.0 {
                return Err(format!(
                    "speed_factor must be in range (0, 100], got {}",
                    seg.speed_factor
                ));
            }
        }
        Ok(Self { segments })
    }

    /// Builds the complete FFmpeg filter graph string for variable-speed playback.
    ///
    /// Produces video trim+setpts chains and audio atrim+asetpts+atempo chains for each
    /// segment, then concatenates all video segments and all audio segments.
    #[must_use]
    pub fn build_filter_graph(&self) -> String {
        let n = self.segments.len();
        let mut parts: Vec<String> = Vec::with_capacity(n * 2 + 2);

        // Video chain for each segment
        for (i, seg) in self.segments.iter().enumerate() {
            let setpts = format_setpts_expr(seg.speed_factor);
            parts.push(format!(
                "[0:v]trim=start_frame={}:end_frame={},{setpts}[vseg{i}]",
                seg.start_frame, seg.end_frame,
            ));
        }

        // Audio chain for each segment: atrim + asetpts + atempo chain
        for (i, seg) in self.segments.iter().enumerate() {
            let chain = atempo_chain(seg.speed_factor);
            let atempo_str: String = chain
                .iter()
                .map(|v| format!(",atempo={}", format_tempo_value(*v)))
                .collect();
            parts.push(format!(
                "[0:a]atrim=start_frame={}:end_frame={},asetpts=NB_CONSUMED_SAMPLES/SR/TB{atempo_str}[aseg{i}]",
                seg.start_frame, seg.end_frame,
            ));
        }

        // Video concat
        let v_inputs: String = (0..n).map(|i| format!("[vseg{i}]")).collect();
        parts.push(format!("{v_inputs}concat=n={n}:v=1:a=0[vout]"));

        // Audio concat
        let a_inputs: String = (0..n).map(|i| format!("[aseg{i}]")).collect();
        parts.push(format!("{a_inputs}concat=n={n}:v=0:a=1[aout]"));

        parts.join(";")
    }
}

// ========== PyO3 bindings for VariableSpeedBuilder ==========

#[pymethods]
impl VariableSpeedBuilder {
    /// Creates a new variable-speed builder with the given segments.
    ///
    /// Args:
    ///     segments: List of SpeedSegment objects defining the speed curve.
    ///
    /// Raises:
    ///     ValueError: If segments is empty or any segment has invalid speed_factor.
    #[new]
    fn py_new(segments: Vec<SpeedSegment>) -> PyResult<Self> {
        Self::new(segments).map_err(PyValueError::new_err)
    }

    /// Builds the complete FFmpeg filter graph string for variable-speed playback.
    ///
    /// Returns a semicolon-separated filter graph with video trim+setpts chains,
    /// audio atrim+asetpts+atempo chains, and concat filters.
    #[pyo3(name = "build_filter_graph")]
    fn py_build_filter_graph(&self) -> String {
        self.build_filter_graph()
    }

    fn __repr__(&self) -> String {
        format!("VariableSpeedBuilder(segments={})", self.segments.len())
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

    // ========== VariableSpeedBuilder tests ==========

    fn seg(start: u64, end: u64, speed: f64) -> SpeedSegment {
        SpeedSegment {
            start_frame: start,
            end_frame: end,
            speed_factor: speed,
        }
    }

    #[test]
    fn test_variable_speed_2_segment_filter_graph() {
        let builder = VariableSpeedBuilder::new(vec![seg(0, 30, 2.0), seg(30, 60, 0.5)]).unwrap();
        let graph = builder.build_filter_graph();
        assert!(
            graph.contains("[0:v]trim=start_frame=0:end_frame=30,setpts=0.5*(PTS-STARTPTS)[vseg0]"),
            "Got: {graph}"
        );
        assert!(
            graph.contains("[0:v]trim=start_frame=30:end_frame=60,setpts=2*(PTS-STARTPTS)[vseg1]"),
            "Got: {graph}"
        );
        assert!(
            graph.contains("[0:a]atrim=start_frame=0:end_frame=30,asetpts=NB_CONSUMED_SAMPLES/SR/TB,atempo=2[aseg0]"),
            "Got: {graph}"
        );
        assert!(
            graph.contains("[0:a]atrim=start_frame=30:end_frame=60,asetpts=NB_CONSUMED_SAMPLES/SR/TB,atempo=0.5[aseg1]"),
            "Got: {graph}"
        );
        assert!(graph.contains("[vseg0][vseg1]concat=n=2:v=1:a=0[vout]"), "Got: {graph}");
        assert!(graph.contains("[aseg0][aseg1]concat=n=2:v=0:a=1[aout]"), "Got: {graph}");
    }

    #[test]
    fn test_variable_speed_3_segment_filter_graph() {
        let builder =
            VariableSpeedBuilder::new(vec![seg(0, 30, 2.0), seg(30, 60, 1.0), seg(60, 90, 0.5)])
                .unwrap();
        let graph = builder.build_filter_graph();
        assert!(graph.contains("trim=start_frame=0:end_frame=30"), "Got: {graph}");
        assert!(graph.contains("trim=start_frame=30:end_frame=60"), "Got: {graph}");
        assert!(graph.contains("trim=start_frame=60:end_frame=90"), "Got: {graph}");
        assert!(
            graph.contains("setpts=1*(PTS-STARTPTS)"),
            "1x speed should give setpts=1*(PTS-STARTPTS), got: {graph}"
        );
        assert!(graph.contains("concat=n=3:v=1:a=0[vout]"), "Got: {graph}");
        assert!(graph.contains("concat=n=3:v=0:a=1[aout]"), "Got: {graph}");
        // 1x speed → atempo chain is empty, no ,atempo= for middle segment
        let mid_audio = "[0:a]atrim=start_frame=30:end_frame=60,asetpts=NB_CONSUMED_SAMPLES/SR/TB[aseg1]";
        assert!(graph.contains(mid_audio), "Got: {graph}");
    }

    #[test]
    fn test_variable_speed_empty_segments_rejected() {
        let result = VariableSpeedBuilder::new(vec![]);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("empty"));
    }

    #[test]
    fn test_variable_speed_invalid_speed_factor_rejected() {
        let result = VariableSpeedBuilder::new(vec![seg(0, 30, 0.0)]);
        assert!(result.is_err());
        let result2 = VariableSpeedBuilder::new(vec![seg(0, 30, 101.0)]);
        assert!(result2.is_err());
    }

    #[test]
    fn test_format_setpts_expr_2x() {
        assert_eq!(format_setpts_expr(2.0), "setpts=0.5*(PTS-STARTPTS)");
    }

    #[test]
    fn test_format_setpts_expr_half() {
        assert_eq!(format_setpts_expr(0.5), "setpts=2*(PTS-STARTPTS)");
    }

    #[test]
    fn test_format_setpts_expr_1x() {
        assert_eq!(format_setpts_expr(1.0), "setpts=1*(PTS-STARTPTS)");
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

        /// Property: out-of-range speeds below minimum are rejected.
        #[test]
        fn invalid_speed_rejected(speed in -100.0f64..0.249) {
            let result = SpeedControl::new(speed);
            prop_assert!(result.is_err());
        }

        /// Property: out-of-range speeds above maximum are rejected.
        #[test]
        fn invalid_speed_above_max_rejected(speed in 4.001f64..=100.0) {
            let result = SpeedControl::new(speed);
            prop_assert!(result.is_err());
        }

        /// Property: full range 0.01..=100.0 is either accepted (valid) or rejected (invalid) without panics.
        #[test]
        fn speed_full_range_no_panic(speed in 0.01f64..=100.0) {
            let result = SpeedControl::new(speed);
            if (0.25..=4.0).contains(&speed) {
                prop_assert!(result.is_ok(), "Valid speed {} rejected", speed);
                let ctrl = result.unwrap();
                let filter = ctrl.setpts_filter();
                let s = filter.to_string();
                prop_assert!(s.starts_with("setpts="), "Got: {}", s);
                prop_assert!(s.contains("*PTS"), "Missing PTS: {}", s);
            } else {
                prop_assert!(result.is_err(), "Invalid speed {} accepted", speed);
            }
        }
    }

    // ========== Additional coverage tests ==========

    #[test]
    fn test_repr() {
        let ctrl = SpeedControl::new(2.0).unwrap();
        let repr = ctrl.__repr__();
        assert!(repr.contains("SpeedControl"));
        assert!(repr.contains("2"));
        assert!(repr.contains("false"));
    }

    #[test]
    fn test_repr_with_drop_audio() {
        let ctrl = SpeedControl::new(1.5).unwrap().with_drop_audio(true);
        let repr = ctrl.__repr__();
        assert!(repr.contains("true"));
    }

    #[test]
    fn test_format_tempo_value_edge_cases() {
        assert_eq!(format_tempo_value(0.25), "0.25");
        assert_eq!(format_tempo_value(0.333), "0.333");
    }

    #[test]
    fn test_atempo_chain_0_3x() {
        let chain = atempo_chain(0.3);
        assert!(!chain.is_empty());
        let product: f64 = chain.iter().product();
        assert!((product - 0.3).abs() < 1e-6);
        for val in &chain {
            assert!(*val >= 0.5 - f64::EPSILON && *val <= 2.0 + f64::EPSILON);
        }
    }

    // ========== PyO3 binding tests ==========

    use pyo3::prelude::*;

    #[test]
    fn test_pyo3_speed_control() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let sc = Bound::new(py, SpeedControl::new(2.0).unwrap()).unwrap();

            // Test drop_audio method
            sc.call_method1("drop_audio", (false,)).unwrap();

            // Test getters
            let factor: f64 = sc.getattr("speed_factor").unwrap().extract().unwrap();
            assert!((factor - 2.0).abs() < f64::EPSILON);
            let drop: bool = sc.getattr("drop_audio_enabled").unwrap().extract().unwrap();
            assert!(!drop);

            // Test setpts_filter
            let filter: String = sc
                .call_method0("setpts_filter")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filter.contains("setpts="));

            // Test atempo_filters
            let filters: Vec<PyObject> = sc
                .call_method0("atempo_filters")
                .unwrap()
                .extract()
                .unwrap();
            assert!(!filters.is_empty());

            // Test repr
            let repr: String = sc.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("SpeedControl"));

            // Test py_new error
            assert!(SpeedControl::py_new(0.1).is_err());
        });
    }

    #[test]
    fn test_pyo3_speed_drop_audio() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let sc = Bound::new(py, SpeedControl::new(2.0).unwrap()).unwrap();
            sc.call_method1("drop_audio", (true,)).unwrap();
            let filters: Vec<PyObject> = sc
                .call_method0("atempo_filters")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filters.is_empty());
        });
    }
}
