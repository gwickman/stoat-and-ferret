// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Render graph translator — converts a multi-clip timeline (Timeline with clips
//! + per-clip effects) into an FFmpeg filter_complex string.
//!
//! This module is purpose-built for the render pipeline and is distinct from
//! `compose/graph.rs` (which handles spatial layout composition).
//!
//! # Filter pattern (PoC-0)
//!
//! ```text
//! [0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];
//! [v0]<per-clip-effects>[ev0];
//! [ev0][v1]xfade=transition=fade:duration=1[xf0];
//! [xf0]format=yuv420p[final]
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

/// Errors produced by the render graph translator.
#[derive(Debug)]
pub enum TranslateError {
    /// No clips were provided.
    EmptyClipList,
    /// A clip at the given index has a non-positive duration.
    InvalidDuration(usize),
}

impl std::fmt::Display for TranslateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TranslateError::EmptyClipList => write!(f, "clip list is empty"),
            TranslateError::InvalidDuration(i) => {
                write!(f, "clip {i} has non-positive duration_secs")
            }
        }
    }
}

// ---------------------------------------------------------------------------
// RenderEffect
// ---------------------------------------------------------------------------

/// Internal effect variant (not exposed to Python).
#[derive(Debug, Clone)]
pub enum RenderEffectKind {
    /// No effect — clip passes through unmodified.
    None,
    /// Animated alpha fade: linear interpolation from `start` to `end` over clip duration.
    AnimatedAlpha { start: f64, end: f64 },
}

/// An effect applied to a single render clip.
///
/// Use the static factory methods to construct variants:
/// - `RenderEffect.none()` — no-op
/// - `RenderEffect.animated_alpha(start, end)` — linear alpha fade
#[gen_stub_pyclass]
#[pyclass(name = "RenderEffect")]
#[derive(Debug, Clone)]
pub struct RenderEffect {
    pub(crate) kind: RenderEffectKind,
}

#[pymethods]
impl RenderEffect {
    /// Creates a no-op effect (clip passes through unmodified).
    #[staticmethod]
    #[pyo3(name = "none")]
    fn py_none() -> Self {
        Self {
            kind: RenderEffectKind::None,
        }
    }

    /// Creates an animated alpha effect that fades from `start` to `end` over the clip duration.
    ///
    /// Args:
    ///     start: Starting alpha in [0.0, 1.0] (0.0 = transparent).
    ///     end: Ending alpha in [0.0, 1.0] (1.0 = opaque).
    #[staticmethod]
    #[pyo3(name = "animated_alpha")]
    fn py_animated_alpha(start: f64, end: f64) -> Self {
        Self {
            kind: RenderEffectKind::AnimatedAlpha { start, end },
        }
    }

    fn __repr__(&self) -> String {
        match &self.kind {
            RenderEffectKind::None => "RenderEffect.none()".to_string(),
            RenderEffectKind::AnimatedAlpha { start, end } => {
                format!("RenderEffect.animated_alpha({start}, {end})")
            }
        }
    }
}

// ---------------------------------------------------------------------------
// ClipWithEffects
// ---------------------------------------------------------------------------

/// A render clip together with its per-clip effects.
///
/// `input_index` maps to the FFmpeg `-i` input argument position.
/// `duration_secs` is the clip's playback duration.
/// `framerate` is the clip's native frame rate; all clips are normalised to
/// 30 fps by the translator regardless of this value.
#[gen_stub_pyclass]
#[pyclass(name = "ClipWithEffects")]
#[derive(Debug, Clone)]
pub struct ClipWithEffects {
    /// Zero-based FFmpeg input index (corresponds to the `-i` argument position).
    #[pyo3(get)]
    pub input_index: usize,
    /// Clip duration in seconds (must be > 0).
    #[pyo3(get)]
    pub duration_secs: f64,
    /// Native frame rate of the clip (informational; normalised to 30 fps at translation).
    #[pyo3(get)]
    pub framerate: f64,
    /// Effects to apply to this clip before compositing.
    pub effects: Vec<RenderEffect>,
}

#[pymethods]
impl ClipWithEffects {
    /// Creates a new ClipWithEffects.
    ///
    /// Args:
    ///     input_index: Zero-based FFmpeg input index.
    ///     duration_secs: Clip duration in seconds. Must be > 0.
    ///     framerate: Native frame rate of the clip.
    ///     effects: List of RenderEffect to apply to this clip.
    ///
    /// Raises:
    ///     ValueError: If duration_secs is not > 0.
    #[new]
    fn py_new(
        input_index: usize,
        duration_secs: f64,
        framerate: f64,
        effects: Vec<RenderEffect>,
    ) -> PyResult<Self> {
        if duration_secs <= 0.0 {
            return Err(PyValueError::new_err(format!(
                "duration_secs must be > 0, got {duration_secs}"
            )));
        }
        Ok(Self {
            input_index,
            duration_secs,
            framerate,
            effects,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "ClipWithEffects(input_index={}, duration_secs={}, framerate={}, effects={})",
            self.input_index,
            self.duration_secs,
            self.framerate,
            self.effects.len(),
        )
    }
}

// ---------------------------------------------------------------------------
// RenderGraphTranslator
// ---------------------------------------------------------------------------

/// Translates a multi-clip render graph into an FFmpeg filter_complex string.
///
/// The produced string can be passed directly to FFmpeg's `-filter_complex`
/// argument. It uses `[final]` as the terminal output label.
///
/// # Filter stages
///
/// 1. Per-clip fps/settb normalization to 30 fps.
/// 2. Per-clip effect sub-chains (animated-alpha, etc.) — always before xfade.
/// 3. xfade transitions between adjacent clips (multi-clip only).
/// 4. `format=yuv420p` terminal (Windows Media Foundation compatibility).
#[gen_stub_pyclass]
#[pyclass(name = "RenderGraphTranslator")]
#[derive(Debug, Clone, Default)]
pub struct RenderGraphTranslator;

#[pymethods]
impl RenderGraphTranslator {
    /// Creates a new RenderGraphTranslator.
    #[new]
    fn py_new() -> Self {
        Self
    }

    /// Translates a list of clips with effects into an FFmpeg filter_complex string.
    ///
    /// Args:
    ///     clips: List of ClipWithEffects describing the timeline.
    ///
    /// Returns:
    ///     A semicolon-separated FFmpeg filter_complex string ending with `[final]`.
    ///
    /// Raises:
    ///     ValueError: If clips is empty or any clip has a non-positive duration.
    #[pyo3(name = "translate")]
    fn py_translate(&self, clips: Vec<ClipWithEffects>) -> PyResult<String> {
        self.translate(clips)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self) -> String {
        "RenderGraphTranslator()".to_string()
    }
}

impl RenderGraphTranslator {
    /// Core translation logic (pure Rust, no PyO3 dependency).
    pub fn translate(&self, clips: Vec<ClipWithEffects>) -> Result<String, TranslateError> {
        if clips.is_empty() {
            return Err(TranslateError::EmptyClipList);
        }
        for (i, clip) in clips.iter().enumerate() {
            if clip.duration_secs <= 0.0 {
                return Err(TranslateError::InvalidDuration(i));
            }
        }

        let mut parts: Vec<String> = Vec::new();

        // Stage 1: per-clip fps/settb normalization (all clips → 30 fps).
        for clip in &clips {
            let i = clip.input_index;
            parts.push(format!("[{i}:v]fps=30,settb=1/30[v{i}]"));
        }

        // Stage 2: per-clip effect sub-chains.
        // Effect chains must be emitted BEFORE the xfade/overlay stage.
        let mut effective_labels: Vec<String> = Vec::new();
        for clip in &clips {
            let i = clip.input_index;
            let has_effect = clip
                .effects
                .iter()
                .any(|e| !matches!(e.kind, RenderEffectKind::None));

            if has_effect {
                let chain = build_effect_chain(clip);
                parts.push(format!("[v{i}]{chain}[ev{i}]"));
                effective_labels.push(format!("[ev{i}]"));
            } else {
                effective_labels.push(format!("[v{i}]"));
            }
        }

        // Stage 3 + 4: xfade (multi-clip) then format=yuv420p terminal.
        if clips.len() == 1 {
            let label = &effective_labels[0];
            parts.push(format!("{label}format=yuv420p[final]"));
        } else {
            let mut current_label = effective_labels[0].clone();
            for (k, next_label) in effective_labels.iter().enumerate().skip(1) {
                let xf_label = format!("[xf{}]", k - 1);
                parts.push(format!(
                    "{current_label}{next_label}xfade=transition=fade:duration=1{xf_label}"
                ));
                current_label = xf_label;
            }
            parts.push(format!("{current_label}format=yuv420p[final]"));
        }

        Ok(parts.join(";"))
    }
}

/// Builds the effect filter chain string for a clip (excluding input/output labels).
fn build_effect_chain(clip: &ClipWithEffects) -> String {
    let mut filters: Vec<String> = Vec::new();
    for effect in &clip.effects {
        match &effect.kind {
            RenderEffectKind::None => {}
            RenderEffectKind::AnimatedAlpha { start, end } => {
                // geq-based animated alpha: linear interpolation from start*255 to end*255
                // over the clip duration, clamped to [0, 255].
                // Uses format=rgba to enable the alpha channel before geq.
                let d = clip.duration_secs;
                filters.push(format!(
                    "format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='({start}+({end}-{start})*min(1,t/{d}))*255'"
                ));
            }
        }
    }
    filters.join(",")
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn clip(input_index: usize, duration_secs: f64, framerate: f64) -> ClipWithEffects {
        ClipWithEffects {
            input_index,
            duration_secs,
            framerate,
            effects: vec![],
        }
    }

    fn clip_with_alpha(
        input_index: usize,
        duration_secs: f64,
        start: f64,
        end: f64,
    ) -> ClipWithEffects {
        ClipWithEffects {
            input_index,
            duration_secs,
            framerate: 30.0,
            effects: vec![RenderEffect {
                kind: RenderEffectKind::AnimatedAlpha { start, end },
            }],
        }
    }

    #[test]
    fn test_single_clip_has_fps_settb_and_format() {
        let clips = vec![clip(0, 5.0, 30.0)];
        let result = RenderGraphTranslator.translate(clips).unwrap();
        assert!(
            result.contains("fps=30"),
            "should contain fps=30, got: {result}"
        );
        assert!(
            result.contains("settb=1/30"),
            "should contain settb=1/30, got: {result}"
        );
        assert!(
            result.contains("format=yuv420p"),
            "should contain format=yuv420p, got: {result}"
        );
        assert!(
            result.contains("[final]"),
            "should contain [final], got: {result}"
        );
    }

    #[test]
    fn test_animated_alpha_before_overlay() {
        let clips = vec![clip_with_alpha(0, 5.0, 0.0, 1.0), clip(1, 5.0, 30.0)];
        let result = RenderGraphTranslator.translate(clips).unwrap();
        let effect_pos = result
            .find("geq")
            .expect("should contain geq effect sub-chain");
        let xfade_pos = result.find("xfade").expect("should contain xfade");
        assert!(
            effect_pos < xfade_pos,
            "effect sub-chain (pos {effect_pos}) should appear before xfade (pos {xfade_pos})"
        );
    }

    #[test]
    fn test_mixed_framerate_normalizes() {
        let clips = vec![clip(0, 5.0, 24.0), clip(1, 5.0, 60.0)];
        let result = RenderGraphTranslator.translate(clips).unwrap();
        let fps_count = result.matches("fps=30").count();
        assert!(
            fps_count >= 2,
            "both clips should be normalized to fps=30 (found {fps_count}), got: {result}"
        );
        assert!(
            result.contains("settb=1/30"),
            "should contain settb=1/30, got: {result}"
        );
    }

    #[test]
    fn test_empty_clips_returns_error() {
        let result = RenderGraphTranslator.translate(vec![]);
        assert!(
            matches!(result, Err(TranslateError::EmptyClipList)),
            "empty clips should return EmptyClipList error"
        );
    }

    #[test]
    fn test_two_clips_have_xfade() {
        let clips = vec![clip(0, 5.0, 30.0), clip(1, 5.0, 30.0)];
        let result = RenderGraphTranslator.translate(clips).unwrap();
        assert!(
            result.contains("xfade"),
            "two clips should produce xfade, got: {result}"
        );
        assert!(
            result.contains("[final]"),
            "should contain [final], got: {result}"
        );
    }

    #[test]
    fn test_terminal_format_yuv420p() {
        // Verify format=yuv420p is last before [final] for Windows MF compatibility
        let clips = vec![clip(0, 3.0, 30.0), clip(1, 3.0, 30.0)];
        let result = RenderGraphTranslator.translate(clips).unwrap();
        let fmt_pos = result
            .rfind("format=yuv420p")
            .expect("format=yuv420p not found");
        let final_pos = result.find("[final]").expect("[final] not found");
        assert!(
            fmt_pos < final_pos,
            "format=yuv420p should appear before [final]"
        );
    }
}
