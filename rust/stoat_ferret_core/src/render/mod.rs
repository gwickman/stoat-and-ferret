//! Render plan builder for multi-clip composition.
//!
//! Provides `build_render_plan()` to decompose composition data into ordered
//! `RenderSegment`s with frame counts and cost estimates, plus
//! `validate_render_settings()` for pre-flight validation of output parameters.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::render::plan::{
//!     RenderSettings, build_render_plan, validate_render_settings,
//! };
//! use stoat_ferret_core::compose::timeline::{CompositionClip, TransitionSpec};
//!
//! let clips = vec![
//!     CompositionClip::new(0, 0.0, 5.0, 0, 0),
//!     CompositionClip::new(1, 5.0, 10.0, 0, 0),
//! ];
//! let settings = RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
//! let plan = build_render_plan(&clips, &[], None, None, 1920, 1080, &settings);
//! assert_eq!(plan.segments.len(), 2);
//! assert_eq!(plan.total_frames, 300); // 10s * 30fps
//! ```

use pyo3::prelude::*;

pub mod encoder;
pub mod plan;

/// Registers render types and functions with the Python module.
pub fn register(m: &Bound<PyModule>) -> PyResult<()> {
    // Render plan types
    m.add_class::<plan::RenderSettings>()?;
    m.add_class::<plan::RenderSegment>()?;
    m.add_class::<plan::RenderPlan>()?;
    m.add_function(wrap_pyfunction!(plan::py_build_render_plan, m)?)?;
    m.add_function(wrap_pyfunction!(plan::py_validate_render_settings, m)?)?;

    // Encoder detection types
    m.add_class::<encoder::EncoderType>()?;
    m.add_class::<encoder::QualityPreset>()?;
    m.add_class::<encoder::EncoderInfo>()?;
    m.add_function(wrap_pyfunction!(encoder::py_detect_hardware_encoders, m)?)?;
    m.add_function(wrap_pyfunction!(encoder::py_select_encoder, m)?)?;
    m.add_function(wrap_pyfunction!(encoder::py_build_encoding_args, m)?)?;
    Ok(())
}
