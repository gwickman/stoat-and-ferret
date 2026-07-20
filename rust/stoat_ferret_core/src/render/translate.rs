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
//! [pv0][pn1]xfade=transition=fade:duration=1:offset=2[xf0];
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
// EffectChainResult
// ---------------------------------------------------------------------------

/// Result of building a per-clip effect sub-chain.
///
/// `Simple` contains a filter chain string injected directly between
/// `[v{i}]` and `[ev{i}]` by Stage 2. `WindowedGraph` contains a set of
/// filter_complex parts that implement windowed application via split/trim/concat
/// for filters that do not support FFmpeg's `enable=` timeline expression.
pub(crate) enum EffectChainResult {
    /// A single filter chain string to inject as `[v{i}]{chain}[ev{i}]`.
    Simple(String),
    /// Multiple filter_complex parts implementing split/trim/concat windowing.
    /// The output label is always `ev{i}` (where `i` is `clip.input_index`).
    WindowedGraph {
        parts: Vec<String>,
        /// The final output label (always `ev{i}`). Provided for callers that
        /// need to know the label without re-deriving it from input_index.
        #[allow(dead_code)]
        output_label: String,
    },
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
    /// Raw FFmpeg filter chain string injected directly (from EffectDefinition.build_fn output).
    Custom { filter_chain: String },
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

    /// Creates a custom effect from a raw FFmpeg filter chain string.
    ///
    /// Args:
    ///     filter_chain: A valid FFmpeg filter chain string (e.g. "gblur=sigma=2.5").
    ///                   Produced by EffectDefinition.build_fn(); injected verbatim.
    #[staticmethod]
    #[pyo3(name = "custom")]
    pub fn py_custom(filter_chain: String) -> Self {
        Self {
            kind: RenderEffectKind::Custom { filter_chain },
            timeline_t_capable: false,
            enable_window: None,
        }
    }

    /// Creates a windowed custom effect from a raw FFmpeg filter chain string.
    ///
    /// Sets `enable_window = Some((start_s, end_s))` and `timeline_t_capable` to
    /// the supplied value (default `true`). When `timeline_t_capable=true` the
    /// translator emits `enable='between(t,…)'`; when `false` it routes through
    /// the split/trim/concat graph-level fallback (BL-512-AC-2).
    ///
    /// Returns `PyValueError` if floats are non-finite or `start_s >= end_s`.
    #[staticmethod]
    #[pyo3(
        name = "windowed_custom",
        signature = (filter_chain, start_s, end_s, timeline_t_capable = true)
    )]
    pub fn py_windowed_custom(
        filter_chain: String,
        start_s: f64,
        end_s: f64,
        timeline_t_capable: bool,
    ) -> PyResult<Self> {
        if !start_s.is_finite() || !end_s.is_finite() {
            return Err(PyValueError::new_err("start_s and end_s must be finite"));
        }
        if start_s >= end_s {
            return Err(PyValueError::new_err(format!(
                "start_s ({start_s:?}) must be less than end_s ({end_s:?})"
            )));
        }
        Ok(RenderEffect {
            kind: RenderEffectKind::Custom { filter_chain },
            timeline_t_capable,
            enable_window: Some((start_s, end_s)),
        })
    }

    fn __repr__(&self) -> String {
        match &self.kind {
            RenderEffectKind::None => "RenderEffect.none()".to_string(),
            RenderEffectKind::AnimatedAlpha { start, end } => {
                format!("RenderEffect.animated_alpha({start}, {end})")
            }
            RenderEffectKind::Custom { filter_chain } => {
                format!("RenderEffect.custom({filter_chain:?})")
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
                let chain_result = build_effect_chain(clip);
                match chain_result {
                    EffectChainResult::Simple(chain_str) => {
                        parts.push(format!("[v{i}]{chain_str}[ev{i}]"));
                    }
                    EffectChainResult::WindowedGraph {
                        parts: graph_parts, ..
                    } => {
                        parts.extend(graph_parts);
                    }
                }
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
            let mut accumulated = clips[0].duration_secs;
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

                // offset = cumulative output duration before this transition.
                let offset = accumulated - duration;
                parts.push(format!(
                    "{pinned_current}{pinned_next}xfade=transition={transition_type}:duration={duration}:offset={offset}{xf_label}"
                ));
                accumulated = accumulated - duration + clips[k].duration_secs;
                current_label = xf_label;
            }
            parts.push(format!("{current_label}format=yuv420p[final]"));
        }

        Ok((parts.join(";"), input_paths))
    }
}

/// Builds the effect sub-chain for a clip and returns an `EffectChainResult`.
///
/// When a `Custom` effect has `timeline_t_capable=false` and `enable_window` set,
/// returns `WindowedGraph` with split/trim/concat parts (BL-512-AC-2 non-T fallback).
/// For all other cases (T-capable windowed or non-windowed effects) returns `Simple`.
fn build_effect_chain(clip: &ClipWithEffects) -> EffectChainResult {
    let i = clip.input_index;

    // Non-T windowed fallback: a Custom effect with !timeline_t_capable + enable_window
    // must be routed through split/trim/concat (BL-512-AC-2).
    let non_t_windowed = clip.effects.iter().find(|e| {
        matches!(&e.kind, RenderEffectKind::Custom { .. })
            && !e.timeline_t_capable
            && e.enable_window.is_some()
    });

    if let Some(effect) = non_t_windowed {
        let (start_s, end_s) = effect.enable_window.unwrap();
        let filter_chain = match &effect.kind {
            RenderEffectKind::Custom { filter_chain } => filter_chain.as_str(),
            _ => unreachable!(),
        };

        // Build split/trim/concat graph. format=yuv420p at each segment junction
        // ensures pix_fmt compatibility (NFR-003). setpts=PTS-STARTPTS resets
        // timestamps after trim so that concat produces correct output timing.
        let bef =
            format!("[vi_bef{i}]trim=end={start_s},setpts=PTS-STARTPTS,format=yuv420p[bef{i}]");
        let seg = format!(
            "[vi_seg{i}]trim=start={start_s}:end={end_s},setpts=PTS-STARTPTS,\
             {filter_chain},format=yuv420p[seg{i}]"
        );
        let aft =
            format!("[vi_aft{i}]trim=start={end_s},setpts=PTS-STARTPTS,format=yuv420p[aft{i}]");
        let parts = vec![
            format!("[v{i}]split=3[vi_seg{i}][vi_bef{i}][vi_aft{i}]"),
            bef,
            seg,
            aft,
            format!("[bef{i}][seg{i}][aft{i}]concat=n=3:v=1:a=0[ev{i}]"),
        ];
        return EffectChainResult::WindowedGraph {
            parts,
            output_label: format!("ev{i}"),
        };
    }

    // Simple path: T-capable windowed effects or effects without a window.
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
                    "format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='({start}+({end}-{start})*min(1,T/{d}))*255'"
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
            RenderEffectKind::Custom { filter_chain } => {
                // LRN-775: enable= uses lowercase t (timeline time); geq uses uppercase T.
                let filter = if effect.timeline_t_capable {
                    if let Some((start_s, end_s)) = effect.enable_window {
                        format!("{filter_chain}:enable='between(t,{start_s:?},{end_s:?})'")
                    } else {
                        filter_chain.clone()
                    }
                } else {
                    filter_chain.clone()
                };
                filters.push(filter);
            }
        }
    }
    EffectChainResult::Simple(filters.join(","))
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
    fn test_animated_alpha_uses_uppercase_t() {
        let clips = vec![
            clip_with_alpha(0, 5.0, "/a.mp4", 0.0, 1.0),
            clip(1, 5.0, 30.0, "/b.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
        assert!(
            result.contains("min(1,T/"),
            "AnimatedAlpha geq expression must use uppercase T (FFmpeg geq timestamp variable), got: {result}"
        );
        assert!(
            !result.contains("min(1,t/"),
            "AnimatedAlpha geq expression must NOT use lowercase t as geq time term, got: {result}"
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
    fn test_xfade_includes_offset() {
        // clip0=3s, xfade=1s → offset = 3 - 1 = 2
        let clips = vec![
            clip_with_transition(0, 3.0, "/a.mp4", "fade", 1.0),
            clip(1, 3.0, 30.0, "/b.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
        assert!(
            result.contains("offset=2"),
            "xfade must include offset=2 for 3s clip with 1s transition; got: {result}"
        );
    }

    #[test]
    fn test_xfade_offset_accumulates_across_clips() {
        // clip0=4s/tr=1s, clip1=3s/tr=1s, clip2=5s
        // join 0→1: offset = 4-1 = 3; join 1→2: offset = (4-1+3)-1 = 5
        let clips = vec![
            clip_with_transition(0, 4.0, "/a.mp4", "fade", 1.0),
            clip_with_transition(1, 3.0, "/b.mp4", "fade", 1.0),
            clip(2, 5.0, 30.0, "/c.mp4"),
        ];
        let (result, _) = RenderGraphTranslator.translate(clips).unwrap();
        assert!(
            result.contains("offset=3"),
            "first xfade must include offset=3; got: {result}"
        );
        assert!(
            result.contains("offset=5"),
            "second xfade must include offset=5; got: {result}"
        );
    }

    #[test]
    fn test_100_clips_is_accepted() {
        let clips: Vec<ClipWithEffects> =
            (0..100).map(|i| clip(i, 1.0, 30.0, "/clip.mp4")).collect();
        let result = RenderGraphTranslator.translate(clips);
        assert!(result.is_ok(), "100 clips should be accepted");
    }

    #[test]
    fn test_custom_variant_passthrough() {
        let filter_str = "gblur=sigma=2.5".to_string();
        let clip = ClipWithEffects {
            input_index: 0,
            duration_secs: 5.0,
            framerate: 30.0,
            source_path: "/a.mp4".to_string(),
            effects: vec![RenderEffect {
                kind: RenderEffectKind::Custom {
                    filter_chain: filter_str.clone(),
                },
                timeline_t_capable: false,
                enable_window: None,
            }],
            outgoing_transition: None,
        };
        let (result, _) = RenderGraphTranslator.translate(vec![clip]).unwrap();
        assert!(
            result.contains(&filter_str),
            "Custom filter_chain must appear verbatim in output; got: {result}"
        );
    }

    #[test]
    fn test_windowed_custom_valid() {
        let e =
            RenderEffect::py_windowed_custom("gblur=sigma=7".to_string(), 1.0, 3.0, true).unwrap();
        assert!(e.timeline_t_capable);
        assert_eq!(e.enable_window, Some((1.0, 3.0)));
    }

    #[test]
    fn test_windowed_custom_rejects_inverted() {
        assert!(
            RenderEffect::py_windowed_custom("gblur=sigma=7".to_string(), 5.0, 1.0, true).is_err()
        );
    }

    #[test]
    fn test_windowed_custom_rejects_equal() {
        assert!(
            RenderEffect::py_windowed_custom("gblur=sigma=7".to_string(), 2.0, 2.0, true).is_err()
        );
    }

    #[test]
    fn test_windowed_custom_rejects_nan() {
        assert!(
            RenderEffect::py_windowed_custom("gblur=sigma=7".to_string(), f64::NAN, 3.0, true)
                .is_err()
        );
    }

    #[test]
    fn test_windowed_custom_non_t_sets_timeline_t_capable_false() {
        let e =
            RenderEffect::py_windowed_custom("scale=iw:ih".to_string(), 1.0, 3.0, false).unwrap();
        assert!(!e.timeline_t_capable);
        assert_eq!(e.enable_window, Some((1.0, 3.0)));
    }

    #[test]
    fn test_build_effect_chain_t_capable_returns_simple() {
        let clip = ClipWithEffects {
            input_index: 0,
            duration_secs: 5.0,
            framerate: 30.0,
            source_path: "/a.mp4".to_string(),
            effects: vec![RenderEffect {
                kind: RenderEffectKind::Custom {
                    filter_chain: "gblur=sigma=7".to_string(),
                },
                timeline_t_capable: true,
                enable_window: Some((1.0, 3.0)),
            }],
            outgoing_transition: None,
        };
        let result = build_effect_chain(&clip);
        assert!(
            matches!(result, EffectChainResult::Simple(_)),
            "T-capable windowed Custom must return Simple"
        );
    }

    #[test]
    fn test_build_effect_chain_non_t_windowed_returns_windowed_graph() {
        let clip = ClipWithEffects {
            input_index: 0,
            duration_secs: 5.0,
            framerate: 30.0,
            source_path: "/a.mp4".to_string(),
            effects: vec![RenderEffect {
                kind: RenderEffectKind::Custom {
                    filter_chain: "scale=iw*0.5:ih*0.5".to_string(),
                },
                timeline_t_capable: false,
                enable_window: Some((1.0, 3.0)),
            }],
            outgoing_transition: None,
        };
        let result = build_effect_chain(&clip);
        match result {
            EffectChainResult::WindowedGraph {
                parts,
                output_label,
            } => {
                let joined = parts.join(";");
                assert!(
                    joined.contains("split=3"),
                    "must contain split=3; got: {joined}"
                );
                assert!(
                    joined.contains("trim=start="),
                    "must contain trim=start=; got: {joined}"
                );
                assert!(
                    joined.contains("concat=n=3"),
                    "must contain concat=n=3; got: {joined}"
                );
                assert!(
                    joined.contains("format=yuv420p"),
                    "must contain format=yuv420p at each junction; got: {joined}"
                );
                assert!(
                    joined.contains("scale=iw*0.5:ih*0.5"),
                    "effect chain must appear in segment; got: {joined}"
                );
                assert_eq!(output_label, "ev0");
            }
            EffectChainResult::Simple(_) => {
                panic!("non-T windowed Custom must return WindowedGraph, got Simple");
            }
        }
    }

    #[test]
    fn test_window_zero_length_returns_error() {
        // BL-512-AC-2: zero-length window must be rejected at construction time
        let err = RenderEffect::py_windowed_custom("scale=iw:ih".to_string(), 2.0, 2.0, true)
            .unwrap_err();
        let msg = err.to_string();
        assert!(
            msg.contains("must be less than"),
            "error must state start < end constraint; got: {msg}"
        );
    }
}
