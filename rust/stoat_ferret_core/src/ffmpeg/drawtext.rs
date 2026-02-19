//! Type-safe drawtext filter builder for FFmpeg text overlays.
//!
//! This module provides a builder for constructing FFmpeg `drawtext` filters
//! with position presets, font styling, shadow, box background, and alpha
//! animation via the expression engine.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::drawtext::{DrawtextBuilder, Position};
//!
//! let filter = DrawtextBuilder::new("Hello World")
//!     .font("monospace")
//!     .fontsize(24)
//!     .fontcolor("white")
//!     .position(Position::Center)
//!     .shadow(2, 2, "black")
//!     .build();
//!
//! let s = filter.to_string();
//! assert!(s.starts_with("drawtext="));
//! assert!(s.contains("text="));
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::expression::{Expr, Variable};
use super::filter::Filter;

/// Escapes text for drawtext filter, extending `escape_filter_text` with `%` -> `%%`.
///
/// The drawtext filter uses `%` for text expansion (e.g., `%{localtime}`),
/// so literal percent signs must be doubled.
fn escape_drawtext(input: &str) -> String {
    let mut result = String::with_capacity(input.len() * 2);
    for c in input.chars() {
        match c {
            '\\' => result.push_str("\\\\"),
            '\'' => result.push_str("'\\''"),
            ':' => result.push_str("\\:"),
            '[' => result.push_str("\\["),
            ']' => result.push_str("\\]"),
            ';' => result.push_str("\\;"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            '%' => result.push_str("%%"),
            _ => result.push(c),
        }
    }
    result
}

/// Position presets for drawtext placement.
///
/// These presets generate the appropriate `x` and `y` FFmpeg expression
/// strings using drawtext variables (`w`, `h`, `text_w`, `text_h`).
#[derive(Debug, Clone, PartialEq)]
pub enum Position {
    /// Absolute pixel coordinates.
    Absolute {
        /// X coordinate.
        x: i32,
        /// Y coordinate.
        y: i32,
    },
    /// Centered horizontally and vertically.
    Center,
    /// Centered horizontally, near the bottom edge.
    BottomCenter {
        /// Margin from the bottom edge in pixels.
        margin: u32,
    },
    /// Top-left corner with margin.
    TopLeft {
        /// Margin from top and left edges in pixels.
        margin: u32,
    },
    /// Top-right corner with margin.
    TopRight {
        /// Margin from top and right edges in pixels.
        margin: u32,
    },
    /// Bottom-left corner with margin.
    BottomLeft {
        /// Margin from bottom and left edges in pixels.
        margin: u32,
    },
    /// Bottom-right corner with margin.
    BottomRight {
        /// Margin from bottom and right edges in pixels.
        margin: u32,
    },
}

impl Position {
    /// Returns the `(x, y)` expression strings for this position preset.
    fn to_xy(&self) -> (String, String) {
        match self {
            Position::Absolute { x, y } => (x.to_string(), y.to_string()),
            Position::Center => ("(w-text_w)/2".to_string(), "(h-text_h)/2".to_string()),
            Position::BottomCenter { margin } => {
                ("(w-text_w)/2".to_string(), format!("h-text_h-{margin}"))
            }
            Position::TopLeft { margin } => (margin.to_string(), margin.to_string()),
            Position::TopRight { margin } => (format!("w-text_w-{margin}"), margin.to_string()),
            Position::BottomLeft { margin } => (margin.to_string(), format!("h-text_h-{margin}")),
            Position::BottomRight { margin } => {
                (format!("w-text_w-{margin}"), format!("h-text_h-{margin}"))
            }
        }
    }
}

/// A type-safe builder for FFmpeg drawtext filters.
///
/// Text is mandatory and set at construction time. All other parameters
/// are optional with sensible defaults.
///
/// # Defaults
///
/// - `fontsize`: 16
/// - `fontcolor`: "black"
/// - Position: not set (FFmpeg defaults to 0,0)
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::ffmpeg::drawtext::{DrawtextBuilder, Position};
///
/// let filter = DrawtextBuilder::new("Score: 100%")
///     .font("monospace")
///     .fontsize(32)
///     .fontcolor("white")
///     .position(Position::BottomCenter { margin: 10 })
///     .box_background("black@0.5", 5)
///     .build();
///
/// let s = filter.to_string();
/// assert!(s.contains("text=Score\\: 100%%"));
/// assert!(s.contains("font=monospace"));
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct DrawtextBuilder {
    text: String,
    font: Option<String>,
    fontfile: Option<String>,
    fontsize: u32,
    fontcolor: String,
    position: Option<Position>,
    shadow_x: Option<i32>,
    shadow_y: Option<i32>,
    shadow_color: Option<String>,
    box_enabled: bool,
    box_color: Option<String>,
    box_borderw: Option<u32>,
    alpha: Option<String>,
    enable: Option<String>,
}

impl DrawtextBuilder {
    /// Creates a new drawtext builder with the given text.
    ///
    /// The text is automatically escaped for FFmpeg drawtext syntax,
    /// including `%` -> `%%` for text expansion mode.
    ///
    /// # Arguments
    ///
    /// * `text` - The text to display
    #[must_use]
    pub fn new(text: &str) -> Self {
        Self {
            text: escape_drawtext(text),
            font: None,
            fontfile: None,
            fontsize: 16,
            fontcolor: "black".to_string(),
            position: None,
            shadow_x: None,
            shadow_y: None,
            shadow_color: None,
            box_enabled: false,
            box_color: None,
            box_borderw: None,
            alpha: None,
            enable: None,
        }
    }

    /// Sets the font name via fontconfig lookup.
    ///
    /// This is the cross-platform way to specify fonts. The font name
    /// is resolved by fontconfig at runtime.
    ///
    /// # Arguments
    ///
    /// * `name` - The fontconfig font name (e.g., "monospace", "Sans")
    #[must_use]
    pub fn font(mut self, name: &str) -> Self {
        self.font = Some(name.to_string());
        self.fontfile = None;
        self
    }

    /// Sets the font file path directly.
    ///
    /// Use this when you need a specific font file rather than fontconfig lookup.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the font file
    #[must_use]
    pub fn fontfile(mut self, path: &str) -> Self {
        self.fontfile = Some(path.to_string());
        self.font = None;
        self
    }

    /// Sets the font size in pixels.
    ///
    /// Default is 16.
    ///
    /// # Arguments
    ///
    /// * `size` - Font size in pixels
    #[must_use]
    pub fn fontsize(mut self, size: u32) -> Self {
        self.fontsize = size;
        self
    }

    /// Sets the font color.
    ///
    /// Default is "black". Accepts FFmpeg color names or hex values.
    ///
    /// # Arguments
    ///
    /// * `color` - Font color (e.g., "white", "red", "#FF0000", "white@0.5")
    #[must_use]
    pub fn fontcolor(mut self, color: &str) -> Self {
        self.fontcolor = color.to_string();
        self
    }

    /// Sets the text position using a preset.
    ///
    /// # Arguments
    ///
    /// * `pos` - Position preset
    #[must_use]
    pub fn position(mut self, pos: Position) -> Self {
        self.position = Some(pos);
        self
    }

    /// Adds a shadow effect to the text.
    ///
    /// # Arguments
    ///
    /// * `x_offset` - Horizontal shadow offset in pixels
    /// * `y_offset` - Vertical shadow offset in pixels
    /// * `color` - Shadow color
    #[must_use]
    pub fn shadow(mut self, x_offset: i32, y_offset: i32, color: &str) -> Self {
        self.shadow_x = Some(x_offset);
        self.shadow_y = Some(y_offset);
        self.shadow_color = Some(color.to_string());
        self
    }

    /// Adds a box background behind the text.
    ///
    /// Uses single-value `boxborderw` only (no per-side syntax).
    ///
    /// # Arguments
    ///
    /// * `color` - Box background color (e.g., "black@0.5")
    /// * `borderw` - Box border width in pixels
    #[must_use]
    pub fn box_background(mut self, color: &str, borderw: u32) -> Self {
        self.box_enabled = true;
        self.box_color = Some(color.to_string());
        self.box_borderw = Some(borderw);
        self
    }

    /// Sets a static alpha value for the text.
    ///
    /// # Arguments
    ///
    /// * `value` - Alpha value between 0.0 (transparent) and 1.0 (opaque)
    #[must_use]
    pub fn alpha(mut self, value: f64) -> Self {
        let clamped = value.clamp(0.0, 1.0);
        // Format without trailing zeros for clean output
        if clamped.fract() == 0.0 {
            self.alpha = Some(format!("{}", clamped as i64));
        } else {
            self.alpha = Some(format!("{clamped}"));
        }
        self
    }

    /// Sets an alpha fade animation using the expression engine.
    ///
    /// Generates the pattern:
    /// `if(lt(t,T1),0,if(lt(t,T1+FI),(t-T1)/FI,if(lt(t,T2-FO),1,if(lt(t,T2),(T2-t)/FO,0))))`
    ///
    /// # Arguments
    ///
    /// * `start_time` - When the text first appears (seconds)
    /// * `fade_in` - Duration of fade in (seconds)
    /// * `end_time` - When the text starts fading out (seconds)
    /// * `fade_out` - Duration of fade out (seconds)
    #[must_use]
    pub fn alpha_fade(
        mut self,
        start_time: f64,
        fade_in: f64,
        end_time: f64,
        fade_out: f64,
    ) -> Self {
        let t = Expr::var(Variable::T);
        let t1 = Expr::constant(start_time);
        let fi = Expr::constant(fade_in);
        let t2 = Expr::constant(end_time);
        let fo = Expr::constant(fade_out);

        // Build the nested if expression from inside out:
        // if(lt(t,T2), (T2-t)/FO, 0)
        let fade_out_expr = Expr::if_then_else(
            Expr::lt(t.clone(), t2.clone()),
            (t2.clone() - t.clone()) / fo,
            Expr::constant(0.0),
        );

        // if(lt(t,T2-FO), 1, fade_out_expr)
        let visible_expr = Expr::if_then_else(
            Expr::lt(t.clone(), t2 - Expr::constant(fade_out)),
            Expr::constant(1.0),
            fade_out_expr,
        );

        // if(lt(t,T1+FI), (t-T1)/FI, visible_expr)
        let fade_in_expr = Expr::if_then_else(
            Expr::lt(t.clone(), t1.clone() + fi.clone()),
            (t.clone() - t1.clone()) / fi,
            visible_expr,
        );

        // if(lt(t,T1), 0, fade_in_expr)
        let full_expr = Expr::if_then_else(Expr::lt(t, t1), Expr::constant(0.0), fade_in_expr);

        self.alpha = Some(full_expr.to_string());
        self
    }

    /// Sets a time-based enable expression.
    ///
    /// # Arguments
    ///
    /// * `expr` - An FFmpeg expression string for the `enable` parameter
    #[must_use]
    pub fn enable(mut self, expr: &str) -> Self {
        self.enable = Some(expr.to_string());
        self
    }

    /// Builds the drawtext filter.
    ///
    /// Returns a [`Filter`] that can be used in filter chains and graphs.
    #[must_use]
    pub fn build(self) -> Filter {
        let mut filter = Filter::new("drawtext").param("text", &self.text);

        // Font specification
        if let Some(font) = &self.font {
            filter = filter.param("font", font);
        }
        if let Some(fontfile) = &self.fontfile {
            filter = filter.param("fontfile", fontfile);
        }

        // Font styling
        filter = filter
            .param("fontsize", self.fontsize)
            .param("fontcolor", &self.fontcolor);

        // Position
        if let Some(pos) = &self.position {
            let (x, y) = pos.to_xy();
            filter = filter.param("x", &x).param("y", &y);
        }

        // Shadow
        if let Some(sx) = self.shadow_x {
            filter = filter.param("shadowx", sx);
        }
        if let Some(sy) = self.shadow_y {
            filter = filter.param("shadowy", sy);
        }
        if let Some(sc) = &self.shadow_color {
            filter = filter.param("shadowcolor", sc);
        }

        // Box background
        if self.box_enabled {
            filter = filter.param("box", 1);
            if let Some(bc) = &self.box_color {
                filter = filter.param("boxcolor", bc);
            }
            if let Some(bw) = self.box_borderw {
                filter = filter.param("boxborderw", bw);
            }
        }

        // Alpha
        if let Some(alpha) = &self.alpha {
            filter = filter.param("alpha", format!("'{alpha}'"));
        }

        // Enable expression
        if let Some(enable) = &self.enable {
            filter = filter.param("enable", format!("'{enable}'"));
        }

        filter
    }
}

// ========== PyO3 bindings ==========

#[pymethods]
impl DrawtextBuilder {
    /// Creates a new drawtext builder with the given text.
    ///
    /// The text is automatically escaped for FFmpeg drawtext syntax.
    #[new]
    fn py_new(text: &str) -> Self {
        Self::new(text)
    }

    /// Sets the font name via fontconfig lookup.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "font")]
    fn py_font<'a>(mut slf: PyRefMut<'a, Self>, name: &str) -> PyRefMut<'a, Self> {
        slf.font = Some(name.to_string());
        slf.fontfile = None;
        slf
    }

    /// Sets the font file path directly.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "fontfile")]
    fn py_fontfile<'a>(mut slf: PyRefMut<'a, Self>, path: &str) -> PyRefMut<'a, Self> {
        slf.fontfile = Some(path.to_string());
        slf.font = None;
        slf
    }

    /// Sets the font size in pixels.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "fontsize")]
    fn py_fontsize(mut slf: PyRefMut<'_, Self>, size: u32) -> PyRefMut<'_, Self> {
        slf.fontsize = size;
        slf
    }

    /// Sets the font color.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "fontcolor")]
    fn py_fontcolor<'a>(mut slf: PyRefMut<'a, Self>, color: &str) -> PyRefMut<'a, Self> {
        slf.fontcolor = color.to_string();
        slf
    }

    /// Sets the text position using a preset name.
    ///
    /// Preset names: "center", "bottom_center", "top_left", "top_right",
    /// "bottom_left", "bottom_right".
    ///
    /// For presets with margin, pass the margin parameter (default: 10).
    /// For absolute positioning, pass x and y coordinates.
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If preset name is unknown.
    #[pyo3(name = "position", signature = (preset, margin=10, x=0, y=0))]
    fn py_position<'a>(
        mut slf: PyRefMut<'a, Self>,
        preset: &str,
        margin: u32,
        x: i32,
        y: i32,
    ) -> PyResult<PyRefMut<'a, Self>> {
        let pos = match preset {
            "center" => Position::Center,
            "bottom_center" => Position::BottomCenter { margin },
            "top_left" => Position::TopLeft { margin },
            "top_right" => Position::TopRight { margin },
            "bottom_left" => Position::BottomLeft { margin },
            "bottom_right" => Position::BottomRight { margin },
            "absolute" => Position::Absolute { x, y },
            _ => {
                return Err(PyValueError::new_err(format!(
                    "unknown position preset: '{preset}'. Use: center, bottom_center, \
                     top_left, top_right, bottom_left, bottom_right, absolute"
                )))
            }
        };
        slf.position = Some(pos);
        Ok(slf)
    }

    /// Adds a shadow effect to the text.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "shadow")]
    fn py_shadow<'a>(
        mut slf: PyRefMut<'a, Self>,
        x_offset: i32,
        y_offset: i32,
        color: &str,
    ) -> PyRefMut<'a, Self> {
        slf.shadow_x = Some(x_offset);
        slf.shadow_y = Some(y_offset);
        slf.shadow_color = Some(color.to_string());
        slf
    }

    /// Adds a box background behind the text.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "box_background")]
    fn py_box_background<'a>(
        mut slf: PyRefMut<'a, Self>,
        color: &str,
        borderw: u32,
    ) -> PyRefMut<'a, Self> {
        slf.box_enabled = true;
        slf.box_color = Some(color.to_string());
        slf.box_borderw = Some(borderw);
        slf
    }

    /// Sets a static alpha value (0.0 to 1.0).
    ///
    /// Returns self for method chaining.
    ///
    /// Raises:
    ///     ValueError: If alpha is not in [0.0, 1.0].
    #[pyo3(name = "alpha")]
    fn py_alpha(mut slf: PyRefMut<'_, Self>, value: f64) -> PyResult<PyRefMut<'_, Self>> {
        if !(0.0..=1.0).contains(&value) {
            return Err(PyValueError::new_err(format!(
                "alpha must be between 0.0 and 1.0, got {value}"
            )));
        }
        if value.fract() == 0.0 {
            slf.alpha = Some(format!("{}", value as i64));
        } else {
            slf.alpha = Some(format!("{value}"));
        }
        Ok(slf)
    }

    /// Sets an alpha fade animation.
    ///
    /// Generates a fade-in/fade-out expression using the expression engine.
    ///
    /// Args:
    ///     start_time: When the text first appears (seconds).
    ///     fade_in: Duration of fade in (seconds).
    ///     end_time: When the text starts fading out (seconds).
    ///     fade_out: Duration of fade out (seconds).
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "alpha_fade")]
    fn py_alpha_fade(
        mut slf: PyRefMut<'_, Self>,
        start_time: f64,
        fade_in: f64,
        end_time: f64,
        fade_out: f64,
    ) -> PyRefMut<'_, Self> {
        let t = Expr::var(Variable::T);
        let t1 = Expr::constant(start_time);
        let fi = Expr::constant(fade_in);
        let t2 = Expr::constant(end_time);
        let fo = Expr::constant(fade_out);

        let fade_out_expr = Expr::if_then_else(
            Expr::lt(t.clone(), t2.clone()),
            (t2.clone() - t.clone()) / fo,
            Expr::constant(0.0),
        );

        let visible_expr = Expr::if_then_else(
            Expr::lt(t.clone(), t2 - Expr::constant(fade_out)),
            Expr::constant(1.0),
            fade_out_expr,
        );

        let fade_in_expr = Expr::if_then_else(
            Expr::lt(t.clone(), t1.clone() + fi.clone()),
            (t.clone() - t1.clone()) / fi,
            visible_expr,
        );

        let full_expr = Expr::if_then_else(Expr::lt(t, t1), Expr::constant(0.0), fade_in_expr);

        slf.alpha = Some(full_expr.to_string());
        slf
    }

    /// Sets a time-based enable expression.
    ///
    /// Returns self for method chaining.
    #[pyo3(name = "enable")]
    fn py_enable<'a>(mut slf: PyRefMut<'a, Self>, expr: &str) -> PyRefMut<'a, Self> {
        slf.enable = Some(expr.to_string());
        slf
    }

    /// Builds the drawtext filter.
    ///
    /// Returns a Filter that can be used in filter chains and graphs.
    #[pyo3(name = "build")]
    fn py_build(&self) -> Filter {
        self.clone().build()
    }

    /// Returns a string representation of the builder.
    fn __repr__(&self) -> String {
        "DrawtextBuilder(text=...)".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========== Text escaping tests ==========

    #[test]
    fn test_escape_drawtext_basic() {
        assert_eq!(escape_drawtext("hello"), "hello");
    }

    #[test]
    fn test_escape_drawtext_colon() {
        assert_eq!(escape_drawtext("key:value"), "key\\:value");
    }

    #[test]
    fn test_escape_drawtext_percent() {
        assert_eq!(escape_drawtext("100%"), "100%%");
    }

    #[test]
    fn test_escape_drawtext_percent_and_colon() {
        assert_eq!(escape_drawtext("Score: 100%"), "Score\\: 100%%");
    }

    #[test]
    fn test_escape_drawtext_all_special() {
        assert_eq!(escape_drawtext("\\':[];%"), "\\\\'\\''\\:\\[\\]\\;%%");
    }

    #[test]
    fn test_escape_drawtext_utf8() {
        assert_eq!(escape_drawtext("Hello, 世界!"), "Hello, 世界!");
    }

    #[test]
    fn test_escape_drawtext_newlines() {
        assert_eq!(escape_drawtext("line1\nline2"), "line1\\nline2");
    }

    // ========== Basic builder tests ==========

    #[test]
    fn test_build_minimal() {
        let filter = DrawtextBuilder::new("hello").build();
        let s = filter.to_string();
        assert!(s.starts_with("drawtext="));
        assert!(s.contains("text=hello"));
        assert!(s.contains("fontsize=16"));
        assert!(s.contains("fontcolor=black"));
    }

    #[test]
    fn test_build_with_font() {
        let filter = DrawtextBuilder::new("hello").font("monospace").build();
        let s = filter.to_string();
        assert!(s.contains("font=monospace"));
    }

    #[test]
    fn test_build_with_fontfile() {
        let filter = DrawtextBuilder::new("hello")
            .fontfile("/path/to/font.ttf")
            .build();
        let s = filter.to_string();
        assert!(s.contains("fontfile=/path/to/font.ttf"));
        assert!(!s.contains("font="));
    }

    #[test]
    fn test_font_overrides_fontfile() {
        let filter = DrawtextBuilder::new("hello")
            .fontfile("/path/to/font.ttf")
            .font("monospace")
            .build();
        let s = filter.to_string();
        assert!(s.contains("font=monospace"));
        assert!(!s.contains("fontfile="));
    }

    #[test]
    fn test_fontfile_overrides_font() {
        let filter = DrawtextBuilder::new("hello")
            .font("monospace")
            .fontfile("/path/to/font.ttf")
            .build();
        let s = filter.to_string();
        assert!(s.contains("fontfile=/path/to/font.ttf"));
        assert!(!s.contains("font=monospace"));
    }

    #[test]
    fn test_build_with_fontsize() {
        let filter = DrawtextBuilder::new("hello").fontsize(24).build();
        let s = filter.to_string();
        assert!(s.contains("fontsize=24"));
    }

    #[test]
    fn test_build_with_fontcolor() {
        let filter = DrawtextBuilder::new("hello").fontcolor("white").build();
        let s = filter.to_string();
        assert!(s.contains("fontcolor=white"));
    }

    #[test]
    fn test_text_escaping_in_build() {
        let filter = DrawtextBuilder::new("Score: 100%").build();
        let s = filter.to_string();
        assert!(s.contains("text=Score\\: 100%%"));
    }

    // ========== Position tests ==========

    #[test]
    fn test_position_center() {
        let filter = DrawtextBuilder::new("hello")
            .position(Position::Center)
            .build();
        let s = filter.to_string();
        assert!(s.contains("x=(w-text_w)/2"));
        assert!(s.contains("y=(h-text_h)/2"));
    }

    #[test]
    fn test_position_bottom_center() {
        let filter = DrawtextBuilder::new("hello")
            .position(Position::BottomCenter { margin: 10 })
            .build();
        let s = filter.to_string();
        assert!(s.contains("x=(w-text_w)/2"));
        assert!(s.contains("y=h-text_h-10"));
    }

    #[test]
    fn test_position_top_left() {
        let filter = DrawtextBuilder::new("hello")
            .position(Position::TopLeft { margin: 10 })
            .build();
        let s = filter.to_string();
        assert!(s.contains("x=10"));
        assert!(s.contains("y=10"));
    }

    #[test]
    fn test_position_top_right() {
        let filter = DrawtextBuilder::new("hello")
            .position(Position::TopRight { margin: 15 })
            .build();
        let s = filter.to_string();
        assert!(s.contains("x=w-text_w-15"));
        assert!(s.contains("y=15"));
    }

    #[test]
    fn test_position_bottom_left() {
        let filter = DrawtextBuilder::new("hello")
            .position(Position::BottomLeft { margin: 20 })
            .build();
        let s = filter.to_string();
        assert!(s.contains("x=20"));
        assert!(s.contains("y=h-text_h-20"));
    }

    #[test]
    fn test_position_bottom_right() {
        let filter = DrawtextBuilder::new("hello")
            .position(Position::BottomRight { margin: 5 })
            .build();
        let s = filter.to_string();
        assert!(s.contains("x=w-text_w-5"));
        assert!(s.contains("y=h-text_h-5"));
    }

    #[test]
    fn test_position_absolute() {
        let filter = DrawtextBuilder::new("hello")
            .position(Position::Absolute { x: 100, y: 200 })
            .build();
        let s = filter.to_string();
        assert!(s.contains("x=100"));
        assert!(s.contains("y=200"));
    }

    // ========== Shadow tests ==========

    #[test]
    fn test_shadow() {
        let filter = DrawtextBuilder::new("hello").shadow(2, 2, "black").build();
        let s = filter.to_string();
        assert!(s.contains("shadowx=2"));
        assert!(s.contains("shadowy=2"));
        assert!(s.contains("shadowcolor=black"));
    }

    #[test]
    fn test_shadow_offset() {
        let filter = DrawtextBuilder::new("hello")
            .shadow(3, 5, "gray@0.5")
            .build();
        let s = filter.to_string();
        assert!(s.contains("shadowx=3"));
        assert!(s.contains("shadowy=5"));
        assert!(s.contains("shadowcolor=gray@0.5"));
    }

    // ========== Box background tests ==========

    #[test]
    fn test_box_background() {
        let filter = DrawtextBuilder::new("hello")
            .box_background("black@0.5", 5)
            .build();
        let s = filter.to_string();
        assert!(s.contains("box=1"));
        assert!(s.contains("boxcolor=black@0.5"));
        assert!(s.contains("boxborderw=5"));
    }

    #[test]
    fn test_box_background_zero_border() {
        let filter = DrawtextBuilder::new("hello")
            .box_background("blue", 0)
            .build();
        let s = filter.to_string();
        assert!(s.contains("box=1"));
        assert!(s.contains("boxcolor=blue"));
        assert!(s.contains("boxborderw=0"));
    }

    // ========== Alpha tests ==========

    #[test]
    fn test_static_alpha() {
        let filter = DrawtextBuilder::new("hello").alpha(0.5).build();
        let s = filter.to_string();
        assert!(s.contains("alpha='0.5'"));
    }

    #[test]
    fn test_static_alpha_integer() {
        let filter = DrawtextBuilder::new("hello").alpha(1.0).build();
        let s = filter.to_string();
        assert!(s.contains("alpha='1'"));
    }

    #[test]
    fn test_static_alpha_clamped_high() {
        let filter = DrawtextBuilder::new("hello").alpha(1.5).build();
        let s = filter.to_string();
        assert!(s.contains("alpha='1'"));
    }

    #[test]
    fn test_static_alpha_clamped_low() {
        let filter = DrawtextBuilder::new("hello").alpha(-0.5).build();
        let s = filter.to_string();
        assert!(s.contains("alpha='0'"));
    }

    #[test]
    fn test_alpha_fade() {
        let filter = DrawtextBuilder::new("hello")
            .alpha_fade(1.0, 0.5, 5.0, 0.5)
            .build();
        let s = filter.to_string();
        // Verify the expression has the expected nested if/lt structure.
        // The expression engine builds addition trees (1+0.5) rather than
        // pre-computing constants (1.5), which FFmpeg evaluates correctly.
        assert!(s.contains("alpha='if(lt(t,1)"));
        assert!(s.contains("lt(t,1+0.5)"));
        assert!(s.contains("lt(t,5-0.5)"));
    }

    #[test]
    fn test_alpha_fade_integer_times() {
        let filter = DrawtextBuilder::new("hello")
            .alpha_fade(0.0, 1.0, 10.0, 1.0)
            .build();
        let s = filter.to_string();
        assert!(s.contains("alpha='if(lt(t,0)"));
    }

    // ========== Enable expression tests ==========

    #[test]
    fn test_enable_expression() {
        let filter = DrawtextBuilder::new("hello")
            .enable("between(t,3,5)")
            .build();
        let s = filter.to_string();
        assert!(s.contains("enable='between(t,3,5)'"));
    }

    // ========== Combined tests ==========

    #[test]
    fn test_full_builder() {
        let filter = DrawtextBuilder::new("Hello World")
            .font("monospace")
            .fontsize(24)
            .fontcolor("white")
            .position(Position::Center)
            .shadow(2, 2, "black")
            .box_background("black@0.5", 5)
            .alpha(0.8)
            .build();
        let s = filter.to_string();
        assert!(s.starts_with("drawtext="));
        assert!(s.contains("text=Hello World"));
        assert!(s.contains("font=monospace"));
        assert!(s.contains("fontsize=24"));
        assert!(s.contains("fontcolor=white"));
        assert!(s.contains("x=(w-text_w)/2"));
        assert!(s.contains("y=(h-text_h)/2"));
        assert!(s.contains("shadowx=2"));
        assert!(s.contains("box=1"));
        assert!(s.contains("alpha='0.8'"));
    }

    #[test]
    fn test_builder_in_filter_chain() {
        use super::super::filter::{FilterChain, FilterGraph};

        let dt = DrawtextBuilder::new("Title")
            .font("monospace")
            .fontsize(32)
            .fontcolor("white")
            .position(Position::Center)
            .build();

        let graph = FilterGraph::new().chain(
            FilterChain::new()
                .input("0:v")
                .filter(dt)
                .output("text_out"),
        );

        let s = graph.to_string();
        assert!(s.contains("[0:v]drawtext="));
        assert!(s.contains("[text_out]"));
    }

    // ========== Proptest ==========

    use proptest::prelude::*;

    fn arb_position() -> impl Strategy<Value = Position> {
        prop_oneof![
            Just(Position::Center),
            (0u32..100).prop_map(|m| Position::BottomCenter { margin: m }),
            (0u32..100).prop_map(|m| Position::TopLeft { margin: m }),
            (0u32..100).prop_map(|m| Position::TopRight { margin: m }),
            (0u32..100).prop_map(|m| Position::BottomLeft { margin: m }),
            (0u32..100).prop_map(|m| Position::BottomRight { margin: m }),
            (0i32..1920, 0i32..1080).prop_map(|(x, y)| Position::Absolute { x, y }),
        ]
    }

    proptest! {
        /// Property: all drawtext builders produce valid filter strings starting with "drawtext=".
        #[test]
        fn drawtext_starts_with_drawtext(
            text in "[a-zA-Z0-9 ]{1,50}",
            size in 8u32..200,
            pos in arb_position(),
        ) {
            let filter = DrawtextBuilder::new(&text)
                .font("monospace")
                .fontsize(size)
                .position(pos)
                .build();
            let s = filter.to_string();
            prop_assert!(s.starts_with("drawtext="), "Got: {}", s);
            prop_assert!(s.contains("text="), "Missing text param: {}", s);
            prop_assert!(s.contains("fontsize="), "Missing fontsize param: {}", s);
        }

        /// Property: special characters in text are properly escaped.
        #[test]
        fn special_chars_escaped(text in ".*") {
            let escaped = escape_drawtext(&text);
            // No unescaped colons (except after backslash)
            for (i, c) in escaped.chars().enumerate() {
                if c == ':' && i > 0 {
                    let prev: Vec<char> = escaped.chars().collect();
                    prop_assert_eq!(prev[i - 1], '\\', "Unescaped colon in: {}", escaped);
                }
            }
        }
    }
}
