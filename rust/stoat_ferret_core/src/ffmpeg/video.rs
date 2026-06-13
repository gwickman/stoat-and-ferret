//! Video effect filter builders.
//!
//! [`BlurBuilder`] generates FFmpeg gblur/dblur filters with optional automation.
//! [`SharpenBuilder`] generates FFmpeg unsharp masking filters.
//! [`ColorLutBuilder`] generates FFmpeg lut3d filters with bundled preset validation.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::automation::{py_compile_automation, Automation};
use super::filter::Filter;

/// Gaussian or directional blur filter builder with optional automation envelope.
///
/// Gaussian mode (`blur_type="gaussian"`) generates `gblur=sigma={sigma}`.
/// Directional mode (`blur_type="directional"`) generates `dblur=sigma={sigma}`.
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
            None => {
                let filter_name = match self.blur_type.as_str() {
                    "directional" => "dblur",
                    _ => "gblur",
                };
                Ok(Filter::new(filter_name).param("sigma", self.sigma))
            }
            Some(auto) => {
                let expr = py_compile_automation(auto)?;
                Ok(Filter::new(format!("gblur=sigma='{}':eval=frame", expr)))
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

#[cfg(test)]
mod tests {
    use super::*;

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
        assert_eq!(filter.to_string(), "dblur=sigma=3");
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
}
