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
//! [ev0]fps=30,settb=1/30[pv0];
//! [pv0][v1]xfade=transition=fade:duration=1[xf0];
//! [xf0]format=yuv420p[final]
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// Known FFmpeg xfade transition types.
const VALID_XFADE_TRANSITIONS: &[&str] = &[
    "fade",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "slideup",
    "slidedown",
    "circlecrop",
    "rectcrop",
    "distance",
    "fadeblack",
    "fadewhite",
    "radial",
    "smoothleft",
    "smoothright",
    "smoothup",
    "smoothdown",
    "circleopen",
    "circleclose",
    "horzopen",
    "horzclose",
    "vertopen",
    "vertclose",
    "dissolve",
    "pixelize",
    "diagbl",
    "diagbr",
    "diagtl",
    "diagtr",
    "hlslice",
    "hrslice",
    "vuslice",
    "vdslice",
    "hblur",
    "fadegrays",
    "wipetl",
    "wipetr",
    "wipebl",
    "wipebr",
    "squeezev",
    "squeezeh",
    "zoomin",
    "fadefast",
    "fadeslow",
    "coverleft",
    "coverright",
    "coverup",
    "coverdown",
    "revealleft",
    "revealright",
    "revealup",
    "revealdown",
];

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
    /// The clip list exceeds the maximum supported count (100).
    TooManyClips(usize),
    /// A clip at the given index has an empty source_path.
    InvalidSourcePath(usize),
    /// A transition at the given clip index has a non-positive duration.
    InvalidTransitionDuration(usize),
    /// A transition at the given clip index has an unknown transition_type.
    InvalidTransitionType(usize, String),
}

impl std::fmt::Display for TranslateError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TranslateError::EmptyClipList => write!(f, "clip list is empty"),
            TranslateError::InvalidDuration(i) => {
                write!(f, "clip {i} has non-positive duration_secs")
            }
            TranslateError::TooManyClips(n) => {
                write!(f, "clip list has {n} clips; maximum is 100")
            }
            TranslateError::InvalidSourcePath(i) => {
                write!(f, "clip {i} has an empty source_path")
            }
            TranslateError::InvalidTransitionDuration(i) => {
                write!(
                    f,
                    "clip {i} outgoing_transition has non-positive duration_secs"
                )
            }
            TranslateError::InvalidTransitionType(i, t) => {
                write!(
                    f,
                    "clip {i} outgoing_transition has unknown transition_type '{t}'"
                )
            }
        }
    }
}

// ---------------------------------------------------------------------------
// RenderTransition
// ---------------------------------------------------------------------------

/// An outgoing transition from one clip to the next (used by the xfade filter).
///
/// Set `outgoing_transition` on a `ClipWithEffects` to specify the transition
/// to the following clip. The last clip in the list should have `None`.
#[gen_stub_pyclass]
#[pyclass(name = "RenderTransition")]
#[derive(Debug, Clone)]
pub struct RenderTransition {
    /// FFmpeg xfade transition type (e.g. "fade", "wipeleft").
    #[pyo3(get, set)]
    pub transition_type: String,
    /// Transition duration in seconds (must be > 0).
    #[pyo3(get, set)]
    pub duration_secs: f64,
}

#[pymethods]
impl RenderTransition {
    /// Creates a new RenderTransition.
    ///
    /// Args:
    ///     transition_type: FFmpeg xfade transition type (e.g. "fade", "wipeleft").
    ///     duration_secs: Transition duration in seconds. Must be > 0.
    ///
    /// Raises:
    ///     ValueError: If duration_secs is not > 0 or transition_type is unknown.
    #[new]
    fn py_new(transition_type: String, duration_secs: f64) -> PyResult<Self> {
        if duration_secs <= 0.0 {
            return Err(PyValueError::new_err(format!(
                "duration_secs must be > 0, got {duration_secs}"
            )));
        }
        if !VALID_XFADE_TRANSITIONS.contains(&transition_type.as_str()) {
            return Err(PyValueError::new_err(format!(
                "unknown transition_type '{transition_type}'"
            )));
        }
        Ok(Self {
            transition_type,
            duration_secs,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderTransition(transition_type={:?}, duration_secs={})",
            self.transition_type, self.duration_secs
        )
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
    /// Whether the underlying FFmpeg filter supports the timeline T flag.
    /// When true and `enable_window` is set, the translator emits
    /// `:enable='between(t,start_s,end_s)'` instead of split/trim/concat.
    pub(crate) timeline_t_capable: bool,
    /// Optional time window [start_s, end_s] for windowed effect application.
    pub(crate) enable_window: Option<(f64, f64)>,
}

#[pymethods]
impl RenderEffect {
    /// Creates a no-op effect (clip passes through unmodified).
    #[staticmethod]
    #[pyo3(name = "none")]
    fn py_none() -> Self {
        Self {
            kind: RenderEffectKind::None,
            timeline_t_capable: false,
            enable_window: None,
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
            timeline_t_capable: false,
            enable_window: None,
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
/// `source_path` is the filesystem path to the video source file.
/// `outgoing_transition` specifies the xfade transition to the next clip,
/// or `None` for the last clip in the list.
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
    /// Filesystem path to the source video file.
    #[pyo3(get)]
    pub source_path: String,
    /// Effects to apply to this clip before compositing.
    pub effects: Vec<RenderEffect>,
    /// Transition to the next clip (None for the last clip).
    pub outgoing_transition: Option<RenderTransition>,
}

#[pymethods]
impl ClipWithEffects {
    /// Creates a new ClipWithEffects.
    ///
    /// Args:
    ///     input_index: Zero-based FFmpeg input index.
    ///     duration_secs: Clip duration in seconds. Must be > 0.
    ///     framerate: Native frame rate of the clip.
    ///     source_path: Filesystem path to the source video file.
    ///     effects: List of RenderEffect to apply to this clip.
    ///     outgoing_transition: Transition to the next clip, or None for the last clip.
    ///
    /// Raises:
    ///     ValueError: If duration_secs is not > 0.
    #[new]
    #[pyo3(signature = (input_index, duration_secs, framerate, source_path, effects, outgoing_transition=None))]
    fn py_new(
        input_index: usize,
        duration_secs: f64,
        framerate: f64,
        source_path: String,
        effects: Vec<RenderEffect>,
        outgoing_transition: Option<RenderTransition>,
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
            source_path,
            effects,
            outgoing_transition,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "ClipWithEffects(input_index={}, duration_secs={}, framerate={}, source_path={:?}, effects={})",
            self.input_index,
            self.duration_secs,
            self.framerate,
            self.source_path,
            self.effects.len(),
        )
    }
}

// ---------------------------------------------------------------------------
// RenderGraphTranslator
// ---------------------------------------------------------------------------

/// Translates a multi-clip render graph into an FFmpeg filter_complex string
/// plus an ordered list of `-i` input paths.
///
/// The produced filter_complex string can be passed directly to FFmpeg's
/// `-filter_complex` argument. It uses `[final]` as the terminal output label.
///
/// # Filter stages
///
/// 1. Per-clip fps/settb normalization to 30 fps.
/// 2. Per-clip effect sub-chains (animated-alpha, etc.) — always before xfade.
/// 3. fps/settb re-pin at every sub-chain boundary feeding xfade.
/// 4. xfade transitions between adjacent clips (multi-clip only).
/// 5. `format=yuv420p` terminal (Windows Media Foundation compatibility).
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

    /// Translates a list of clips with effects into a (filter_complex, input_paths) tuple.
    ///
    /// Args:
    ///     clips: List of ClipWithEffects describing the timeline.
    ///
    /// Returns:
    ///     A 2-tuple of (filter_complex_string, input_paths_list) where
    ///     filter_complex_string is a semicolon-separated FFmpeg filter_complex
    ///     ending with `[final]`, and input_paths_list is the ordered list of
    ///     source video paths for `-i` arguments.
    ///
    /// Raises:
    ///     ValueError: If clips is empty, exceeds 100, or contains invalid data.
    #[pyo3(name = "translate")]
    fn py_translate(&self, clips: Vec<ClipWithEffects>) -> PyResult<(String, Vec<String>)> {
        self.translate(clips)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    fn __repr__(&self) -> String {
        "RenderGraphTranslator()".to_string()
    }
}

impl RenderGraphTranslator {
    /// Core translation logic (pure Rust, no PyO3 dependency).
    pub fn translate(
        &self,
        clips: Vec<ClipWithEffects>,
    ) -> Result<(String, Vec<String>), TranslateError> {
        // N > 100 guard — checked before any allocation.
        if clips.len() > 100 {
            return Err(TranslateError::TooManyClips(clips.len()));
        }
        if clips.is_empty() {
            return Err(TranslateError::EmptyClipList);
        }

        // Validate all clips and transitions up front.
        for (i, clip) in clips.iter().enumerate() {
            if clip.duration_secs <= 0.0 {
                return Err(TranslateError::InvalidDuration(i));
            }
            if clip.source_path.is_empty() {
                return Err(TranslateError::InvalidSourcePath(i));
            }
            if let Some(t) = &clip.outgoing_transition {
                if t.duration_secs <= 0.0 {
                    return Err(TranslateError::InvalidTransitionDuration(i));
                }
                if !VALID_XFADE_TRANSITIONS.contains(&t.transition_type.as_str()) {
                    return Err(TranslateError::InvalidTransitionType(
                        i,
                        t.transition_type.clone(),
                    ));
                }
            }
        }

        // Collect ordered input paths from source_path fields.
        let input_paths: Vec<String> = clips.iter().map(|c| c.source_path.clone()).collect();

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

        // Stage 3 + 4 + 5: fps/settb re-pin at xfade boundaries, xfade (multi-clip),
        // then format=yuv420p terminal.
        if clips.len() == 1 {
            let label = &effective_labels[0];
            parts.push(format!("{label}format=yuv420p[final]"));
        } else {
            let mut current_label = effective_labels[0].clone();
            for k in 1..clips.len() {
                let next_label = &effective_labels[k];
                let xf_label = format!("[xf{}]", k - 1);

                // fps/settb re-pin at every boundary feeding xfade (BL-507 cross-segment rule).
                let pinned_current = format!("[pv{}]", k - 1);
                let pinned_next = format!("[pn{}]", k);
                parts.push(format!("{current_label}fps=30,settb=1/30{pinned_current}"));
                parts.push(format!("{next_label}fps=30,settb=1/30{pinned_next}"));

                // Determine xfade parameters from outgoing_transition (clip k-1).
                let (transition_type, duration) = if let Some(t) = &clips[k - 1].outgoing_transition
                {
                    (t.transition_type.as_str(), t.duration_secs)
                } else {
                    ("fade", 1.0)
                };

                parts.push(format!(
                    "{pinned_current}{pinned_next}xfade=transition={transition_type}:duration={duration}{xf_label}"
                ));
                current_label = xf_label;
            }
            parts.push(format!("{current_label}format=yuv420p[final]"));
        }

        Ok((parts.join(";"), input_paths))
    }
}

/// Builds the effect filter chain string for a clip (excluding input/output labels).
///
/// For effects with `timeline_t_capable=true` and an `enable_window`, emits
/// `:enable='between(t,start_s,end_s)'` to restrict the effect to a time window.
/// Otherwise applies the effect to the entire clip (split/trim/concat fallback is
/// deferred to a future feature since no v088 builder uses windowing).
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
                let filter = format!(
                    "format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='({start}+({end}-{start})*min(1,t/{d}))*255'"
                );
                // Enable expression: applied when the filter supports the T flag
                // and a time window is provided.
                let filter = if effect.timeline_t_capable {
                    if let Some((start_s, end_s)) = effect.enable_window {
                        format!("{filter}:enable='between(t,{start_s},{end_s})'")
                    } else {
                        filter
                    }
                } else {
                    filter
                };
                filters.push(filter);
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

    fn clip(
        input_index: usize,
        duration_secs: f64,
        framerate: f64,
        source_path: &str,
    ) -> ClipWithEffects {
        ClipWithEffects {
            input_index,
            duration_secs,
            framerate,
            source_path: source_path.to_string(),
            effects: vec![],
            outgoing_transition: None,
        }
    }

    fn clip_with_transition(
        input_index: usize,
        duration_secs: f64,
        source_path: &str,
        transition_type: &str,
        transition_duration: f64,
    ) -> ClipWithEffects {
        ClipWithEffects {
            input_index,
            duration_secs,
            framerate: 30.0,
            source_path: source_path.to_string(),
            effects: vec![],
            outgoing_transition: Some(RenderTransition {
                transition_type: transition_type.to_string(),
                duration_secs: transition_duration,
            }),
        }
    }

    fn clip_with_alpha(
        input_index: usize,
        duration_secs: f64,
        source_path: &str,
        start: f64,
        end: f64,
    ) -> ClipWithEffects {
        ClipWithEffects {
            input_index,
            duration_secs,
            framerate: 30.0,
            source_path: source_path.to_string(),
            effects: vec![RenderEffect {
                kind: RenderEffectKind::AnimatedAlpha { start, end },
                timeline_t_capable: false,
                enable_window: None,
            }],
            outgoing_transition: None,
        }
    }

    #[test]
    fn test_single_clip_has_fps_settb_and_format() {
        let clips = vec![clip(0, 5.0, 30.0, "/a.mp4")];
        let (result, paths) = RenderGraphTranslator.translate(clips).unwrap();
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
        assert_eq!(paths, vec!["/a.mp4"]);
    }

    #[test]
    fn test_translate_returns_input_paths_in_clip_order() {
        let clips = vec![
            clip(0, 5.0, 30.0, "/clip0.mp4"),
            clip(1, 5.0, 30.0, "/clip1.mp4"),
        ];
        let (_filter, paths) = RenderGraphTranslator.translate(clips).unwrap();
        assert_eq!(paths, vec!["/clip0.mp4", "/clip1.mp4"]);
    }

    #[test]
    fn test_animated_alpha_before_xfade() {
        let clips = vec![
            clip_with_alpha(0, 5.0, "/a.mp4", 0.0, 1.0),
            clip(1, 5.0, 30.0, "/b.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
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
        let clips = vec![clip(0, 5.0, 24.0, "/a.mp4"), clip(1, 5.0, 60.0, "/b.mp4")];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
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
    fn test_too_many_clips_returns_error() {
        let clips: Vec<ClipWithEffects> =
            (0..101).map(|i| clip(i, 1.0, 30.0, "/clip.mp4")).collect();
        let result = RenderGraphTranslator.translate(clips);
        assert!(
            matches!(result, Err(TranslateError::TooManyClips(101))),
            "101 clips should return TooManyClips(101)"
        );
    }

    #[test]
    fn test_invalid_source_path_returns_error() {
        let clips = vec![clip(0, 5.0, 30.0, "")];
        let result = RenderGraphTranslator.translate(clips);
        assert!(
            matches!(result, Err(TranslateError::InvalidSourcePath(0))),
            "empty source_path should return InvalidSourcePath(0)"
        );
    }

    #[test]
    fn test_invalid_transition_duration_returns_error() {
        let clips = vec![
            clip_with_transition(0, 5.0, "/a.mp4", "fade", 0.0),
            clip(1, 5.0, 30.0, "/b.mp4"),
        ];
        let result = RenderGraphTranslator.translate(clips);
        assert!(
            matches!(result, Err(TranslateError::InvalidTransitionDuration(0))),
            "zero transition duration should return InvalidTransitionDuration(0)"
        );
    }

    #[test]
    fn test_invalid_transition_type_returns_error() {
        let clips = vec![
            clip_with_transition(0, 5.0, "/a.mp4", "not_a_real_transition", 1.0),
            clip(1, 5.0, 30.0, "/b.mp4"),
        ];
        let result = RenderGraphTranslator.translate(clips);
        assert!(
            matches!(result, Err(TranslateError::InvalidTransitionType(0, _))),
            "unknown transition type should return InvalidTransitionType(0, ...)"
        );
    }

    #[test]
    fn test_two_clips_have_xfade() {
        let clips = vec![
            clip_with_transition(0, 5.0, "/a.mp4", "fade", 1.0),
            clip(1, 5.0, 30.0, "/b.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
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
    fn test_xfade_uses_outgoing_transition_params() {
        let clips = vec![
            clip_with_transition(0, 5.0, "/a.mp4", "wipeleft", 2.5),
            clip(1, 5.0, 30.0, "/b.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
        assert!(
            result.contains("transition=wipeleft"),
            "should use specified transition type, got: {result}"
        );
        assert!(
            result.contains("duration=2.5"),
            "should use specified transition duration, got: {result}"
        );
    }

    #[test]
    fn test_terminal_format_yuv420p() {
        // Verify format=yuv420p is last before [final] for Windows MF compatibility
        let clips = vec![
            clip_with_transition(0, 3.0, "/a.mp4", "fade", 1.0),
            clip(1, 3.0, 30.0, "/b.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
        let fmt_pos = result
            .rfind("format=yuv420p")
            .expect("format=yuv420p not found");
        let final_pos = result.find("[final]").expect("[final] not found");
        assert!(
            fmt_pos < final_pos,
            "format=yuv420p should appear before [final]"
        );
    }

    #[test]
    fn test_fps_settb_pin_at_xfade_boundaries() {
        // BL-507 cross-segment rule: fps/settb re-pin before every xfade input.
        let clips = vec![
            clip_with_transition(0, 5.0, "/a.mp4", "fade", 1.0),
            clip(1, 5.0, 30.0, "/b.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
        // Stage 1 gives one fps=30 per clip; re-pins at xfade boundary give more.
        let fps_count = result.matches("fps=30").count();
        assert!(
            fps_count >= 4,
            "expected ≥4 fps=30 occurrences (2 stage-1 + 2 re-pins), got {fps_count}: {result}"
        );
    }

    #[test]
    fn test_100_clips_is_accepted() {
        let clips: Vec<ClipWithEffects> =
            (0..100).map(|i| clip(i, 1.0, 30.0, "/clip.mp4")).collect();
        let result = RenderGraphTranslator.translate(clips);
        assert!(result.is_ok(), "100 clips should be accepted");
    }
}
