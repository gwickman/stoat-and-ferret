//! Video effect filter builders.
//!
//! [`BlurBuilder`] generates FFmpeg gblur/dblur filters with optional automation.
//! [`SharpenBuilder`] generates FFmpeg unsharp masking filters.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::automation::{py_compile_automation, Automation};
use super::filter::Filter;

/// Escape commas in FFmpeg filter-option values.
///
/// FFmpeg's filter-graph parser treats `,` as an option separator inside a
/// filter's argument list.  Automation expressions like `if(lt(t,0),0,1)`
/// contain bare commas that break FFmpeg parsing when embedded as option
/// values.  Replace each `,` with `\,` before format! substitution.
pub(crate) fn escape_for_filter(expr: &str) -> String {
    expr.replace(',', r"\,")
}

/// Gaussian or directional blur filter builder with optional automation envelope.
///
/// Gaussian mode (`blur_type="gaussian"`) generates `gblur=sigma={sigma}`.
/// Directional mode (`blur_type="directional"`) generates `dblur=radius={sigma_rounded}`.
/// When automation is present, build() produces `gblur=sigma='{expr}':eval=frame`
/// using the compiled expression from `compile_automation`.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct BlurBuilder {
    sigma: f32,
    blur_type: String,
    automation: Option<Automation>,
}

#[pymethods]
impl BlurBuilder {
    #[new]
    pub fn py_new(sigma: f32, blur_type: &str) -> PyResult<Self> {
        if sigma <= 0.0 {
            return Err(PyValueError::new_err("sigma must be > 0"));
        }
        match blur_type {
            "gaussian" | "directional" => {}
            _ => {
                return Err(PyValueError::new_err(
                    "blur_type must be 'gaussian' or 'directional'",
                ))
            }
        }
        Ok(Self {
            sigma,
            blur_type: blur_type.to_string(),
            automation: None,
        })
    }

    #[pyo3(name = "with_automation")]
    pub fn py_with_automation(&self, automation: Automation) -> Self {
        Self {
            automation: Some(automation),
            ..self.clone()
        }
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        match &self.automation {
            None => match self.blur_type.as_str() {
                "directional" => {
                    Ok(Filter::new("dblur").param("radius", self.sigma.round() as i32))
                }
                _ => Ok(Filter::new("gblur").param("sigma", self.sigma)),
            },
            Some(auto) => {
                let expr = py_compile_automation(auto)?;
                let escaped = escape_for_filter(&expr);
                Ok(Filter::new(format!("gblur=sigma='{}':eval=frame", escaped)))
            }
        }
    }
}

/// Unsharp masking filter builder for image sharpening.
///
/// Generates `unsharp=luma_msize_x=5:luma_msize_y=5:luma_amount={amount}`.
/// `amount` must be > 0.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct SharpenBuilder {
    amount: f32,
}

#[pymethods]
impl SharpenBuilder {
    #[new]
    pub fn py_new(amount: f32) -> PyResult<Self> {
        if amount <= 0.0 {
            return Err(PyValueError::new_err("amount must be > 0"));
        }
        Ok(Self { amount })
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        Ok(Filter::new("unsharp")
            .param("luma_msize_x", 5)
            .param("luma_msize_y", 5)
            .param("luma_amount", self.amount))
    }
}

/// Bundled LUT preset names. The `identity` preset is mandatory for unit testing.
const BUNDLED_PRESETS: &[&str] = &["calming_teal", "warm_fade", "identity"];

/// 3D LUT color grading filter builder with bundled preset validation.
///
/// Validates `preset` against a fixed set of bundled preset names.
/// `build()` produces `lut3d=file={preset}.cube` using the preset name as a
/// logical filename; callers resolve the bundled asset path to a real file.
/// `preset_name()` exposes the validated name for path resolution.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ColorLutBuilder {
    preset: String,
}

#[pymethods]
impl ColorLutBuilder {
    #[new]
    pub fn py_new(preset: &str) -> PyResult<Self> {
        if !BUNDLED_PRESETS.contains(&preset) {
            return Err(PyValueError::new_err(format!(
                "Unknown LUT preset: {preset}"
            )));
        }
        Ok(Self {
            preset: preset.to_string(),
        })
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        Ok(Filter::new("lut3d").param("file", format!("{}.cube", self.preset)))
    }

    #[pyo3(name = "preset_name")]
    pub fn py_preset_name(&self) -> String {
        self.preset.clone()
    }
}

/// Opacity filter builder using `colorchannelmixer` alpha channel adjustment.
///
/// Static mode generates `format=rgba,colorchannelmixer=aa={opacity}`.
/// When automation is present, `build()` produces
/// `format=rgba,colorchannelmixer=aa='{expr}':eval=frame`.
///
/// `opacity` must be in [0.0, 1.0] (0 = transparent, 1 = opaque).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct OpacityBuilder {
    opacity: f32,
    automation: Option<Automation>,
}

#[pymethods]
impl OpacityBuilder {
    #[new]
    pub fn py_new(opacity: f32) -> PyResult<Self> {
        if !(0.0..=1.0).contains(&opacity) {
            return Err(PyValueError::new_err("opacity must be in [0.0, 1.0]"));
        }
        Ok(Self {
            opacity,
            automation: None,
        })
    }

    #[pyo3(name = "with_automation")]
    pub fn py_with_automation(&self, automation: Automation) -> Self {
        Self {
            automation: Some(automation),
            ..self.clone()
        }
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        match &self.automation {
            None => Ok(Filter::new("format=rgba,colorchannelmixer").param("aa", self.opacity)),
            Some(auto) => {
                let expr = py_compile_automation(auto)?;
                let escaped = escape_for_filter(&expr);
                Ok(Filter::new(format!(
                    "format=rgba,colorchannelmixer=aa='{}':eval=frame",
                    escaped
                )))
            }
        }
    }
}

/// Scale filter builder with even-dimension trunc rounding.
///
/// Static mode generates `scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2`.
/// When automation is present, `build()` produces
/// `scale=trunc(iw*('{expr}')/2)*2:trunc(ih*('{expr}')/2)*2:eval=frame`.
///
/// `scale` must be > 0.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ScaleBuilder {
    scale: f32,
    automation: Option<Automation>,
}

#[pymethods]
impl ScaleBuilder {
    #[new]
    pub fn py_new(scale: f32) -> PyResult<Self> {
        if scale <= 0.0 {
            return Err(PyValueError::new_err("scale must be > 0"));
        }
        Ok(Self {
            scale,
            automation: None,
        })
    }

    #[pyo3(name = "with_automation")]
    pub fn py_with_automation(&self, automation: Automation) -> Self {
        Self {
            automation: Some(automation),
            ..self.clone()
        }
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        match &self.automation {
            None => {
                let w = format!("trunc(iw*{}/2)*2", self.scale);
                let h = format!("trunc(ih*{}/2)*2", self.scale);
                Ok(Filter::new("scale").param("w", w).param("h", h))
            }
            Some(auto) => {
                let expr = py_compile_automation(auto)?;
                let escaped = escape_for_filter(&expr);
                Ok(Filter::new(format!(
                    "scale=trunc(iw*('{}')/2)*2:trunc(ih*('{}')/2)*2:eval=frame",
                    escaped, escaped
                )))
            }
        }
    }
}

/// Parses a CSS `#RRGGBB` or `0xRRGGBB` color string and returns it in `0xRRGGBB` format.
///
/// Accepts `#RRGGBB` (6 hex digits after `#`) and `0xRRGGBB` passthrough.
/// Returns `PyValueError` for any other format.
fn parse_color_to_hex(color: &str) -> PyResult<String> {
    if let Some(hex) = color.strip_prefix('#') {
        if hex.len() == 6 && hex.chars().all(|c| c.is_ascii_hexdigit()) {
            return Ok(format!("0x{}", hex.to_uppercase()));
        }
        return Err(PyValueError::new_err(format!(
            "Invalid color format: '{color}'. Expected #RRGGBB or a CSS color name."
        )));
    }
    if let Some(hex) = color
        .strip_prefix("0x")
        .or_else(|| color.strip_prefix("0X"))
    {
        if hex.len() == 6 && hex.chars().all(|c| c.is_ascii_hexdigit()) {
            return Ok(format!("0x{}", hex.to_uppercase()));
        }
        return Err(PyValueError::new_err(format!(
            "Invalid color format: '{color}'. Expected #RRGGBB or a CSS color name."
        )));
    }
    // CSS named colors: validate as a non-empty alphabetic-only string
    let trimmed = color.trim();
    if !trimmed.is_empty() && trimmed.chars().all(|c| c.is_ascii_alphabetic()) {
        return Ok(trimmed.to_lowercase());
    }
    Err(PyValueError::new_err(format!(
        "Invalid color format: '{color}'. Expected #RRGGBB or a CSS color name."
    )))
}

/// Chroma-key (green-screen) filter builder.
///
/// `build()` produces `chromakey=color={hex}:similarity={similarity}`.
/// Keyed pixels become transparent (not black).
/// Color accepts `#RRGGBB` CSS hex or a CSS color name (e.g. `"green"`).
/// `similarity` must be in [0.0, 1.0] (default 0.1).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ChromaKeyBuilder {
    color: String,
    similarity: f32,
}

#[pymethods]
impl ChromaKeyBuilder {
    #[new]
    #[pyo3(signature = (color, similarity=None))]
    pub fn py_new(color: &str, similarity: Option<f32>) -> PyResult<Self> {
        let hex = parse_color_to_hex(color)?;
        let sim = similarity.unwrap_or(0.1);
        if !(0.0..=1.0).contains(&sim) {
            return Err(PyValueError::new_err("similarity must be in [0.0, 1.0]"));
        }
        Ok(Self {
            color: hex,
            similarity: sim,
        })
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        Ok(Filter::new("chromakey")
            .param("color", &self.color)
            .param("similarity", self.similarity))
    }
}

/// Color-key filter builder.
///
/// `build()` produces `colorkey=color={hex}:similarity={similarity}`.
/// Color accepts `#RRGGBB` CSS hex or a CSS color name.
/// `similarity` must be in [0.0, 1.0] (default 0.1).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ColorKeyBuilder {
    color: String,
    similarity: f32,
}

#[pymethods]
impl ColorKeyBuilder {
    #[new]
    #[pyo3(signature = (color, similarity=None))]
    pub fn py_new(color: &str, similarity: Option<f32>) -> PyResult<Self> {
        let hex = parse_color_to_hex(color)?;
        let sim = similarity.unwrap_or(0.1);
        if !(0.0..=1.0).contains(&sim) {
            return Err(PyValueError::new_err("similarity must be in [0.0, 1.0]"));
        }
        Ok(Self {
            color: hex,
            similarity: sim,
        })
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        Ok(Filter::new("colorkey")
            .param("color", &self.color)
            .param("similarity", self.similarity))
    }
}

/// Gradient generator source filter builder using FFmpeg `gradients` lavfi source.
///
/// `build()` produces `gradients=s={w}x{h}:c0={color1}:c1={color2}:d={duration}`.
/// Colors accept `#RRGGBB` CSS hex or a CSS color name (e.g. `"blue"`).
/// `duration` must be > 0. `width` and `height` default to 1920×1080.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct GradientGeneratorBuilder {
    color1: String,
    color2: String,
    width: u32,
    height: u32,
    duration: f64,
}

#[pymethods]
impl GradientGeneratorBuilder {
    #[new]
    #[pyo3(signature = (color1, color2, duration, width=None, height=None))]
    pub fn py_new(
        color1: &str,
        color2: &str,
        duration: f64,
        width: Option<u32>,
        height: Option<u32>,
    ) -> PyResult<Self> {
        let c1 = parse_color_to_hex(color1)?;
        let c2 = parse_color_to_hex(color2)?;
        if duration <= 0.0 {
            return Err(PyValueError::new_err("duration must be > 0"));
        }
        let w = width.unwrap_or(1920);
        let h = height.unwrap_or(1080);
        if w == 0 {
            return Err(PyValueError::new_err("width must be > 0"));
        }
        if h == 0 {
            return Err(PyValueError::new_err("height must be > 0"));
        }
        Ok(Self {
            color1: c1,
            color2: c2,
            width: w,
            height: h,
            duration,
        })
    }

    pub fn build(&self) -> PyResult<Filter> {
        Ok(Filter::new(format!(
            "gradients=s={}x{}:c0={}:c1={}:d={}",
            self.width, self.height, self.color1, self.color2, self.duration
        )))
    }
}

/// Noise/pattern generator source filter builder using FFmpeg `cellauto` lavfi source.
///
/// `build()` produces `cellauto=s={w}x{h}`.
/// `duration` must be > 0 (validated at construction; not emitted — duration is
/// controlled via the FFmpeg `-t` flag at the command level).
/// `width` and `height` default to 1920×1080.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct NoiseGeneratorBuilder {
    width: u32,
    height: u32,
    /// Retained for API-level validation; not emitted in the filter string.
    #[allow(dead_code)]
    duration: f64,
}

#[pymethods]
impl NoiseGeneratorBuilder {
    #[new]
    #[pyo3(signature = (duration, width=None, height=None))]
    pub fn py_new(duration: f64, width: Option<u32>, height: Option<u32>) -> PyResult<Self> {
        if duration <= 0.0 {
            return Err(PyValueError::new_err("duration must be > 0"));
        }
        let w = width.unwrap_or(1920);
        let h = height.unwrap_or(1080);
        if w == 0 {
            return Err(PyValueError::new_err("width must be > 0"));
        }
        if h == 0 {
            return Err(PyValueError::new_err("height must be > 0"));
        }
        Ok(Self {
            width: w,
            height: h,
            duration,
        })
    }

    pub fn build(&self) -> PyResult<Filter> {
        Ok(Filter::new(format!(
            "cellauto=s={}x{}",
            self.width, self.height
        )))
    }
}

/// Lens distortion filter builder using the FFmpeg `lenscorrection` filter.
///
/// `k1` and `k2` are barrel/pincushion distortion coefficients in [-1.0, 1.0].
/// Negative values produce barrel distortion; positive values produce pincushion.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct LensDistortBuilder {
    k1: f64,
    k2: f64,
}

#[pymethods]
impl LensDistortBuilder {
    #[new]
    pub fn py_new(k1: f64, k2: f64) -> PyResult<Self> {
        if !(-1.0..=1.0).contains(&k1) {
            return Err(PyValueError::new_err("k1 must be in [-1.0, 1.0]"));
        }
        if !(-1.0..=1.0).contains(&k2) {
            return Err(PyValueError::new_err("k2 must be in [-1.0, 1.0]"));
        }
        Ok(Self { k1, k2 })
    }

    pub fn build(&self) -> PyResult<Filter> {
        Ok(Filter::new("lenscorrection")
            .param("k1", self.k1)
            .param("k2", self.k2))
    }
}

/// Chromatic aberration filter builder using the FFmpeg `rgbashift` filter.
///
/// Shifts each RGB channel independently by configurable horizontal/vertical pixel offsets.
/// All parameters are in the range `[-255, 255]`; all default to 0 (pass-through).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct ChromaticAberrationBuilder {
    rx: i32,
    ry: i32,
    gx: i32,
    gy: i32,
    bx: i32,
    by: i32,
}

#[pymethods]
impl ChromaticAberrationBuilder {
    #[new]
    pub fn py_new(rx: i32, ry: i32, gx: i32, gy: i32, bx: i32, by: i32) -> PyResult<Self> {
        for &v in &[rx, ry, gx, gy, bx, by] {
            if !(-255..=255).contains(&v) {
                return Err(PyValueError::new_err("shift values must be in [-255, 255]"));
            }
        }
        Ok(Self { rx, ry, gx, gy, bx, by })
    }

    #[pyo3(name = "build")]
    pub fn py_build(&self) -> PyResult<Filter> {
        Ok(Filter::new("rgbashift")
            .param("rh", self.rx)
            .param("rv", self.ry)
            .param("gh", self.gx)
            .param("gv", self.gy)
            .param("bh", self.bx)
            .param("bv", self.by))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_escape_for_filter_commas() {
        assert_eq!(escape_for_filter("if(lt(t,0),0,1)"), r"if(lt(t\,0)\,0\,1)");
        assert_eq!(escape_for_filter("no_commas"), "no_commas");
    }

    #[test]
    fn test_blur_gaussian_default() {
        let builder = BlurBuilder::py_new(2.5, "gaussian").unwrap();
        let filter = builder.py_build().unwrap();
        assert_eq!(filter.to_string(), "gblur=sigma=2.5");
    }

    #[test]
    fn test_blur_directional() {
        let builder = BlurBuilder::py_new(3.0, "directional").unwrap();
        let filter = builder.py_build().unwrap();
        assert_eq!(filter.to_string(), "dblur=radius=3");
    }

    #[test]
    fn test_blur_invalid_sigma() {
        assert!(BlurBuilder::py_new(0.0, "gaussian").is_err());
        assert!(BlurBuilder::py_new(-1.0, "gaussian").is_err());
    }

    #[test]
    fn test_blur_invalid_type() {
        assert!(BlurBuilder::py_new(1.0, "box").is_err());
    }

    #[test]
    fn test_sharpen_default() {
        let builder = SharpenBuilder::py_new(1.5).unwrap();
        let filter = builder.py_build().unwrap();
        let s = filter.to_string();
        assert!(s.starts_with("unsharp="), "expected unsharp filter: {s}");
        assert!(s.contains("luma_amount=1.5"), "expected luma_amount: {s}");
    }

    #[test]
    fn test_sharpen_invalid_amount() {
        assert!(SharpenBuilder::py_new(0.0).is_err());
        assert!(SharpenBuilder::py_new(-1.0).is_err());
    }

    #[test]
    fn test_blur_with_automation_stores_envelope() {
        let auto = Automation {
            default: 1.0,
            keyframes: vec![
                super::super::automation::Keyframe {
                    t: 0.0,
                    value: 1.0,
                    curve: "Linear".to_string(),
                },
                super::super::automation::Keyframe {
                    t: 5.0,
                    value: 5.0,
                    curve: "Linear".to_string(),
                },
            ],
        };
        let builder = BlurBuilder::py_new(2.0, "gaussian").unwrap();
        let with_auto = builder.py_with_automation(auto);
        assert!(with_auto.automation.is_some());
    }

    #[test]
    fn test_blur_build_with_automation_contains_eval_frame() {
        let auto = Automation {
            default: 1.0,
            keyframes: vec![
                super::super::automation::Keyframe {
                    t: 0.0,
                    value: 1.0,
                    curve: "Linear".to_string(),
                },
                super::super::automation::Keyframe {
                    t: 5.0,
                    value: 5.0,
                    curve: "Linear".to_string(),
                },
            ],
        };
        let builder = BlurBuilder::py_new(2.0, "gaussian")
            .unwrap()
            .py_with_automation(auto);
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("eval=frame"),
            "expected eval=frame in: {filter_str}"
        );
        assert!(
            filter_str.contains("gblur"),
            "expected gblur in: {filter_str}"
        );
    }

    #[test]
    fn test_color_lut_valid_presets() {
        assert!(ColorLutBuilder::py_new("identity").is_ok());
        assert!(ColorLutBuilder::py_new("calming_teal").is_ok());
        assert!(ColorLutBuilder::py_new("warm_fade").is_ok());
    }

    #[test]
    fn test_color_lut_invalid_preset() {
        assert!(ColorLutBuilder::py_new("unknown").is_err());
        assert!(ColorLutBuilder::py_new("").is_err());
    }

    #[test]
    fn test_color_lut_build_contains_lut3d() {
        let builder = ColorLutBuilder::py_new("identity").unwrap();
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.starts_with("lut3d"),
            "expected lut3d prefix in: {filter_str}"
        );
        assert!(
            filter_str.contains("identity.cube"),
            "expected identity.cube in: {filter_str}"
        );
    }

    #[test]
    fn test_color_lut_deterministic() {
        let b1 = ColorLutBuilder::py_new("identity").unwrap();
        let b2 = ColorLutBuilder::py_new("identity").unwrap();
        assert_eq!(
            b1.py_build().unwrap().to_string(),
            b2.py_build().unwrap().to_string()
        );
    }

    #[test]
    fn test_color_lut_preset_name_getter() {
        let builder = ColorLutBuilder::py_new("calming_teal").unwrap();
        assert_eq!(builder.py_preset_name(), "calming_teal");
    }

    #[test]
    fn test_opacity_valid_range() {
        assert!(OpacityBuilder::py_new(0.0).is_ok());
        assert!(OpacityBuilder::py_new(0.5).is_ok());
        assert!(OpacityBuilder::py_new(1.0).is_ok());
    }

    #[test]
    fn test_opacity_invalid_range() {
        assert!(OpacityBuilder::py_new(-0.1).is_err());
        assert!(OpacityBuilder::py_new(1.1).is_err());
    }

    #[test]
    fn test_opacity_static_build() {
        let builder = OpacityBuilder::py_new(0.5).unwrap();
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("colorchannelmixer"),
            "expected colorchannelmixer in: {filter_str}"
        );
        assert!(
            filter_str.contains("aa=0.5"),
            "expected aa=0.5 in: {filter_str}"
        );
    }

    #[test]
    fn test_opacity_with_automation_stores_envelope() {
        let auto = Automation {
            default: 0.5,
            keyframes: vec![
                super::super::automation::Keyframe {
                    t: 0.0,
                    value: 0.0,
                    curve: "Linear".to_string(),
                },
                super::super::automation::Keyframe {
                    t: 5.0,
                    value: 1.0,
                    curve: "Linear".to_string(),
                },
            ],
        };
        let builder = OpacityBuilder::py_new(0.5).unwrap();
        let with_auto = builder.py_with_automation(auto);
        assert!(with_auto.automation.is_some());
    }

    #[test]
    fn test_opacity_build_with_automation_contains_eval_frame() {
        let auto = Automation {
            default: 0.5,
            keyframes: vec![
                super::super::automation::Keyframe {
                    t: 0.0,
                    value: 0.0,
                    curve: "Linear".to_string(),
                },
                super::super::automation::Keyframe {
                    t: 5.0,
                    value: 1.0,
                    curve: "Linear".to_string(),
                },
            ],
        };
        let builder = OpacityBuilder::py_new(0.5)
            .unwrap()
            .py_with_automation(auto);
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("eval=frame"),
            "expected eval=frame in: {filter_str}"
        );
        assert!(
            filter_str.contains("colorchannelmixer"),
            "expected colorchannelmixer in: {filter_str}"
        );
    }

    #[test]
    fn test_scale_valid() {
        assert!(ScaleBuilder::py_new(1.0).is_ok());
        assert!(ScaleBuilder::py_new(0.5).is_ok());
        assert!(ScaleBuilder::py_new(2.0).is_ok());
    }

    #[test]
    fn test_scale_invalid() {
        assert!(ScaleBuilder::py_new(0.0).is_err());
        assert!(ScaleBuilder::py_new(-1.0).is_err());
    }

    #[test]
    fn test_scale_static_build() {
        let builder = ScaleBuilder::py_new(1.5).unwrap();
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.starts_with("scale="),
            "expected scale= prefix in: {filter_str}"
        );
        assert!(
            filter_str.contains("trunc(iw"),
            "expected trunc(iw in: {filter_str}"
        );
    }

    #[test]
    fn test_scale_with_automation_stores_envelope() {
        let auto = Automation {
            default: 1.0,
            keyframes: vec![
                super::super::automation::Keyframe {
                    t: 0.0,
                    value: 1.0,
                    curve: "Linear".to_string(),
                },
                super::super::automation::Keyframe {
                    t: 5.0,
                    value: 2.0,
                    curve: "Linear".to_string(),
                },
            ],
        };
        let builder = ScaleBuilder::py_new(1.0).unwrap();
        let with_auto = builder.py_with_automation(auto);
        assert!(with_auto.automation.is_some());
    }

    #[test]
    fn test_scale_build_with_automation_contains_eval_frame() {
        let auto = Automation {
            default: 1.0,
            keyframes: vec![
                super::super::automation::Keyframe {
                    t: 0.0,
                    value: 1.0,
                    curve: "Linear".to_string(),
                },
                super::super::automation::Keyframe {
                    t: 5.0,
                    value: 2.0,
                    curve: "Linear".to_string(),
                },
            ],
        };
        let builder = ScaleBuilder::py_new(1.0).unwrap().py_with_automation(auto);
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("eval=frame"),
            "expected eval=frame in: {filter_str}"
        );
        assert!(
            filter_str.contains("scale="),
            "expected scale= in: {filter_str}"
        );
    }

    // -- parse_color_to_hex --

    #[test]
    fn test_parse_color_css_hex() {
        let result = parse_color_to_hex("#00FF00").unwrap();
        assert_eq!(result, "0x00FF00");
    }

    #[test]
    fn test_parse_color_lowercase_hex() {
        let result = parse_color_to_hex("#00ff00").unwrap();
        assert_eq!(result, "0x00FF00");
    }

    #[test]
    fn test_parse_color_0x_passthrough() {
        let result = parse_color_to_hex("0x00FF00").unwrap();
        assert_eq!(result, "0x00FF00");
    }

    #[test]
    fn test_parse_color_named() {
        let result = parse_color_to_hex("green").unwrap();
        assert_eq!(result, "green");
    }

    #[test]
    fn test_parse_color_invalid() {
        assert!(parse_color_to_hex("#GGGGGG").is_err());
        assert!(parse_color_to_hex("#1234").is_err());
        assert!(parse_color_to_hex("123456").is_err());
        assert!(parse_color_to_hex("").is_err());
    }

    // -- ChromaKeyBuilder --

    #[test]
    fn test_chroma_key_hex_color() {
        let builder = ChromaKeyBuilder::py_new("#00FF00", None).unwrap();
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("chromakey="),
            "expected chromakey: {filter_str}"
        );
        assert!(
            filter_str.contains("0x00FF00"),
            "expected hex color: {filter_str}"
        );
        assert!(
            filter_str.contains("similarity=0.1"),
            "expected default similarity: {filter_str}"
        );
    }

    #[test]
    fn test_chroma_key_named_color() {
        let builder = ChromaKeyBuilder::py_new("green", Some(0.3)).unwrap();
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("color=green"),
            "expected named color: {filter_str}"
        );
        assert!(
            filter_str.contains("similarity=0.3"),
            "expected custom similarity: {filter_str}"
        );
    }

    #[test]
    fn test_chroma_key_invalid_color() {
        assert!(ChromaKeyBuilder::py_new("notacolor123", None).is_err());
        assert!(ChromaKeyBuilder::py_new("#GGGGGG", None).is_err());
    }

    #[test]
    fn test_chroma_key_invalid_similarity() {
        assert!(ChromaKeyBuilder::py_new("#00FF00", Some(-0.1)).is_err());
        assert!(ChromaKeyBuilder::py_new("#00FF00", Some(1.1)).is_err());
    }

    #[test]
    fn test_chroma_key_similarity_bounds() {
        assert!(ChromaKeyBuilder::py_new("#00FF00", Some(0.0)).is_ok());
        assert!(ChromaKeyBuilder::py_new("#00FF00", Some(1.0)).is_ok());
    }

    // -- ColorKeyBuilder --

    #[test]
    fn test_color_key_hex_color() {
        let builder = ColorKeyBuilder::py_new("#FF0000", None).unwrap();
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("colorkey="),
            "expected colorkey: {filter_str}"
        );
        assert!(
            filter_str.contains("0xFF0000"),
            "expected hex color: {filter_str}"
        );
    }

    #[test]
    fn test_color_key_named_color() {
        let builder = ColorKeyBuilder::py_new("red", Some(0.2)).unwrap();
        let filter_str = builder.py_build().unwrap().to_string();
        assert!(
            filter_str.contains("color=red"),
            "expected named color: {filter_str}"
        );
    }

    #[test]
    fn test_color_key_invalid_similarity() {
        assert!(ColorKeyBuilder::py_new("#FF0000", Some(2.0)).is_err());
    }

    // -- LensDistortBuilder --

    // -- GradientGeneratorBuilder --

    #[test]
    fn test_gradient_generator_valid() {
        let b = GradientGeneratorBuilder::py_new("black", "white", 5.0, None, None).unwrap();
        let s = b.build().unwrap().to_string();
        assert!(
            s.starts_with("gradients="),
            "expected gradients= prefix: {s}"
        );
        assert!(s.contains("c0="), "expected c0= in: {s}");
        assert!(s.contains("c1="), "expected c1= in: {s}");
        assert!(s.contains("d=5"), "expected d=5 in: {s}");
    }

    #[test]
    fn test_gradient_generator_hex_colors() {
        let b = GradientGeneratorBuilder::py_new("#000080", "#FF8C00", 10.0, None, None).unwrap();
        let s = b.build().unwrap().to_string();
        assert!(s.contains("0x000080"), "expected 0x000080 in: {s}");
        assert!(s.contains("0xFF8C00"), "expected 0xFF8C00 in: {s}");
    }

    #[test]
    fn test_gradient_generator_custom_size() {
        let b =
            GradientGeneratorBuilder::py_new("black", "white", 3.0, Some(640), Some(480)).unwrap();
        let s = b.build().unwrap().to_string();
        assert!(s.contains("640x480"), "expected 640x480 in: {s}");
    }

    #[test]
    fn test_gradient_generator_invalid_duration() {
        assert!(GradientGeneratorBuilder::py_new("black", "white", 0.0, None, None).is_err());
        assert!(GradientGeneratorBuilder::py_new("black", "white", -1.0, None, None).is_err());
    }

    #[test]
    fn test_gradient_generator_invalid_color() {
        assert!(
            GradientGeneratorBuilder::py_new("notacolor123", "white", 5.0, None, None).is_err()
        );
    }

    #[test]
    fn test_gradient_generator_zero_size() {
        assert!(GradientGeneratorBuilder::py_new("black", "white", 5.0, Some(0), None).is_err());
        assert!(GradientGeneratorBuilder::py_new("black", "white", 5.0, None, Some(0)).is_err());
    }

    #[test]
    fn test_gradient_generator_deterministic() {
        let b1 = GradientGeneratorBuilder::py_new("black", "white", 5.0, None, None).unwrap();
        let b2 = GradientGeneratorBuilder::py_new("black", "white", 5.0, None, None).unwrap();
        assert_eq!(
            b1.build().unwrap().to_string(),
            b2.build().unwrap().to_string()
        );
    }

    // -- NoiseGeneratorBuilder --

    #[test]
    fn test_noise_generator_valid() {
        let b = NoiseGeneratorBuilder::py_new(5.0, None, None).unwrap();
        let s = b.build().unwrap().to_string();
        assert!(s.starts_with("cellauto="), "expected cellauto= prefix: {s}");
        assert!(!s.contains("d="), "expected no d= in: {s}");
    }

    #[test]
    fn test_noise_generator_custom_size() {
        let b = NoiseGeneratorBuilder::py_new(3.0, Some(640), Some(480)).unwrap();
        let s = b.build().unwrap().to_string();
        assert!(s.contains("640x480"), "expected 640x480 in: {s}");
    }

    #[test]
    fn test_noise_generator_default_size() {
        let b = NoiseGeneratorBuilder::py_new(5.0, None, None).unwrap();
        let s = b.build().unwrap().to_string();
        assert!(s.contains("1920x1080"), "expected 1920x1080 in: {s}");
    }

    #[test]
    fn test_noise_generator_invalid_duration() {
        assert!(NoiseGeneratorBuilder::py_new(0.0, None, None).is_err());
        assert!(NoiseGeneratorBuilder::py_new(-1.0, None, None).is_err());
    }

    #[test]
    fn test_noise_generator_zero_size() {
        assert!(NoiseGeneratorBuilder::py_new(5.0, Some(0), None).is_err());
        assert!(NoiseGeneratorBuilder::py_new(5.0, None, Some(0)).is_err());
    }

    #[test]
    fn test_noise_generator_deterministic() {
        let b1 = NoiseGeneratorBuilder::py_new(5.0, None, None).unwrap();
        let b2 = NoiseGeneratorBuilder::py_new(5.0, None, None).unwrap();
        assert_eq!(
            b1.build().unwrap().to_string(),
            b2.build().unwrap().to_string()
        );
    }

    #[test]
    fn test_lens_distort_valid_construction() {
        assert!(LensDistortBuilder::py_new(0.0, 0.0).is_ok());
        assert!(LensDistortBuilder::py_new(-1.0, 1.0).is_ok());
        assert!(LensDistortBuilder::py_new(0.5, -0.5).is_ok());
    }

    #[test]
    fn test_lens_distort_invalid_k1() {
        assert!(LensDistortBuilder::py_new(1.1, 0.0).is_err());
        assert!(LensDistortBuilder::py_new(-1.1, 0.0).is_err());
    }

    #[test]
    fn test_lens_distort_invalid_k2() {
        assert!(LensDistortBuilder::py_new(0.0, 1.1).is_err());
        assert!(LensDistortBuilder::py_new(0.0, -1.1).is_err());
    }

    #[test]
    fn test_lens_distort_build_output() {
        let builder = LensDistortBuilder::py_new(0.3, -0.2).unwrap();
        let filter_str = builder.build().unwrap().to_string();
        assert!(
            filter_str.starts_with("lenscorrection="),
            "expected lenscorrection= prefix in: {filter_str}"
        );
        assert!(filter_str.contains("k1="), "expected k1= in: {filter_str}");
        assert!(filter_str.contains("k2="), "expected k2= in: {filter_str}");
    }

    #[test]
    fn test_lens_distort_deterministic() {
        let b1 = LensDistortBuilder::py_new(0.1, 0.2).unwrap();
        let b2 = LensDistortBuilder::py_new(0.1, 0.2).unwrap();
        assert_eq!(
            b1.build().unwrap().to_string(),
            b2.build().unwrap().to_string()
        );
    }
}
