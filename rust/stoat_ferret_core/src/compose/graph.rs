//! Composition graph builder — the primary entry point for building
//! complete FFmpeg filter graphs from multi-clip compositions.
//!
//! Supports two composition modes:
//!
//! - **Sequential** (no layout): Clips play one after another, using
//!   concat or xfade/acrossfade for transitions.
//! - **Layout** (with layout): Clips are spatially composited on a canvas
//!   using overlay/scale positioning. Optional audio mixing via [`AudioMixSpec`].
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::compose::graph::{build_composition_graph, LayoutSpec};
//! use stoat_ferret_core::compose::timeline::{CompositionClip, TransitionSpec};
//! use stoat_ferret_core::ffmpeg::transitions::TransitionType;
//!
//! // Sequential 2-clip composition with crossfade
//! let clips = vec![
//!     CompositionClip::new(0, 0.0, 5.0, 0, 0),
//!     CompositionClip::new(1, 5.0, 10.0, 0, 0),
//! ];
//! let transitions = vec![
//!     TransitionSpec::new(TransitionType::Fade, 1.0, 0.0),
//! ];
//! let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
//! let s = graph.to_string();
//! assert!(s.contains("xfade"));
//! assert!(s.contains("acrossfade"));
//! ```

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use crate::compose::timeline::{calculate_composition_positions, CompositionClip, TransitionSpec};
use crate::ffmpeg::audio::AudioMixSpec;
use crate::ffmpeg::filter::{concat, Filter, FilterChain, FilterGraph};
use crate::layout::position::LayoutPosition;

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

/// Rounds a value to the nearest even number (minimum 2).
///
/// FFmpeg requires even dimensions for many codecs (e.g., H.264).
fn round_even(value: f64) -> u32 {
    let rounded = value.round() as i64;
    let even = if rounded % 2 == 0 {
        rounded
    } else {
        rounded + 1
    };
    even.max(2) as u32
}

/// Layout specification for multi-stream composition.
///
/// Contains a list of [`LayoutPosition`] values that define where each
/// input stream is placed on the output canvas. Position indices
/// correspond to clip indices in the composition.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::compose::graph::LayoutSpec;
/// use stoat_ferret_core::layout::position::LayoutPosition;
///
/// let positions = vec![
///     LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),   // full-screen base
///     LayoutPosition::new(0.73, 0.02, 0.25, 0.25, 1), // PIP overlay
/// ];
/// let spec = LayoutSpec::new(positions).unwrap();
/// assert_eq!(spec.position_count(), 2);
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct LayoutSpec {
    /// Layout positions for each input stream.
    positions: Vec<LayoutPosition>,
}

impl LayoutSpec {
    /// Creates a new LayoutSpec with validation.
    ///
    /// # Arguments
    ///
    /// * `positions` - Layout positions (at least 1 required)
    ///
    /// # Errors
    ///
    /// Returns an error if positions is empty.
    pub fn new(positions: Vec<LayoutPosition>) -> Result<Self, String> {
        if positions.is_empty() {
            return Err("LayoutSpec requires at least one position".to_string());
        }
        Ok(Self { positions })
    }

    /// Returns the layout positions.
    #[must_use]
    pub fn positions(&self) -> &[LayoutPosition] {
        &self.positions
    }

    /// Returns the number of positions.
    #[must_use]
    pub fn position_count(&self) -> usize {
        self.positions.len()
    }
}

#[pymethods]
impl LayoutSpec {
    /// Creates a new LayoutSpec from a list of LayoutPosition.
    ///
    /// Args:
    ///     positions: List of LayoutPosition (at least 1).
    ///
    /// Raises:
    ///     ValueError: If positions is empty.
    #[new]
    fn py_new(positions: Vec<LayoutPosition>) -> PyResult<Self> {
        Self::new(positions).map_err(PyValueError::new_err)
    }

    /// Returns the layout positions.
    #[pyo3(name = "positions")]
    fn py_positions(&self) -> Vec<LayoutPosition> {
        self.positions.clone()
    }

    /// Returns the number of positions.
    #[pyo3(name = "position_count")]
    fn py_position_count(&self) -> usize {
        self.position_count()
    }

    /// Returns a string representation of the spec.
    fn __repr__(&self) -> String {
        format!("LayoutSpec(positions={})", self.positions.len())
    }
}

/// Builds a complete FilterGraph for multi-clip composition.
///
/// This is the primary composition entry point. Depending on whether a layout
/// is provided, builds either:
/// - **Sequential mode** (no layout): concat or xfade/acrossfade chains
/// - **Layout mode** (with layout): overlay/scale spatial composition
///
/// # Arguments
///
/// * `clips` - Clips positioned on the composition timeline
/// * `transitions` - Transitions between adjacent clips (used in sequential mode)
/// * `layout` - Optional layout for spatial composition (PIP, side-by-side)
/// * `audio_mix` - Optional audio mix specification (used in layout mode)
/// * `output_width` - Output canvas width in pixels
/// * `output_height` - Output canvas height in pixels
///
/// # Returns
///
/// A complete FilterGraph ready for FFmpeg's `-filter_complex` argument.
pub fn build_composition_graph(
    clips: &[CompositionClip],
    transitions: &[TransitionSpec],
    layout: Option<&LayoutSpec>,
    audio_mix: Option<&AudioMixSpec>,
    output_width: u32,
    output_height: u32,
) -> FilterGraph {
    if clips.is_empty() {
        return FilterGraph::new();
    }

    if clips.len() == 1 {
        return build_single_clip_graph(clips, output_width, output_height);
    }

    match layout {
        Some(spec) => build_layout_graph(clips, spec, audio_mix, output_width, output_height),
        None => build_sequential_graph(clips, transitions),
    }
}

/// Builds a graph for a single clip (scale to output size).
fn build_single_clip_graph(
    clips: &[CompositionClip],
    output_width: u32,
    output_height: u32,
) -> FilterGraph {
    let clip = &clips[0];
    let input_label = format!("{}:v", clip.input_index);

    let scale_filter = Filter::new("scale")
        .param("w", output_width)
        .param("h", output_height)
        .param("force_divisible_by", 2);

    FilterGraph::new().chain(
        FilterChain::new()
            .input(&input_label)
            .filter(scale_filter)
            .output("outv"),
    )
}

/// Builds a sequential composition graph (clips play one after another).
fn build_sequential_graph(
    clips: &[CompositionClip],
    transitions: &[TransitionSpec],
) -> FilterGraph {
    if transitions.is_empty() {
        build_concat_graph(clips)
    } else {
        build_xfade_graph(clips, transitions)
    }
}

/// Builds a concat-based graph for sequential composition without transitions.
fn build_concat_graph(clips: &[CompositionClip]) -> FilterGraph {
    let n = clips.len();

    let mut chain = FilterChain::new();
    for clip in clips {
        chain = chain
            .input(format!("{}:v", clip.input_index))
            .input(format!("{}:a", clip.input_index));
    }
    chain = chain.filter(concat(n, 1, 1)).output("outv").output("outa");

    FilterGraph::new().chain(chain)
}

/// Builds an xfade/acrossfade graph for sequential composition with transitions.
fn build_xfade_graph(clips: &[CompositionClip], transitions: &[TransitionSpec]) -> FilterGraph {
    let mut graph = FilterGraph::new();
    let adjusted = calculate_composition_positions(clips, transitions);

    // Track accumulated output duration for xfade offset calculation
    let mut accumulated_duration = adjusted[0].duration();

    for i in 0..clips.len() - 1 {
        // No transition available for this pair — stop chaining
        if i >= transitions.len() {
            break;
        }

        let transition = &transitions[i];
        let clip_b_dur = adjusted[i + 1].duration();

        // Clamp transition duration to prevent invalid offsets
        let clamped_dur = transition
            .duration
            .min(accumulated_duration)
            .min(clip_b_dur)
            .max(0.0);

        // xfade offset: when in the accumulated output the transition starts
        let offset = accumulated_duration - clamped_dur;

        // Video xfade chain
        let video_in_a = if i == 0 {
            format!("{}:v", clips[0].input_index)
        } else {
            format!("xv{}", i - 1)
        };
        let video_out = if i == clips.len() - 2 {
            "outv".to_string()
        } else {
            format!("xv{i}")
        };

        graph = graph.chain(
            FilterChain::new()
                .input(video_in_a)
                .input(format!("{}:v", clips[i + 1].input_index))
                .filter(
                    Filter::new("xfade")
                        .param("transition", transition.transition_type.as_str())
                        .param("duration", format_value(clamped_dur))
                        .param("offset", format_value(offset)),
                )
                .output(video_out),
        );

        // Audio acrossfade chain
        let audio_in_a = if i == 0 {
            format!("{}:a", clips[0].input_index)
        } else {
            format!("xa{}", i - 1)
        };
        let audio_out = if i == clips.len() - 2 {
            "outa".to_string()
        } else {
            format!("xa{i}")
        };

        graph = graph.chain(
            FilterChain::new()
                .input(audio_in_a)
                .input(format!("{}:a", clips[i + 1].input_index))
                .filter(Filter::new("acrossfade").param("d", format_value(clamped_dur)))
                .output(audio_out),
        );

        // Update accumulated duration
        accumulated_duration = accumulated_duration + clip_b_dur - clamped_dur;
    }

    graph
}

/// Builds a layout-based graph (spatial composition with overlay/scale).
fn build_layout_graph(
    clips: &[CompositionClip],
    layout: &LayoutSpec,
    audio_mix: Option<&AudioMixSpec>,
    output_width: u32,
    output_height: u32,
) -> FilterGraph {
    let positions = layout.positions();
    let mut graph = FilterGraph::new();

    // Calculate canvas duration from clips
    let max_end = clips.iter().map(|c| c.timeline_end).fold(0.0_f64, f64::max);
    let min_start = clips
        .iter()
        .map(|c| c.timeline_start)
        .fold(f64::INFINITY, f64::min);
    let duration = max_end - min_start;

    // Pair clips with positions, sorted by z_index for overlay ordering
    let mut indexed_pairs: Vec<(usize, &CompositionClip, &LayoutPosition)> = clips
        .iter()
        .enumerate()
        .take(positions.len())
        .map(|(idx, clip)| (idx, clip, &positions[idx]))
        .collect();
    indexed_pairs.sort_by_key(|(_, _, pos)| pos.z_index());

    // Create color source canvas as the base for overlays
    graph = graph.chain(
        FilterChain::new()
            .filter(
                Filter::new("color")
                    .param("c", "black")
                    .param("s", format!("{output_width}x{output_height}"))
                    .param("d", format_value(duration))
                    .param("r", 30),
            )
            .output("canvas"),
    );

    // Scale each input to its layout dimensions
    for &(idx, clip, pos) in &indexed_pairs {
        let (_, _, pw, ph) = pos.to_pixels(output_width, output_height);
        let target_w = round_even(pw as f64);
        let target_h = round_even(ph as f64);

        graph = graph.chain(
            FilterChain::new()
                .input(format!("{}:v", clip.input_index))
                .filter(
                    Filter::new("scale")
                        .param("w", target_w)
                        .param("h", target_h)
                        .param("force_divisible_by", 2),
                )
                .output(format!("s{idx}")),
        );
    }

    // Overlay each scaled input onto the canvas in z-order
    let num_overlays = indexed_pairs.len();
    for (overlay_idx, &(idx, clip, pos)) in indexed_pairs.iter().enumerate() {
        let base_label = if overlay_idx == 0 {
            "canvas".to_string()
        } else {
            format!("ov{}", overlay_idx - 1)
        };
        let out_label = if overlay_idx == num_overlays - 1 {
            "outv".to_string()
        } else {
            format!("ov{overlay_idx}")
        };

        let (px, py, _, _) = pos.to_pixels(output_width, output_height);

        graph = graph.chain(
            FilterChain::new()
                .input(base_label)
                .input(format!("s{idx}"))
                .filter(Filter::new("overlay").param("x", px).param("y", py).param(
                    "enable",
                    format!(
                        "'between(t,{},{})'",
                        format_value(clip.timeline_start),
                        format_value(clip.timeline_end),
                    ),
                ))
                .output(out_label),
        );
    }

    // Add audio mix if provided
    if let Some(mix) = audio_mix {
        graph = add_audio_mix(graph, mix);
    }

    graph
}

/// Adds audio mix filter chains to the graph.
fn add_audio_mix(mut graph: FilterGraph, audio_mix: &AudioMixSpec) -> FilterGraph {
    let tracks = audio_mix.tracks();
    let num_tracks = tracks.len();

    // Build per-track volume/fade chains
    for (i, track) in tracks.iter().enumerate() {
        let mut filters: Vec<Filter> = Vec::new();

        // Volume filter (skip if unity gain)
        if (track.volume - 1.0).abs() > 1e-9 {
            filters.push(Filter::new("volume").param("volume", format_value(track.volume)));
        }

        // Fade-in filter (skip if 0.0)
        if track.fade_in > 0.0 {
            filters.push(
                Filter::new("afade")
                    .param("t", "in")
                    .param("d", format_value(track.fade_in)),
            );
        }

        // Fade-out filter (skip if 0.0)
        if track.fade_out > 0.0 {
            filters.push(
                Filter::new("afade")
                    .param("t", "out")
                    .param("d", format_value(track.fade_out)),
            );
        }

        if !filters.is_empty() {
            let mut chain = FilterChain::new().input(format!("{i}:a"));
            for f in filters {
                chain = chain.filter(f);
            }
            chain = chain.output(format!("a{i}"));
            graph = graph.chain(chain);
        }
    }

    // Build amix chain with labeled or raw inputs
    let mut amix_chain = FilterChain::new();
    for (i, track) in tracks.iter().enumerate() {
        let has_filters =
            (track.volume - 1.0).abs() > 1e-9 || track.fade_in > 0.0 || track.fade_out > 0.0;
        if has_filters {
            amix_chain = amix_chain.input(format!("a{i}"));
        } else {
            amix_chain = amix_chain.input(format!("{i}:a"));
        }
    }
    amix_chain = amix_chain
        .filter(Filter::new("amix").param("inputs", num_tracks))
        .output("outa");
    graph = graph.chain(amix_chain);

    graph
}

// ---------------------------------------------------------------------------
// PyO3 function bindings
// ---------------------------------------------------------------------------

/// Builds a complete FilterGraph for multi-clip composition.
///
/// This is the primary composition entry point. Builds either sequential
/// (concat/xfade) or spatial (overlay/scale) filter graphs depending on
/// whether a layout is provided.
///
/// Args:
///     clips: List of CompositionClip objects with timeline positions.
///     transitions: List of TransitionSpec for adjacent clip pairs.
///     layout: Optional LayoutSpec for spatial composition.
///     audio_mix: Optional AudioMixSpec for multi-track audio mixing.
///     output_width: Output canvas width in pixels.
///     output_height: Output canvas height in pixels.
///
/// Returns:
///     A FilterGraph ready for FFmpeg's -filter_complex argument.
#[pyfunction]
#[pyo3(name = "build_composition_graph")]
fn py_build_composition_graph(
    clips: Vec<CompositionClip>,
    transitions: Vec<TransitionSpec>,
    layout: Option<LayoutSpec>,
    audio_mix: Option<AudioMixSpec>,
    output_width: u32,
    output_height: u32,
) -> FilterGraph {
    build_composition_graph(
        &clips,
        &transitions,
        layout.as_ref(),
        audio_mix.as_ref(),
        output_width,
        output_height,
    )
}

/// Registers graph builder types and functions with the Python module.
pub fn register(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<LayoutSpec>()?;
    m.add_function(wrap_pyfunction!(py_build_composition_graph, m)?)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ffmpeg::audio::TrackAudioConfig;
    use crate::ffmpeg::transitions::TransitionType;

    fn make_clip(index: usize, start: f64, end: f64) -> CompositionClip {
        CompositionClip::new(index, start, end, 0, 0)
    }

    fn make_transition(duration: f64) -> TransitionSpec {
        TransitionSpec::new(TransitionType::Fade, duration, 0.0)
    }

    // -- LayoutSpec tests --

    #[test]
    fn layout_spec_requires_at_least_one_position() {
        let result = LayoutSpec::new(vec![]);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("at least one"));
    }

    #[test]
    fn layout_spec_single_position() {
        let spec = LayoutSpec::new(vec![LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0)]).unwrap();
        assert_eq!(spec.position_count(), 1);
    }

    #[test]
    fn layout_spec_positions_accessible() {
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
            LayoutPosition::new(0.73, 0.02, 0.25, 0.25, 1),
        ];
        let spec = LayoutSpec::new(positions).unwrap();
        assert_eq!(spec.positions().len(), 2);
    }

    // -- Empty input --

    #[test]
    fn empty_clips_returns_empty_graph() {
        let graph = build_composition_graph(&[], &[], None, None, 1920, 1080);
        assert_eq!(graph.to_string(), "");
    }

    // -- Single clip --

    #[test]
    fn single_clip_produces_scale_graph() {
        let clips = vec![make_clip(0, 0.0, 5.0)];
        let graph = build_composition_graph(&clips, &[], None, None, 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("[0:v]"), "Should reference input 0:v: {s}");
        assert!(s.contains("scale="), "Should contain scale filter: {s}");
        assert!(s.contains("w=1920"), "Should scale to 1920: {s}");
        assert!(s.contains("h=1080"), "Should scale to 1080: {s}");
        assert!(s.contains("[outv]"), "Should output to outv: {s}");
    }

    // -- Two clips, no transitions (concat) --

    #[test]
    fn two_clips_no_transitions_uses_concat() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 5.0, 10.0)];
        let graph = build_composition_graph(&clips, &[], None, None, 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("concat="), "Should use concat: {s}");
        assert!(s.contains("n=2"), "Should concat 2 segments: {s}");
        assert!(s.contains("v=1"), "Should have 1 video stream: {s}");
        assert!(s.contains("a=1"), "Should have 1 audio stream: {s}");
        assert!(s.contains("[outv]"), "Should output video: {s}");
        assert!(s.contains("[outa]"), "Should output audio: {s}");
    }

    // -- Two clips with transition (xfade + acrossfade) --

    #[test]
    fn two_clips_with_transition_uses_xfade() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let transitions = vec![make_transition(1.0)];
        let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("xfade="), "Should use xfade: {s}");
        assert!(
            s.contains("transition=fade"),
            "Should have fade transition: {s}"
        );
        assert!(s.contains("duration=1"), "Should have 1s duration: {s}");
        assert!(s.contains("offset=4"), "Offset should be 5-1=4: {s}");
        assert!(s.contains("acrossfade="), "Should use acrossfade: {s}");
        assert!(s.contains("[outv]"), "Should output video: {s}");
        assert!(s.contains("[outa]"), "Should output audio: {s}");
    }

    #[test]
    fn two_clips_xfade_correct_input_labels() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let transitions = vec![make_transition(1.0)];
        let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("[0:v][1:v]xfade="), "Video inputs: {s}");
        assert!(s.contains("[0:a][1:a]acrossfade="), "Audio inputs: {s}");
    }

    // -- Three clips with transitions --

    #[test]
    fn three_clips_with_transitions_chains_xfade() {
        let clips = vec![
            make_clip(0, 0.0, 5.0),
            make_clip(1, 0.0, 5.0),
            make_clip(2, 0.0, 5.0),
        ];
        let transitions = vec![make_transition(1.0), make_transition(1.0)];
        let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
        let s = graph.to_string();
        // First xfade: [0:v][1:v]xfade=...offset=4[xv0]
        assert!(
            s.contains("[xv0]"),
            "Should have intermediate xv0 label: {s}"
        );
        // Second xfade: [xv0][2:v]xfade=...offset=8[outv]
        assert!(s.contains("[xv0][2:v]xfade="), "Should chain xfade: {s}");
        assert!(s.contains("[outv]"), "Should output video: {s}");
        // Audio chain
        assert!(
            s.contains("[xa0]"),
            "Should have intermediate xa0 label: {s}"
        );
        assert!(
            s.contains("[xa0][2:a]acrossfade="),
            "Should chain acrossfade: {s}"
        );
        assert!(s.contains("[outa]"), "Should output audio: {s}");
    }

    #[test]
    fn three_clips_xfade_offsets_correct() {
        let clips = vec![
            make_clip(0, 0.0, 5.0),
            make_clip(1, 0.0, 5.0),
            make_clip(2, 0.0, 5.0),
        ];
        let transitions = vec![make_transition(1.0), make_transition(1.0)];
        let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
        let s = graph.to_string();
        // First xfade offset: 5-1=4
        assert!(s.contains("offset=4"), "First offset should be 4: {s}");
        // Second xfade offset: (5+5-1)-1 = 8
        assert!(s.contains("offset=8"), "Second offset should be 8: {s}");
    }

    // -- PIP layout --

    #[test]
    fn two_clips_pip_layout() {
        let clips = vec![make_clip(0, 0.0, 10.0), make_clip(1, 0.0, 10.0)];
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0), // full-screen base
            LayoutPosition::new(0.73, 0.02, 0.25, 0.25, 1), // PIP overlay
        ];
        let layout = LayoutSpec::new(positions).unwrap();
        let graph = build_composition_graph(&clips, &[], Some(&layout), None, 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("color="), "Should have canvas: {s}");
        assert!(s.contains("scale="), "Should have scale filters: {s}");
        assert!(s.contains("overlay="), "Should have overlay filter: {s}");
        assert!(s.contains("[outv]"), "Should output video: {s}");
    }

    #[test]
    fn pip_layout_correct_overlay_positions() {
        let clips = vec![make_clip(0, 0.0, 10.0), make_clip(1, 0.0, 10.0)];
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
            LayoutPosition::new(0.5, 0.5, 0.25, 0.25, 1),
        ];
        let layout = LayoutSpec::new(positions).unwrap();
        let graph = build_composition_graph(&clips, &[], Some(&layout), None, 1920, 1080);
        let s = graph.to_string();
        // First overlay (z=0 base at 0,0): overlay=x=0:y=0
        assert!(s.contains("x=0"), "Base should be at x=0: {s}");
        assert!(s.contains("y=0"), "Base should be at y=0: {s}");
        // Second overlay (z=1 pip at 0.5,0.5): overlay=x=960:y=540
        assert!(s.contains("x=960"), "PIP should be at x=960: {s}");
        assert!(s.contains("y=540"), "PIP should be at y=540: {s}");
    }

    // -- Side-by-side layout --

    #[test]
    fn two_clips_side_by_side_layout() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 0.5, 1.0, 0),
            LayoutPosition::new(0.5, 0.0, 0.5, 1.0, 0),
        ];
        let layout = LayoutSpec::new(positions).unwrap();
        let graph = build_composition_graph(&clips, &[], Some(&layout), None, 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("scale="), "Should have scale: {s}");
        assert!(s.contains("overlay="), "Should have overlay: {s}");
        assert!(s.contains("[outv]"), "Should output video: {s}");
    }

    // -- 4-clip grid layout --

    #[test]
    fn four_clips_grid_layout() {
        let clips = vec![
            make_clip(0, 0.0, 5.0),
            make_clip(1, 0.0, 5.0),
            make_clip(2, 0.0, 5.0),
            make_clip(3, 0.0, 5.0),
        ];
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0),
            LayoutPosition::new(0.5, 0.0, 0.5, 0.5, 0),
            LayoutPosition::new(0.0, 0.5, 0.5, 0.5, 0),
            LayoutPosition::new(0.5, 0.5, 0.5, 0.5, 0),
        ];
        let layout = LayoutSpec::new(positions).unwrap();
        let graph = build_composition_graph(&clips, &[], Some(&layout), None, 1920, 1080);
        let s = graph.to_string();
        // Should have 4 scale chains + 4 overlay chains + canvas
        assert!(s.contains("[s0]"), "Should have scaled input 0: {s}");
        assert!(s.contains("[s1]"), "Should have scaled input 1: {s}");
        assert!(s.contains("[s2]"), "Should have scaled input 2: {s}");
        assert!(s.contains("[s3]"), "Should have scaled input 3: {s}");
        assert!(s.contains("[outv]"), "Should output video: {s}");
    }

    #[test]
    fn four_clips_grid_has_correct_scale_dimensions() {
        let clips = vec![
            make_clip(0, 0.0, 5.0),
            make_clip(1, 0.0, 5.0),
            make_clip(2, 0.0, 5.0),
            make_clip(3, 0.0, 5.0),
        ];
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 0.5, 0.5, 0),
            LayoutPosition::new(0.5, 0.0, 0.5, 0.5, 0),
            LayoutPosition::new(0.0, 0.5, 0.5, 0.5, 0),
            LayoutPosition::new(0.5, 0.5, 0.5, 0.5, 0),
        ];
        let layout = LayoutSpec::new(positions).unwrap();
        let graph = build_composition_graph(&clips, &[], Some(&layout), None, 1920, 1080);
        let s = graph.to_string();
        // 0.5 * 1920 = 960, 0.5 * 1080 = 540 → both even
        assert!(s.contains("w=960"), "Should scale to w=960: {s}");
        assert!(s.contains("h=540"), "Should scale to h=540: {s}");
    }

    // -- Layout with audio mix --

    #[test]
    fn layout_with_audio_mix() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
            LayoutPosition::new(0.73, 0.02, 0.25, 0.25, 1),
        ];
        let layout = LayoutSpec::new(positions).unwrap();
        let tracks = vec![
            TrackAudioConfig::new(0.8, 1.0, 0.5).unwrap(),
            TrackAudioConfig::new(0.5, 0.0, 0.0).unwrap(),
        ];
        let audio_mix = AudioMixSpec::new(tracks).unwrap();
        let graph =
            build_composition_graph(&clips, &[], Some(&layout), Some(&audio_mix), 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("overlay="), "Should have overlay: {s}");
        assert!(s.contains("volume="), "Should have volume filter: {s}");
        assert!(s.contains("afade="), "Should have fade filter: {s}");
        assert!(s.contains("amix="), "Should have amix: {s}");
        assert!(s.contains("[outv]"), "Should output video: {s}");
        assert!(s.contains("[outa]"), "Should output audio: {s}");
    }

    #[test]
    fn audio_mix_unity_tracks_skip_volume_filter() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let positions = vec![
            LayoutPosition::new(0.0, 0.0, 1.0, 1.0, 0),
            LayoutPosition::new(0.73, 0.02, 0.25, 0.25, 1),
        ];
        let layout = LayoutSpec::new(positions).unwrap();
        let tracks = vec![
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(), // unity, no fades
            TrackAudioConfig::new(1.0, 0.0, 0.0).unwrap(), // unity, no fades
        ];
        let audio_mix = AudioMixSpec::new(tracks).unwrap();
        let graph =
            build_composition_graph(&clips, &[], Some(&layout), Some(&audio_mix), 1920, 1080);
        let s = graph.to_string();
        // Should have amix but no volume/fade filters
        assert!(s.contains("amix="), "Should have amix: {s}");
        assert!(!s.contains("volume="), "Should skip volume filter: {s}");
        assert!(!s.contains("afade="), "Should skip fade filters: {s}");
        // Amix should reference raw inputs directly
        assert!(s.contains("[0:a]"), "Should reference raw input 0:a: {s}");
        assert!(s.contains("[1:a]"), "Should reference raw input 1:a: {s}");
    }

    // -- Edge cases --

    #[test]
    fn zero_duration_transition() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let transitions = vec![make_transition(0.0)];
        let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
        let s = graph.to_string();
        // Should still produce xfade with 0 duration and offset=5
        assert!(s.contains("xfade="), "Should use xfade: {s}");
        assert!(s.contains("duration=0"), "Duration should be 0: {s}");
        assert!(s.contains("offset=5"), "Offset should be 5: {s}");
    }

    #[test]
    fn transition_clamped_to_shorter_clip() {
        // 2s and 3s clips, transition 5s → clamped to 2s
        let clips = vec![make_clip(0, 0.0, 2.0), make_clip(1, 0.0, 3.0)];
        let transitions = vec![make_transition(5.0)];
        let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
        let s = graph.to_string();
        // Clamped to min(2, 3) = 2, offset = 2-2 = 0
        assert!(
            s.contains("duration=2"),
            "Duration should be clamped to 2: {s}"
        );
        assert!(s.contains("offset=0"), "Offset should be 0: {s}");
    }

    #[test]
    fn non_zero_input_indices() {
        let clips = vec![make_clip(2, 0.0, 5.0), make_clip(5, 0.0, 5.0)];
        let graph = build_composition_graph(&clips, &[], None, None, 1920, 1080);
        let s = graph.to_string();
        assert!(s.contains("[2:v]"), "Should reference input 2:v: {s}");
        assert!(s.contains("[2:a]"), "Should reference input 2:a: {s}");
        assert!(s.contains("[5:v]"), "Should reference input 5:v: {s}");
        assert!(s.contains("[5:a]"), "Should reference input 5:a: {s}");
    }

    // -- format_value tests --

    #[test]
    fn format_value_integer() {
        assert_eq!(format_value(5.0), "5");
        assert_eq!(format_value(0.0), "0");
        assert_eq!(format_value(10.0), "10");
    }

    #[test]
    fn format_value_fractional() {
        assert_eq!(format_value(1.5), "1.5");
        assert_eq!(format_value(0.25), "0.25");
    }

    // -- round_even tests --

    #[test]
    fn round_even_already_even() {
        assert_eq!(round_even(100.0), 100);
    }

    #[test]
    fn round_even_rounds_up_odd() {
        assert_eq!(round_even(101.0), 102);
    }

    #[test]
    fn round_even_minimum() {
        assert_eq!(round_even(0.0), 2);
        assert_eq!(round_even(1.0), 2);
    }
}

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use crate::ffmpeg::transitions::TransitionType;
    use proptest::prelude::*;

    fn arb_clip(index: usize) -> impl Strategy<Value = CompositionClip> {
        (0.1f64..=300.0).prop_map(move |duration| CompositionClip::new(index, 0.0, duration, 0, 0))
    }

    fn arb_clips(min: usize, max: usize) -> impl Strategy<Value = Vec<CompositionClip>> {
        proptest::collection::vec(0.1f64..=300.0, min..=max).prop_map(|durations| {
            durations
                .into_iter()
                .enumerate()
                .map(|(i, dur)| CompositionClip::new(i, 0.0, dur, 0, 0))
                .collect()
        })
    }

    fn arb_transition() -> impl Strategy<Value = TransitionSpec> {
        (0.0f64..=60.0).prop_map(|dur| TransitionSpec::new(TransitionType::Fade, dur, 0.0))
    }

    proptest! {
        #[test]
        fn no_panics_sequential(
            clips in arb_clips(1, 8),
            transitions in proptest::collection::vec(arb_transition(), 0..=7),
        ) {
            let graph = build_composition_graph(&clips, &transitions, None, None, 1920, 1080);
            let _ = graph.to_string();
        }

        #[test]
        fn no_panics_layout(
            num_clips in 2usize..=4,
        ) {
            let clips: Vec<CompositionClip> = (0..num_clips)
                .map(|i| CompositionClip::new(i, 0.0, 5.0, 0, 0))
                .collect();
            let positions: Vec<LayoutPosition> = (0..num_clips)
                .map(|i| {
                    let x = (i % 2) as f64 * 0.5;
                    let y = (i / 2) as f64 * 0.5;
                    LayoutPosition::new(x, y, 0.5, 0.5, i as i32)
                })
                .collect();
            let layout = LayoutSpec::new(positions).unwrap();
            let graph = build_composition_graph(&clips, &[], Some(&layout), None, 1920, 1080);
            let _ = graph.to_string();
        }

        #[test]
        fn output_contains_outv_for_multi_clip(
            clips in arb_clips(2, 6),
        ) {
            let graph = build_composition_graph(&clips, &[], None, None, 1920, 1080);
            let s = graph.to_string();
            prop_assert!(s.contains("[outv]"), "Must contain [outv]: {}", s);
        }
    }
}
