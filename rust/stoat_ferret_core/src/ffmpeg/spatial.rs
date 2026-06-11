//! Spatial audio filter builders.
//!
//! [`PanBuilder`] generates FFmpeg stereo pan filters for static positioning
//! or time-varying positioning via automation envelopes.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::automation::{py_compile_automation, Automation};
use super::filter::Filter;

fn gain_to_string(v: f32) -> String {
    let s = format!("{v:.4}");
    let s = s.trim_end_matches('0');
    s.trim_end_matches('.').to_string()
}

/// Stereo pan position builder with optional automation envelope.
///
/// Static mode generates `pan=stereo|c0=L*c0|c1=R*c1`.
/// Automated mode generates `aeval=exprs=...:eval=frame` (LRN-583: eval=frame mandatory).
/// Pan position is clamped to [-1.0, 1.0] (LRN-597).
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct PanBuilder {
    position: f32,
    automation: Option<Automation>,
}

#[pymethods]
impl PanBuilder {
    #[new]
    pub fn py_new(position: f32) -> Self {
        Self {
            position: position.clamp(-1.0, 1.0),
            automation: None,
        }
    }

    pub fn with_automation(&self, automation: Automation) -> Self {
        Self {
            position: self.position,
            automation: Some(automation),
        }
    }

    pub fn build(&self) -> PyResult<Filter> {
        match &self.automation {
            None => {
                let pos = self.position;
                let left = (1.0_f32 - pos).max(0.0);
                let right = (1.0_f32 + pos).max(0.0);
                Ok(Filter::new(format!(
                    "pan=stereo|c0={}*c0|c1={}*c1",
                    gain_to_string(left),
                    gain_to_string(right)
                )))
            }
            Some(auto) => {
                let pos_expr = py_compile_automation(auto)?;
                let exprs = format!(
                    "max(0\\,1-({pos_expr}))*c0|max(0\\,1+({pos_expr}))*c1"
                );
                Ok(Filter::new(format!("aeval=exprs={exprs}:eval=frame")))
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_position_clamped_above_max() {
        let b = PanBuilder::py_new(2.0);
        assert_eq!(b.position, 1.0);
    }

    #[test]
    fn test_position_clamped_below_min() {
        let b = PanBuilder::py_new(-2.0);
        assert_eq!(b.position, -1.0);
    }

    #[test]
    fn test_position_at_max_boundary_unchanged() {
        let b = PanBuilder::py_new(1.0);
        assert_eq!(b.position, 1.0);
    }

    #[test]
    fn test_position_at_min_boundary_unchanged() {
        let b = PanBuilder::py_new(-1.0);
        assert_eq!(b.position, -1.0);
    }

    #[test]
    fn test_static_center_pan_filter_prefix() {
        let b = PanBuilder::py_new(0.0);
        let s = b.build().unwrap().to_string();
        assert!(s.starts_with("pan=stereo|"), "expected pan=stereo| prefix, got: {s}");
    }

    #[test]
    fn test_static_center_equal_gains() {
        let b = PanBuilder::py_new(0.0);
        let s = b.build().unwrap().to_string();
        assert!(s.contains("c0=1*c0"), "expected c0=1*c0 at center, got: {s}");
        assert!(s.contains("c1=1*c1"), "expected c1=1*c1 at center, got: {s}");
    }

    #[test]
    fn test_static_full_right_zeroes_left_channel() {
        let b = PanBuilder::py_new(1.0);
        let s = b.build().unwrap().to_string();
        assert!(s.contains("c0=0*c0"), "expected c0=0*c0 at full right, got: {s}");
    }

    #[test]
    fn test_static_full_left_zeroes_right_channel() {
        let b = PanBuilder::py_new(-1.0);
        let s = b.build().unwrap().to_string();
        assert!(s.contains("c1=0*c1"), "expected c1=0*c1 at full left, got: {s}");
    }

    #[test]
    fn test_automated_build_contains_eval_frame() {
        use super::super::automation::{Automation, Keyframe};
        let auto = Automation {
            default: 0.0,
            keyframes: vec![
                Keyframe { t: 0.0, value: -0.5, curve: "Linear".to_string() },
                Keyframe { t: 1.0, value: 0.5, curve: "Linear".to_string() },
            ],
        };
        let b = PanBuilder::py_new(0.0).with_automation(auto);
        let s = b.build().unwrap().to_string();
        assert!(s.contains("eval=frame"), "eval=frame must be present (LRN-583), got: {s}");
        assert!(s.starts_with("aeval="), "expected aeval filter for automation, got: {s}");
    }
}
