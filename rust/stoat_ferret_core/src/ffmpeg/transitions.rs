//! Video/audio transition filter builders for FFmpeg.
//!
//! This module provides type-safe builders for constructing transition filters:
//!
//! - [`FadeBuilder`] - Video fade in/out with configurable duration and color
//! - [`XfadeBuilder`] - Video crossfade with selectable transition effects
//! - [`TransitionType`] - All 59 FFmpeg xfade transition variants
//! - [`AcrossfadeBuilder`] - Audio crossfade between two inputs
//!
//! All builders follow the fluent pattern: construct, configure, then `.build()`.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::transitions::FadeBuilder;
//!
//! let filter = FadeBuilder::new("in", 3.0).unwrap().build();
//! assert_eq!(filter.to_string(), "fade=t=in:d=3");
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::audio::FadeCurve;
use super::filter::Filter;

// ========== Helper ==========

/// Formats a numeric value, stripping unnecessary trailing zeros.
fn format_value(value: f64) -> String {
    if (value - value.round()).abs() < 1e-9 {
        format!("{}", value.round() as i64)
    } else {
        let s = format!("{value:.10}");
        let s = s.trim_end_matches('0');
        s.trim_end_matches('.').to_string()
    }
}

// ========== TransitionType Enum ==========

/// All 59 FFmpeg xfade transition variants.
///
/// Each variant maps to an FFmpeg xfade `transition` parameter value.
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TransitionType {
    // Basic fades
    Fade,
    Fadeblack,
    Fadewhite,
    Fadegrays,
    Fadefast,
    Fadeslow,
    // Wipes
    Wipeleft,
    Wiperight,
    Wipeup,
    Wipedown,
    Wipetl,
    Wipetr,
    Wipebl,
    Wipebr,
    // Slides
    Slideleft,
    Slideright,
    Slideup,
    Slidedown,
    // Smooth
    Smoothleft,
    Smoothright,
    Smoothup,
    Smoothdown,
    // Shapes
    Circlecrop,
    Rectcrop,
    Circleopen,
    Circleclose,
    Radial,
    // Bars
    Vertopen,
    Vertclose,
    Horzopen,
    Horzclose,
    // Effects
    Dissolve,
    Pixelize,
    Distance,
    Hblur,
    // Diagonal
    Diagtl,
    Diagtr,
    Diagbl,
    Diagbr,
    // Slices
    Hlslice,
    Hrslice,
    Vuslice,
    Vdslice,
    // Squeeze
    Squeezeh,
    Squeezev,
    // Zoom
    Zoomin,
    // Wind
    Hlwind,
    Hrwind,
    Vuwind,
    Vdwind,
    // Cover
    Coverleft,
    Coverright,
    Coverup,
    Coverdown,
    // Reveal
    Revealleft,
    Revealright,
    Revealup,
    Revealdown,
    // Custom
    Custom,
}

/// All valid transition type strings for error messages.
const VALID_TRANSITIONS: &str = "fade, fadeblack, fadewhite, fadegrays, fadefast, fadeslow, \
    wipeleft, wiperight, wipeup, wipedown, wipetl, wipetr, wipebl, wipebr, \
    slideleft, slideright, slideup, slidedown, \
    smoothleft, smoothright, smoothup, smoothdown, \
    circlecrop, rectcrop, circleopen, circleclose, radial, \
    vertopen, vertclose, horzopen, horzclose, \
    dissolve, pixelize, distance, hblur, \
    diagtl, diagtr, diagbl, diagbr, \
    hlslice, hrslice, vuslice, vdslice, \
    squeezeh, squeezev, zoomin, \
    hlwind, hrwind, vuwind, vdwind, \
    coverleft, coverright, coverup, coverdown, \
    revealleft, revealright, revealup, revealdown, custom";

impl TransitionType {
    /// Returns the FFmpeg string representation of this transition type.
    pub fn as_str(&self) -> &'static str {
        match self {
            TransitionType::Fade => "fade",
            TransitionType::Fadeblack => "fadeblack",
            TransitionType::Fadewhite => "fadewhite",
            TransitionType::Fadegrays => "fadegrays",
            TransitionType::Fadefast => "fadefast",
            TransitionType::Fadeslow => "fadeslow",
            TransitionType::Wipeleft => "wipeleft",
            TransitionType::Wiperight => "wiperight",
            TransitionType::Wipeup => "wipeup",
            TransitionType::Wipedown => "wipedown",
            TransitionType::Wipetl => "wipetl",
            TransitionType::Wipetr => "wipetr",
            TransitionType::Wipebl => "wipebl",
            TransitionType::Wipebr => "wipebr",
            TransitionType::Slideleft => "slideleft",
            TransitionType::Slideright => "slideright",
            TransitionType::Slideup => "slideup",
            TransitionType::Slidedown => "slidedown",
            TransitionType::Smoothleft => "smoothleft",
            TransitionType::Smoothright => "smoothright",
            TransitionType::Smoothup => "smoothup",
            TransitionType::Smoothdown => "smoothdown",
            TransitionType::Circlecrop => "circlecrop",
            TransitionType::Rectcrop => "rectcrop",
            TransitionType::Circleopen => "circleopen",
            TransitionType::Circleclose => "circleclose",
            TransitionType::Radial => "radial",
            TransitionType::Vertopen => "vertopen",
            TransitionType::Vertclose => "vertclose",
            TransitionType::Horzopen => "horzopen",
            TransitionType::Horzclose => "horzclose",
            TransitionType::Dissolve => "dissolve",
            TransitionType::Pixelize => "pixelize",
            TransitionType::Distance => "distance",
            TransitionType::Hblur => "hblur",
            TransitionType::Diagtl => "diagtl",
            TransitionType::Diagtr => "diagtr",
            TransitionType::Diagbl => "diagbl",
            TransitionType::Diagbr => "diagbr",
            TransitionType::Hlslice => "hlslice",
            TransitionType::Hrslice => "hrslice",
            TransitionType::Vuslice => "vuslice",
            TransitionType::Vdslice => "vdslice",
            TransitionType::Squeezeh => "squeezeh",
            TransitionType::Squeezev => "squeezev",
            TransitionType::Zoomin => "zoomin",
            TransitionType::Hlwind => "hlwind",
            TransitionType::Hrwind => "hrwind",
            TransitionType::Vuwind => "vuwind",
            TransitionType::Vdwind => "vdwind",
            TransitionType::Coverleft => "coverleft",
            TransitionType::Coverright => "coverright",
            TransitionType::Coverup => "coverup",
            TransitionType::Coverdown => "coverdown",
            TransitionType::Revealleft => "revealleft",
            TransitionType::Revealright => "revealright",
            TransitionType::Revealup => "revealup",
            TransitionType::Revealdown => "revealdown",
            TransitionType::Custom => "custom",
        }
    }

    /// Parses a transition type name string into a TransitionType.
    ///
    /// # Errors
    ///
    /// Returns an error message if the name is not recognized.
    pub fn parse(s: &str) -> Result<Self, String> {
        match s {
            "fade" => Ok(TransitionType::Fade),
            "fadeblack" => Ok(TransitionType::Fadeblack),
            "fadewhite" => Ok(TransitionType::Fadewhite),
            "fadegrays" => Ok(TransitionType::Fadegrays),
            "fadefast" => Ok(TransitionType::Fadefast),
            "fadeslow" => Ok(TransitionType::Fadeslow),
            "wipeleft" => Ok(TransitionType::Wipeleft),
            "wiperight" => Ok(TransitionType::Wiperight),
            "wipeup" => Ok(TransitionType::Wipeup),
            "wipedown" => Ok(TransitionType::Wipedown),
            "wipetl" => Ok(TransitionType::Wipetl),
            "wipetr" => Ok(TransitionType::Wipetr),
            "wipebl" => Ok(TransitionType::Wipebl),
            "wipebr" => Ok(TransitionType::Wipebr),
            "slideleft" => Ok(TransitionType::Slideleft),
            "slideright" => Ok(TransitionType::Slideright),
            "slideup" => Ok(TransitionType::Slideup),
            "slidedown" => Ok(TransitionType::Slidedown),
            "smoothleft" => Ok(TransitionType::Smoothleft),
            "smoothright" => Ok(TransitionType::Smoothright),
            "smoothup" => Ok(TransitionType::Smoothup),
            "smoothdown" => Ok(TransitionType::Smoothdown),
            "circlecrop" => Ok(TransitionType::Circlecrop),
            "rectcrop" => Ok(TransitionType::Rectcrop),
            "circleopen" => Ok(TransitionType::Circleopen),
            "circleclose" => Ok(TransitionType::Circleclose),
            "radial" => Ok(TransitionType::Radial),
            "vertopen" => Ok(TransitionType::Vertopen),
            "vertclose" => Ok(TransitionType::Vertclose),
            "horzopen" => Ok(TransitionType::Horzopen),
            "horzclose" => Ok(TransitionType::Horzclose),
            "dissolve" => Ok(TransitionType::Dissolve),
            "pixelize" => Ok(TransitionType::Pixelize),
            "distance" => Ok(TransitionType::Distance),
            "hblur" => Ok(TransitionType::Hblur),
            "diagtl" => Ok(TransitionType::Diagtl),
            "diagtr" => Ok(TransitionType::Diagtr),
            "diagbl" => Ok(TransitionType::Diagbl),
            "diagbr" => Ok(TransitionType::Diagbr),
            "hlslice" => Ok(TransitionType::Hlslice),
            "hrslice" => Ok(TransitionType::Hrslice),
            "vuslice" => Ok(TransitionType::Vuslice),
            "vdslice" => Ok(TransitionType::Vdslice),
            "squeezeh" => Ok(TransitionType::Squeezeh),
            "squeezev" => Ok(TransitionType::Squeezev),
            "zoomin" => Ok(TransitionType::Zoomin),
            "hlwind" => Ok(TransitionType::Hlwind),
            "hrwind" => Ok(TransitionType::Hrwind),
            "vuwind" => Ok(TransitionType::Vuwind),
            "vdwind" => Ok(TransitionType::Vdwind),
            "coverleft" => Ok(TransitionType::Coverleft),
            "coverright" => Ok(TransitionType::Coverright),
            "coverup" => Ok(TransitionType::Coverup),
            "coverdown" => Ok(TransitionType::Coverdown),
            "revealleft" => Ok(TransitionType::Revealleft),
            "revealright" => Ok(TransitionType::Revealright),
            "revealup" => Ok(TransitionType::Revealup),
            "revealdown" => Ok(TransitionType::Revealdown),
            "custom" => Ok(TransitionType::Custom),
            _ => Err(format!(
                "invalid transition type '{s}'. Valid types: {VALID_TRANSITIONS}"
            )),
        }
    }
}

// ========== TransitionType PyO3 bindings ==========

#[pymethods]
impl TransitionType {
    /// Creates a TransitionType from a string name.
    ///
    /// Args:
    ///     name: Transition type name (e.g., "wipeleft", "dissolve").
    ///
    /// Raises:
    ///     ValueError: If the name is not a valid transition type.
    #[staticmethod]
    #[pyo3(name = "from_str")]
    fn py_from_str(name: &str) -> PyResult<Self> {
        Self::parse(name).map_err(PyValueError::new_err)
    }

    /// Returns the FFmpeg string representation of this transition type.
    #[pyo3(name = "as_str")]
    fn py_as_str(&self) -> &'static str {
        self.as_str()
    }

    /// Returns a string representation of the transition type.
    fn __repr__(&self) -> String {
        format!("TransitionType.{:?}", self)
    }

    /// Returns the FFmpeg string for this transition type.
    fn __str__(&self) -> &'static str {
        self.as_str()
    }
}

// ========== FadeBuilder ==========

/// Type-safe builder for FFmpeg `fade` video filter.
///
/// Supports fade in/out with configurable duration, color, alpha mode,
/// start time, and nb_frames alternative.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::transitions::FadeBuilder;
///
/// let filter = FadeBuilder::new("in", 3.0).unwrap().build();
/// assert_eq!(filter.to_string(), "fade=t=in:d=3");
///
/// let filter = FadeBuilder::new("out", 2.0).unwrap()
///     .with_color("white")
///     .with_start_time(10.0)
///     .build();
/// assert_eq!(filter.to_string(), "fade=t=out:d=2:st=10:c=white");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct FadeBuilder {
    /// Fade type: "in" or "out".
    fade_type: String,
    /// Fade duration in seconds.
    duration: f64,
    /// Start time in seconds (optional).
    start_time: Option<f64>,
    /// Color for the fade (default: "black").
    color: Option<String>,
    /// Whether to fade the alpha channel.
    alpha: bool,
    /// Number of frames for the fade (alternative to duration).
    nb_frames: Option<u64>,
}

impl FadeBuilder {
    /// Creates a new FadeBuilder.
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
            color: None,
            alpha: false,
            nb_frames: None,
        })
    }

    /// Sets the start time for the fade.
    #[must_use]
    pub fn with_start_time(mut self, start_time: f64) -> Self {
        self.start_time = Some(start_time);
        self
    }

    /// Sets the fade color.
    #[must_use]
    pub fn with_color(mut self, color: &str) -> Self {
        self.color = Some(color.to_string());
        self
    }

    /// Enables alpha channel fading.
    #[must_use]
    pub fn with_alpha(mut self, alpha: bool) -> Self {
        self.alpha = alpha;
        self
    }

    /// Sets the number of frames (alternative to duration).
    #[must_use]
    pub fn with_nb_frames(mut self, nb_frames: u64) -> Self {
        self.nb_frames = Some(nb_frames);
        self
    }

    /// Builds the fade Filter.
    #[must_use]
    pub fn build(&self) -> Filter {
        let mut filter = Filter::new("fade").param("t", &self.fade_type);
        if let Some(nb) = self.nb_frames {
            filter = filter.param("nb_frames", nb);
        } else {
            filter = filter.param("d", format_value(self.duration));
        }
        if let Some(st) = self.start_time {
            filter = filter.param("st", format_value(st));
        }
        if let Some(ref c) = self.color {
            filter = filter.param("c", c);
        }
        if self.alpha {
            filter = filter.param("alpha", 1);
        }
        filter
    }
}

// ========== FadeBuilder PyO3 bindings ==========

#[pymethods]
impl FadeBuilder {
    /// Creates a new FadeBuilder.
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

    /// Sets the fade color (named colors or hex #RRGGBB).
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "color")]
    fn py_color<'a>(mut slf: PyRefMut<'a, Self>, color: &str) -> PyRefMut<'a, Self> {
        slf.color = Some(color.to_string());
        slf
    }

    /// Enables or disables alpha channel fading.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "alpha")]
    fn py_alpha(mut slf: PyRefMut<'_, Self>, alpha: bool) -> PyRefMut<'_, Self> {
        slf.alpha = alpha;
        slf
    }

    /// Sets the number of frames for the fade (alternative to duration).
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "nb_frames")]
    fn py_nb_frames(mut slf: PyRefMut<'_, Self>, nb_frames: u64) -> PyRefMut<'_, Self> {
        slf.nb_frames = Some(nb_frames);
        slf
    }

    /// Builds the fade Filter.
    ///
    /// Returns:
    ///     A Filter with the fade syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!(
            "FadeBuilder(type={}, duration={})",
            self.fade_type, self.duration
        )
    }
}

// ========== XfadeBuilder ==========

/// Type-safe builder for FFmpeg `xfade` video crossfade filter.
///
/// Creates a two-input crossfade with a selectable transition effect.
/// Duration is validated in range 0.0-60.0 seconds.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::transitions::{XfadeBuilder, TransitionType};
///
/// let filter = XfadeBuilder::new(TransitionType::Wipeleft, 2.0, 5.0).unwrap().build();
/// assert_eq!(filter.to_string(), "xfade=transition=wipeleft:duration=2:offset=5");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct XfadeBuilder {
    /// Transition type.
    transition: TransitionType,
    /// Transition duration in seconds (0.0-60.0).
    duration: f64,
    /// Offset in seconds (when the transition starts relative to first input).
    offset: f64,
}

impl XfadeBuilder {
    /// Creates a new XfadeBuilder.
    ///
    /// # Arguments
    ///
    /// * `transition` - The transition effect to use
    /// * `duration` - Transition duration in seconds (0.0-60.0)
    /// * `offset` - When the transition starts relative to the first input
    ///
    /// # Errors
    ///
    /// Returns an error if duration is outside [0.0, 60.0].
    pub fn new(transition: TransitionType, duration: f64, offset: f64) -> Result<Self, String> {
        if !(0.0..=60.0).contains(&duration) {
            return Err(format!(
                "xfade duration must be 0.0-60.0 seconds, got {duration}"
            ));
        }
        Ok(Self {
            transition,
            duration,
            offset,
        })
    }

    /// Builds the xfade Filter.
    #[must_use]
    pub fn build(&self) -> Filter {
        Filter::new("xfade")
            .param("transition", self.transition.as_str())
            .param("duration", format_value(self.duration))
            .param("offset", format_value(self.offset))
    }
}

// ========== XfadeBuilder PyO3 bindings ==========

#[pymethods]
impl XfadeBuilder {
    /// Creates a new XfadeBuilder.
    ///
    /// Args:
    ///     transition: The transition effect to use.
    ///     duration: Transition duration in seconds (0.0-60.0).
    ///     offset: When the transition starts relative to the first input.
    ///
    /// Raises:
    ///     ValueError: If duration is outside [0.0, 60.0].
    #[new]
    fn py_new(transition: TransitionType, duration: f64, offset: f64) -> PyResult<Self> {
        Self::new(transition, duration, offset).map_err(PyValueError::new_err)
    }

    /// Builds the xfade Filter.
    ///
    /// Returns:
    ///     A Filter with the xfade syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!(
            "XfadeBuilder(transition={}, duration={}, offset={})",
            self.transition.as_str(),
            self.duration,
            self.offset
        )
    }
}

// ========== AcrossfadeBuilder ==========

/// Type-safe builder for FFmpeg `acrossfade` audio crossfade filter.
///
/// Creates a two-input audio crossfade with configurable duration,
/// curve types, and overlap toggle.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::transitions::AcrossfadeBuilder;
///
/// let filter = AcrossfadeBuilder::new(2.0).unwrap().build();
/// assert_eq!(filter.to_string(), "acrossfade=d=2");
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct AcrossfadeBuilder {
    /// Crossfade duration in seconds.
    duration: f64,
    /// Fade curve for the first input (optional).
    curve1: Option<FadeCurve>,
    /// Fade curve for the second input (optional).
    curve2: Option<FadeCurve>,
    /// Whether to overlap the inputs (default: true).
    overlap: Option<bool>,
}

impl AcrossfadeBuilder {
    /// Creates a new AcrossfadeBuilder.
    ///
    /// # Arguments
    ///
    /// * `duration` - Crossfade duration in seconds (0.0-60.0)
    ///
    /// # Errors
    ///
    /// Returns an error if duration is outside (0.0, 60.0].
    pub fn new(duration: f64) -> Result<Self, String> {
        if duration <= 0.0 || duration > 60.0 {
            return Err(format!(
                "acrossfade duration must be > 0 and <= 60.0 seconds, got {duration}"
            ));
        }
        Ok(Self {
            duration,
            curve1: None,
            curve2: None,
            overlap: None,
        })
    }

    /// Sets the fade curve for the first input.
    #[must_use]
    pub fn with_curve1(mut self, curve: FadeCurve) -> Self {
        self.curve1 = Some(curve);
        self
    }

    /// Sets the fade curve for the second input.
    #[must_use]
    pub fn with_curve2(mut self, curve: FadeCurve) -> Self {
        self.curve2 = Some(curve);
        self
    }

    /// Sets whether inputs overlap.
    #[must_use]
    pub fn with_overlap(mut self, overlap: bool) -> Self {
        self.overlap = Some(overlap);
        self
    }

    /// Builds the acrossfade Filter.
    #[must_use]
    pub fn build(&self) -> Filter {
        let mut filter = Filter::new("acrossfade").param("d", format_value(self.duration));
        if let Some(ref c1) = self.curve1 {
            filter = filter.param("c1", c1.as_str());
        }
        if let Some(ref c2) = self.curve2 {
            filter = filter.param("c2", c2.as_str());
        }
        if let Some(overlap) = self.overlap {
            filter = filter.param("o", if overlap { 1 } else { 0 });
        }
        filter
    }
}

// ========== AcrossfadeBuilder PyO3 bindings ==========

#[pymethods]
impl AcrossfadeBuilder {
    /// Creates a new AcrossfadeBuilder.
    ///
    /// Args:
    ///     duration: Crossfade duration in seconds (> 0 and <= 60.0).
    ///
    /// Raises:
    ///     ValueError: If duration is <= 0 or > 60.0.
    #[new]
    fn py_new(duration: f64) -> PyResult<Self> {
        Self::new(duration).map_err(PyValueError::new_err)
    }

    /// Sets the fade curve for the first input.
    ///
    /// Valid curves: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par.
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If curve name is invalid.
    #[pyo3(name = "curve1")]
    fn py_curve1<'a>(mut slf: PyRefMut<'a, Self>, curve: &str) -> PyResult<PyRefMut<'a, Self>> {
        let c = FadeCurve::parse(curve).map_err(PyValueError::new_err)?;
        slf.curve1 = Some(c);
        Ok(slf)
    }

    /// Sets the fade curve for the second input.
    ///
    /// Valid curves: tri, qsin, hsin, esin, log, ipar, qua, cub, squ, cbr, par.
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If curve name is invalid.
    #[pyo3(name = "curve2")]
    fn py_curve2<'a>(mut slf: PyRefMut<'a, Self>, curve: &str) -> PyResult<PyRefMut<'a, Self>> {
        let c = FadeCurve::parse(curve).map_err(PyValueError::new_err)?;
        slf.curve2 = Some(c);
        Ok(slf)
    }

    /// Sets the overlap toggle.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "overlap")]
    fn py_overlap(mut slf: PyRefMut<'_, Self>, overlap: bool) -> PyRefMut<'_, Self> {
        slf.overlap = Some(overlap);
        slf
    }

    /// Builds the acrossfade Filter.
    ///
    /// Returns:
    ///     A Filter with the acrossfade syntax.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        format!("AcrossfadeBuilder(duration={})", self.duration)
    }
}

// ========== Tests ==========

#[cfg(test)]
mod tests {
    use super::*;

    // ========== TransitionType tests ==========

    #[test]
    fn test_transition_type_round_trip() {
        let all_variants = [
            TransitionType::Fade,
            TransitionType::Fadeblack,
            TransitionType::Fadewhite,
            TransitionType::Fadegrays,
            TransitionType::Fadefast,
            TransitionType::Fadeslow,
            TransitionType::Wipeleft,
            TransitionType::Wiperight,
            TransitionType::Wipeup,
            TransitionType::Wipedown,
            TransitionType::Wipetl,
            TransitionType::Wipetr,
            TransitionType::Wipebl,
            TransitionType::Wipebr,
            TransitionType::Slideleft,
            TransitionType::Slideright,
            TransitionType::Slideup,
            TransitionType::Slidedown,
            TransitionType::Smoothleft,
            TransitionType::Smoothright,
            TransitionType::Smoothup,
            TransitionType::Smoothdown,
            TransitionType::Circlecrop,
            TransitionType::Rectcrop,
            TransitionType::Circleopen,
            TransitionType::Circleclose,
            TransitionType::Radial,
            TransitionType::Vertopen,
            TransitionType::Vertclose,
            TransitionType::Horzopen,
            TransitionType::Horzclose,
            TransitionType::Dissolve,
            TransitionType::Pixelize,
            TransitionType::Distance,
            TransitionType::Hblur,
            TransitionType::Diagtl,
            TransitionType::Diagtr,
            TransitionType::Diagbl,
            TransitionType::Diagbr,
            TransitionType::Hlslice,
            TransitionType::Hrslice,
            TransitionType::Vuslice,
            TransitionType::Vdslice,
            TransitionType::Squeezeh,
            TransitionType::Squeezev,
            TransitionType::Zoomin,
            TransitionType::Hlwind,
            TransitionType::Hrwind,
            TransitionType::Vuwind,
            TransitionType::Vdwind,
            TransitionType::Coverleft,
            TransitionType::Coverright,
            TransitionType::Coverup,
            TransitionType::Coverdown,
            TransitionType::Revealleft,
            TransitionType::Revealright,
            TransitionType::Revealup,
            TransitionType::Revealdown,
            TransitionType::Custom,
        ];
        assert_eq!(all_variants.len(), 59, "Expected 59 transition types");
        for variant in &all_variants {
            let s = variant.as_str();
            let parsed = TransitionType::parse(s).unwrap();
            assert_eq!(*variant, parsed, "Round-trip failed for {s}");
        }
    }

    #[test]
    fn test_transition_type_invalid() {
        let result = TransitionType::parse("nonexistent");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(err.contains("invalid transition type"));
        assert!(err.contains("nonexistent"));
    }

    #[test]
    fn test_transition_type_specific_values() {
        assert_eq!(
            TransitionType::parse("wipeleft").unwrap(),
            TransitionType::Wipeleft
        );
        assert_eq!(TransitionType::Wipeleft.as_str(), "wipeleft");
        assert_eq!(
            TransitionType::parse("dissolve").unwrap(),
            TransitionType::Dissolve
        );
        assert_eq!(TransitionType::Dissolve.as_str(), "dissolve");
    }

    // ========== FadeBuilder tests ==========

    #[test]
    fn test_fade_in_basic() {
        let filter = FadeBuilder::new("in", 3.0).unwrap().build();
        assert_eq!(filter.to_string(), "fade=t=in:d=3");
    }

    #[test]
    fn test_fade_out_basic() {
        let filter = FadeBuilder::new("out", 2.0).unwrap().build();
        assert_eq!(filter.to_string(), "fade=t=out:d=2");
    }

    #[test]
    fn test_fade_with_start_time() {
        let filter = FadeBuilder::new("out", 2.0)
            .unwrap()
            .with_start_time(10.0)
            .build();
        assert_eq!(filter.to_string(), "fade=t=out:d=2:st=10");
    }

    #[test]
    fn test_fade_with_color() {
        let filter = FadeBuilder::new("in", 1.0)
            .unwrap()
            .with_color("white")
            .build();
        assert_eq!(filter.to_string(), "fade=t=in:d=1:c=white");
    }

    #[test]
    fn test_fade_with_hex_color() {
        let filter = FadeBuilder::new("in", 1.0)
            .unwrap()
            .with_color("#FF0000")
            .build();
        assert_eq!(filter.to_string(), "fade=t=in:d=1:c=#FF0000");
    }

    #[test]
    fn test_fade_with_alpha() {
        let filter = FadeBuilder::new("in", 1.0)
            .unwrap()
            .with_alpha(true)
            .build();
        assert_eq!(filter.to_string(), "fade=t=in:d=1:alpha=1");
    }

    #[test]
    fn test_fade_with_nb_frames() {
        let filter = FadeBuilder::new("in", 1.0)
            .unwrap()
            .with_nb_frames(30)
            .build();
        // nb_frames replaces duration
        assert_eq!(filter.to_string(), "fade=t=in:nb_frames=30");
    }

    #[test]
    fn test_fade_all_options() {
        let filter = FadeBuilder::new("out", 2.5)
            .unwrap()
            .with_start_time(5.0)
            .with_color("white")
            .with_alpha(true)
            .build();
        let s = filter.to_string();
        assert!(s.contains("t=out"));
        assert!(s.contains("d=2.5"));
        assert!(s.contains("st=5"));
        assert!(s.contains("c=white"));
        assert!(s.contains("alpha=1"));
    }

    #[test]
    fn test_fade_invalid_type() {
        let result = FadeBuilder::new("up", 1.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("'in' or 'out'"));
    }

    #[test]
    fn test_fade_zero_duration() {
        let result = FadeBuilder::new("in", 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("> 0"));
    }

    #[test]
    fn test_fade_negative_duration() {
        let result = FadeBuilder::new("in", -1.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_fade_fractional_duration() {
        let filter = FadeBuilder::new("in", 0.5).unwrap().build();
        assert_eq!(filter.to_string(), "fade=t=in:d=0.5");
    }

    // ========== XfadeBuilder tests ==========

    #[test]
    fn test_xfade_basic() {
        let filter = XfadeBuilder::new(TransitionType::Wipeleft, 2.0, 5.0)
            .unwrap()
            .build();
        assert_eq!(
            filter.to_string(),
            "xfade=transition=wipeleft:duration=2:offset=5"
        );
    }

    #[test]
    fn test_xfade_dissolve() {
        let filter = XfadeBuilder::new(TransitionType::Dissolve, 1.5, 3.0)
            .unwrap()
            .build();
        assert_eq!(
            filter.to_string(),
            "xfade=transition=dissolve:duration=1.5:offset=3"
        );
    }

    #[test]
    fn test_xfade_all_transition_types_produce_valid_filter() {
        let types = [
            TransitionType::Fade,
            TransitionType::Fadeblack,
            TransitionType::Wipeleft,
            TransitionType::Circlecrop,
            TransitionType::Dissolve,
            TransitionType::Zoomin,
            TransitionType::Custom,
        ];
        for tt in &types {
            let filter = XfadeBuilder::new(*tt, 1.0, 0.0).unwrap().build();
            let s = filter.to_string();
            assert!(
                s.contains(&format!("transition={}", tt.as_str())),
                "Missing transition in: {s}"
            );
        }
    }

    #[test]
    fn test_xfade_duration_min() {
        let filter = XfadeBuilder::new(TransitionType::Fade, 0.0, 0.0)
            .unwrap()
            .build();
        assert!(filter.to_string().contains("duration=0"));
    }

    #[test]
    fn test_xfade_duration_max() {
        let filter = XfadeBuilder::new(TransitionType::Fade, 60.0, 0.0)
            .unwrap()
            .build();
        assert!(filter.to_string().contains("duration=60"));
    }

    #[test]
    fn test_xfade_duration_below_range() {
        let result = XfadeBuilder::new(TransitionType::Fade, -0.1, 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("0.0-60.0"));
    }

    #[test]
    fn test_xfade_duration_above_range() {
        let result = XfadeBuilder::new(TransitionType::Fade, 60.1, 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("0.0-60.0"));
    }

    #[test]
    fn test_xfade_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let xfade = XfadeBuilder::new(TransitionType::Wipeleft, 2.0, 5.0)
            .unwrap()
            .build();
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .input("1:v")
                .filter(xfade)
                .output("out"),
        );
        let s = graph.to_string();
        assert!(s.contains("[0:v][1:v]"));
        assert!(s.contains("xfade="));
        assert!(s.contains("[out]"));
    }

    // ========== AcrossfadeBuilder tests ==========

    #[test]
    fn test_acrossfade_basic() {
        let filter = AcrossfadeBuilder::new(2.0).unwrap().build();
        assert_eq!(filter.to_string(), "acrossfade=d=2");
    }

    #[test]
    fn test_acrossfade_with_curves() {
        let filter = AcrossfadeBuilder::new(1.5)
            .unwrap()
            .with_curve1(FadeCurve::Qsin)
            .with_curve2(FadeCurve::Log)
            .build();
        assert_eq!(filter.to_string(), "acrossfade=d=1.5:c1=qsin:c2=log");
    }

    #[test]
    fn test_acrossfade_overlap_disabled() {
        let filter = AcrossfadeBuilder::new(2.0)
            .unwrap()
            .with_overlap(false)
            .build();
        assert_eq!(filter.to_string(), "acrossfade=d=2:o=0");
    }

    #[test]
    fn test_acrossfade_overlap_enabled() {
        let filter = AcrossfadeBuilder::new(2.0)
            .unwrap()
            .with_overlap(true)
            .build();
        assert_eq!(filter.to_string(), "acrossfade=d=2:o=1");
    }

    #[test]
    fn test_acrossfade_all_options() {
        let filter = AcrossfadeBuilder::new(3.0)
            .unwrap()
            .with_curve1(FadeCurve::Hsin)
            .with_curve2(FadeCurve::Esin)
            .with_overlap(false)
            .build();
        let s = filter.to_string();
        assert!(s.contains("d=3"));
        assert!(s.contains("c1=hsin"));
        assert!(s.contains("c2=esin"));
        assert!(s.contains("o=0"));
    }

    #[test]
    fn test_acrossfade_zero_duration() {
        let result = AcrossfadeBuilder::new(0.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_acrossfade_negative_duration() {
        let result = AcrossfadeBuilder::new(-1.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_acrossfade_above_max_duration() {
        let result = AcrossfadeBuilder::new(61.0);
        assert!(result.is_err());
    }

    #[test]
    fn test_acrossfade_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let acf = AcrossfadeBuilder::new(2.0).unwrap().build();
        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:a")
                .input("1:a")
                .filter(acf)
                .output("aout"),
        );
        let s = graph.to_string();
        assert!(s.contains("[0:a][1:a]"));
        assert!(s.contains("acrossfade="));
        assert!(s.contains("[aout]"));
    }

    // ========== Validation tests ==========

    #[test]
    fn test_fade_duration_validation_message() {
        let result = FadeBuilder::new("in", -5.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("> 0"));
    }

    #[test]
    fn test_xfade_duration_validation_message() {
        let result = XfadeBuilder::new(TransitionType::Fade, 100.0, 0.0);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("0.0-60.0"));
    }

    #[test]
    fn test_transition_type_invalid_returns_valid_list() {
        let result = TransitionType::parse("invalid");
        let err = result.unwrap_err();
        assert!(err.contains("fade"));
        assert!(err.contains("wipeleft"));
        assert!(err.contains("dissolve"));
    }

    // ========== Additional coverage tests ==========

    #[test]
    fn test_fade_with_alpha_false() {
        let filter = FadeBuilder::new("in", 1.0)
            .unwrap()
            .with_alpha(false)
            .build();
        let s = filter.to_string();
        assert!(!s.contains("alpha="));
    }

    #[test]
    fn test_fade_with_all_and_nb_frames() {
        let filter = FadeBuilder::new("out", 2.0)
            .unwrap()
            .with_start_time(5.0)
            .with_color("white")
            .with_alpha(true)
            .with_nb_frames(60)
            .build();
        let s = filter.to_string();
        assert!(s.contains("nb_frames=60"));
        assert!(!s.contains("d=2"));
        assert!(s.contains("st=5"));
        assert!(s.contains("c=white"));
        assert!(s.contains("alpha=1"));
    }

    #[test]
    fn test_format_value_integer() {
        assert_eq!(format_value(5.0), "5");
        assert_eq!(format_value(0.0), "0");
    }

    #[test]
    fn test_format_value_decimal() {
        assert_eq!(format_value(2.5), "2.5");
        assert_eq!(format_value(0.333), "0.333");
    }

    #[test]
    fn test_acrossfade_max_duration() {
        let filter = AcrossfadeBuilder::new(60.0).unwrap().build();
        assert!(filter.to_string().contains("d=60"));
    }

    #[test]
    fn test_acrossfade_fractional_duration() {
        let filter = AcrossfadeBuilder::new(0.5).unwrap().build();
        assert_eq!(filter.to_string(), "acrossfade=d=0.5");
    }

    #[test]
    fn test_xfade_fractional_offset() {
        let filter = XfadeBuilder::new(TransitionType::Fade, 1.0, 3.5)
            .unwrap()
            .build();
        assert!(filter.to_string().contains("offset=3.5"));
    }

    #[test]
    fn test_fade_repr() {
        let builder = FadeBuilder::new("in", 2.0).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("FadeBuilder"));
        assert!(repr.contains("in"));
    }

    #[test]
    fn test_xfade_repr() {
        let builder = XfadeBuilder::new(TransitionType::Wipeleft, 2.0, 5.0).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("XfadeBuilder"));
        assert!(repr.contains("wipeleft"));
    }

    #[test]
    fn test_acrossfade_repr() {
        let builder = AcrossfadeBuilder::new(2.0).unwrap();
        let repr = builder.__repr__();
        assert!(repr.contains("AcrossfadeBuilder"));
    }

    #[test]
    fn test_transition_type_repr() {
        let tt = TransitionType::Dissolve;
        let repr = tt.__repr__();
        assert!(repr.contains("Dissolve"));
        assert_eq!(tt.__str__(), "dissolve");
    }

    // ========== Proptest ==========

    use proptest::prelude::*;

    fn arb_transition_type() -> impl Strategy<Value = TransitionType> {
        prop_oneof![
            Just(TransitionType::Fade),
            Just(TransitionType::Fadeblack),
            Just(TransitionType::Fadewhite),
            Just(TransitionType::Fadegrays),
            Just(TransitionType::Fadefast),
            Just(TransitionType::Fadeslow),
            Just(TransitionType::Wipeleft),
            Just(TransitionType::Wiperight),
            Just(TransitionType::Wipeup),
            Just(TransitionType::Wipedown),
            Just(TransitionType::Wipetl),
            Just(TransitionType::Wipetr),
            Just(TransitionType::Wipebl),
            Just(TransitionType::Wipebr),
            Just(TransitionType::Slideleft),
            Just(TransitionType::Slideright),
            Just(TransitionType::Slideup),
            Just(TransitionType::Slidedown),
            Just(TransitionType::Smoothleft),
            Just(TransitionType::Smoothright),
            Just(TransitionType::Smoothup),
            Just(TransitionType::Smoothdown),
            Just(TransitionType::Circlecrop),
            Just(TransitionType::Rectcrop),
            Just(TransitionType::Circleopen),
            Just(TransitionType::Circleclose),
            Just(TransitionType::Radial),
            Just(TransitionType::Vertopen),
            Just(TransitionType::Vertclose),
            Just(TransitionType::Horzopen),
            Just(TransitionType::Horzclose),
            Just(TransitionType::Dissolve),
            Just(TransitionType::Pixelize),
            Just(TransitionType::Distance),
            Just(TransitionType::Hblur),
            Just(TransitionType::Diagtl),
            Just(TransitionType::Diagtr),
            Just(TransitionType::Diagbl),
            Just(TransitionType::Diagbr),
            Just(TransitionType::Hlslice),
            Just(TransitionType::Hrslice),
            Just(TransitionType::Vuslice),
            Just(TransitionType::Vdslice),
            Just(TransitionType::Squeezeh),
            Just(TransitionType::Squeezev),
            Just(TransitionType::Zoomin),
            Just(TransitionType::Hlwind),
            Just(TransitionType::Hrwind),
            Just(TransitionType::Vuwind),
            Just(TransitionType::Vdwind),
            Just(TransitionType::Coverleft),
            Just(TransitionType::Coverright),
            Just(TransitionType::Coverup),
            Just(TransitionType::Coverdown),
            Just(TransitionType::Revealleft),
            Just(TransitionType::Revealright),
            Just(TransitionType::Revealup),
            Just(TransitionType::Revealdown),
            Just(TransitionType::Custom),
        ]
    }

    proptest! {
        /// Property: all valid fade durations produce valid fade filter strings.
        #[test]
        fn fade_builder_valid(duration in 0.01f64..=60.0) {
            let fade_type = if duration.to_bits() % 2 == 0 { "in" } else { "out" };
            let builder = FadeBuilder::new(fade_type, duration).unwrap();
            let filter = builder.build();
            let s = filter.to_string();
            prop_assert!(s.starts_with("fade="), "Got: {}", s);
            prop_assert!(s.contains("t="), "Missing type param: {}", s);
        }

        /// Property: all transition types with valid durations produce valid xfade filter strings.
        #[test]
        fn xfade_builder_valid(
            tt in arb_transition_type(),
            duration in 0.01f64..=60.0,
            offset in 0.0f64..=300.0,
        ) {
            let builder = XfadeBuilder::new(tt, duration, offset).unwrap();
            let filter = builder.build();
            let s = filter.to_string();
            prop_assert!(s.starts_with("xfade="), "Got: {}", s);
            prop_assert!(s.contains(&format!("transition={}", tt.as_str())), "Missing transition: {}", s);
            prop_assert!(s.contains("duration="), "Missing duration: {}", s);
            prop_assert!(s.contains("offset="), "Missing offset: {}", s);
        }

        /// Property: all valid durations produce valid acrossfade filter strings.
        #[test]
        fn acrossfade_builder_valid(duration in 0.01f64..=60.0) {
            let builder = AcrossfadeBuilder::new(duration).unwrap();
            let filter = builder.build();
            let s = filter.to_string();
            prop_assert!(s.starts_with("acrossfade="), "Got: {}", s);
            prop_assert!(s.contains("d="), "Missing duration param: {}", s);
        }
    }

    // ========== PyO3 binding tests ==========

    use pyo3::prelude::*;

    #[test]
    fn test_pyo3_fade_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let fb = Bound::new(py, FadeBuilder::new("in", 2.0).unwrap()).unwrap();
            fb.call_method1("start_time", (5.0f64,)).unwrap();
            fb.call_method1("color", ("white",)).unwrap();
            fb.call_method1("alpha", (true,)).unwrap();
            fb.call_method1("nb_frames", (30u64,)).unwrap();
            let filter: String = fb
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filter.contains("fade="));
            let repr: String = fb.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("FadeBuilder"));

            // Test py_new error
            assert!(FadeBuilder::py_new("bad", 1.0).is_err());
        });
    }

    #[test]
    fn test_pyo3_xfade_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let xf = Bound::new(
                py,
                XfadeBuilder::new(TransitionType::Wipeleft, 2.0, 5.0).unwrap(),
            )
            .unwrap();
            let filter: String = xf
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filter.contains("xfade="));
            let repr: String = xf.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("XfadeBuilder"));

            // Test py_new error
            assert!(XfadeBuilder::py_new(TransitionType::Fade, 100.0, 0.0).is_err());
        });
    }

    #[test]
    fn test_pyo3_acrossfade_builder() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let acf = Bound::new(py, AcrossfadeBuilder::new(2.0).unwrap()).unwrap();
            acf.call_method1("curve1", ("qsin",)).unwrap();
            acf.call_method1("curve2", ("log",)).unwrap();
            acf.call_method1("overlap", (false,)).unwrap();
            let filter: String = acf
                .call_method0("build")
                .unwrap()
                .call_method0("__str__")
                .unwrap()
                .extract()
                .unwrap();
            assert!(filter.contains("acrossfade="));
            let repr: String = acf.call_method0("__repr__").unwrap().extract().unwrap();
            assert!(repr.contains("AcrossfadeBuilder"));

            // Test curve error
            let acf2 = Bound::new(py, AcrossfadeBuilder::new(1.0).unwrap()).unwrap();
            assert!(acf2.call_method1("curve1", ("invalid",)).is_err());
            assert!(acf2.call_method1("curve2", ("invalid",)).is_err());

            // Test py_new error
            assert!(AcrossfadeBuilder::py_new(0.0).is_err());
        });
    }

    #[test]
    fn test_pyo3_transition_type() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let tt = TransitionType::py_from_str("dissolve").unwrap();
            assert_eq!(tt.py_as_str(), "dissolve");
            assert!(TransitionType::py_from_str("invalid").is_err());
        });
    }
}
