//! Render plan types and builder logic.
//!
//! Decomposes composition data (clips, transitions, layout, audio) into a
//! `RenderPlan` containing ordered, non-overlapping `RenderSegment`s that
//! cover the full timeline without gaps.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use crate::compose::graph::LayoutSpec;
use crate::compose::timeline::{
    calculate_composition_positions, calculate_timeline_duration, CompositionClip, TransitionSpec,
};
use crate::ffmpeg::audio::AudioMixSpec;

// ---------------------------------------------------------------------------
// Supported values for validation
// ---------------------------------------------------------------------------

/// Allowed output container formats.
const OUTPUT_FORMATS: &[&str] = &["mp4", "mkv", "webm", "mov", "avi"];

/// Allowed video codecs (must match sanitize module's VIDEO_CODECS).
const VIDEO_CODECS: &[&str] = &[
    "libx264", "libx265", "libvpx", "libvpx-vp9", "libaom-av1", "prores_ks",
];

/// Allowed quality presets.
const QUALITY_PRESETS: &[&str] = &[
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
    "placebo",
];

// ---------------------------------------------------------------------------
// Core types
// ---------------------------------------------------------------------------

/// Settings controlling how a render is executed.
///
/// Contains the output format, resolution, codec, quality preset, and frame
/// rate. Use `validate_render_settings()` to check these before building a
/// render plan.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct RenderSettings {
    /// Output container format (e.g., "mp4", "mkv").
    #[pyo3(get)]
    pub output_format: String,
    /// Output width in pixels.
    #[pyo3(get)]
    pub width: u32,
    /// Output height in pixels.
    #[pyo3(get)]
    pub height: u32,
    /// Video codec (e.g., "libx264", "libx265").
    #[pyo3(get)]
    pub codec: String,
    /// Quality preset (e.g., "fast", "medium", "slow").
    #[pyo3(get)]
    pub quality_preset: String,
    /// Frames per second for the output.
    #[pyo3(get)]
    pub fps: f64,
}

#[pymethods]
impl RenderSettings {
    /// Creates a new RenderSettings.
    ///
    /// Args:
    ///     output_format: Container format (e.g., "mp4").
    ///     width: Output width in pixels.
    ///     height: Output height in pixels.
    ///     codec: Video codec (e.g., "libx264").
    ///     quality_preset: Encoding preset (e.g., "medium").
    ///     fps: Output frame rate.
    #[new]
    pub fn py_new(
        output_format: String,
        width: u32,
        height: u32,
        codec: String,
        quality_preset: String,
        fps: f64,
    ) -> Self {
        Self::new(output_format, width, height, codec, quality_preset, fps)
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderSettings(format={}, {}x{}, codec={}, preset={}, fps={})",
            self.output_format, self.width, self.height, self.codec, self.quality_preset, self.fps
        )
    }
}

impl RenderSettings {
    /// Creates a new RenderSettings.
    pub fn new(
        output_format: String,
        width: u32,
        height: u32,
        codec: String,
        quality_preset: String,
        fps: f64,
    ) -> Self {
        Self {
            output_format,
            width,
            height,
            codec,
            quality_preset,
            fps,
        }
    }
}

/// A single non-overlapping segment of the render timeline.
///
/// Segments partition the full timeline so their durations sum to the
/// total render duration with no gaps or overlaps.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct RenderSegment {
    /// Zero-based segment index.
    #[pyo3(get)]
    pub index: usize,
    /// Start time on the composition timeline in seconds.
    #[pyo3(get)]
    pub timeline_start: f64,
    /// End time on the composition timeline in seconds.
    #[pyo3(get)]
    pub timeline_end: f64,
    /// Number of frames in this segment.
    #[pyo3(get)]
    pub frame_count: u64,
    /// Estimated cost (proportional to frame count × active clip count).
    #[pyo3(get)]
    pub cost_estimate: f64,
}

#[pymethods]
impl RenderSegment {
    /// Creates a new RenderSegment.
    ///
    /// Args:
    ///     index: Zero-based segment index.
    ///     timeline_start: Start time in seconds.
    ///     timeline_end: End time in seconds.
    ///     frame_count: Number of frames in this segment.
    ///     cost_estimate: Estimated rendering cost.
    #[new]
    pub fn py_new(
        index: usize,
        timeline_start: f64,
        timeline_end: f64,
        frame_count: u64,
        cost_estimate: f64,
    ) -> Self {
        Self::new(index, timeline_start, timeline_end, frame_count, cost_estimate)
    }

    /// Returns the duration of this segment in seconds.
    #[pyo3(name = "duration")]
    fn py_duration(&self) -> f64 {
        self.duration()
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderSegment(index={}, {:.3}-{:.3}, frames={}, cost={:.1})",
            self.index, self.timeline_start, self.timeline_end, self.frame_count, self.cost_estimate
        )
    }
}

impl RenderSegment {
    /// Creates a new RenderSegment.
    pub fn new(
        index: usize,
        timeline_start: f64,
        timeline_end: f64,
        frame_count: u64,
        cost_estimate: f64,
    ) -> Self {
        Self {
            index,
            timeline_start,
            timeline_end,
            frame_count,
            cost_estimate,
        }
    }

    /// Returns the duration of this segment in seconds.
    pub fn duration(&self) -> f64 {
        self.timeline_end - self.timeline_start
    }
}

/// A complete render plan decomposed from composition data.
///
/// Contains ordered, non-overlapping segments covering the full timeline
/// duration, along with aggregate totals and the render settings.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct RenderPlan {
    /// Ordered list of non-overlapping segments.
    pub segments: Vec<RenderSegment>,
    /// Total frame count across all segments.
    #[pyo3(get)]
    pub total_frames: u64,
    /// Total timeline duration in seconds.
    #[pyo3(get)]
    pub total_duration: f64,
    /// Render settings for this plan.
    pub settings: RenderSettings,
}

#[pymethods]
impl RenderPlan {
    /// Creates a new RenderPlan.
    ///
    /// Args:
    ///     segments: Ordered list of RenderSegment.
    ///     total_frames: Total frame count.
    ///     total_duration: Total duration in seconds.
    ///     settings: Render settings.
    #[new]
    pub fn py_new(
        segments: Vec<RenderSegment>,
        total_frames: u64,
        total_duration: f64,
        settings: RenderSettings,
    ) -> Self {
        Self {
            segments,
            total_frames,
            total_duration,
            settings,
        }
    }

    /// Returns the list of segments.
    #[pyo3(name = "segments")]
    fn py_segments(&self) -> Vec<RenderSegment> {
        self.segments.clone()
    }

    /// Returns the render settings.
    #[pyo3(name = "settings")]
    fn py_settings(&self) -> RenderSettings {
        self.settings.clone()
    }

    /// Returns the number of segments.
    #[pyo3(name = "segment_count")]
    fn py_segment_count(&self) -> usize {
        self.segments.len()
    }

    /// Returns the total estimated cost.
    #[pyo3(name = "total_cost")]
    fn py_total_cost(&self) -> f64 {
        self.segments.iter().map(|s| s.cost_estimate).sum()
    }

    fn __repr__(&self) -> String {
        format!(
            "RenderPlan(segments={}, frames={}, duration={:.3}s, {})",
            self.segments.len(),
            self.total_frames,
            self.total_duration,
            self.settings.__repr__()
        )
    }
}

// ---------------------------------------------------------------------------
// Plan builder
// ---------------------------------------------------------------------------

/// Builds a render plan from composition inputs.
///
/// Decomposes the timeline into non-overlapping segments at clip boundary
/// points (starts and ends). Uses `calculate_composition_positions()` from
/// `compose::timeline` for transition clamping (NFR-002).
///
/// Segments that overlap due to transitions are split so the transition
/// region becomes its own segment with a higher cost estimate (2× base cost).
///
/// # Arguments
///
/// * `clips` - Source clips with timeline positions
/// * `transitions` - Transitions between adjacent clips
/// * `_layout` - Optional layout spec (reserved for future spatial cost hints)
/// * `_audio_mix` - Optional audio mix spec (reserved for future audio segments)
/// * `_output_width` - Output width in pixels (used by downstream command builder)
/// * `_output_height` - Output height in pixels (used by downstream command builder)
/// * `settings` - Render settings (fps used for frame count calculation)
pub fn build_render_plan(
    clips: &[CompositionClip],
    transitions: &[TransitionSpec],
    _layout: Option<&LayoutSpec>,
    _audio_mix: Option<&AudioMixSpec>,
    _output_width: u32,
    _output_height: u32,
    settings: &RenderSettings,
) -> RenderPlan {
    if clips.is_empty() {
        return RenderPlan {
            segments: Vec::new(),
            total_frames: 0,
            total_duration: 0.0,
            settings: settings.clone(),
        };
    }

    // Reuse composition timeline logic for clamping (NFR-002)
    let positioned = calculate_composition_positions(clips, transitions);
    let total_duration = calculate_timeline_duration(clips, transitions);

    // Collect all boundary points from positioned clips
    let mut boundaries: Vec<f64> = Vec::new();
    for clip in &positioned {
        boundaries.push(clip.timeline_start);
        boundaries.push(clip.timeline_end);
    }
    // Sort and deduplicate (with floating-point tolerance)
    boundaries.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    boundaries.dedup_by(|a, b| (*a - *b).abs() < 1e-9);

    // Build segments between consecutive boundary points
    let fps = settings.fps.max(1.0);
    let mut segments = Vec::new();
    for i in 0..boundaries.len().saturating_sub(1) {
        let start = boundaries[i];
        let end = boundaries[i + 1];
        let duration = end - start;
        if duration < 1e-9 {
            continue;
        }

        // Count how many positioned clips are active during this segment
        let active_clips = positioned
            .iter()
            .filter(|c| c.timeline_start < end - 1e-9 && c.timeline_end > start + 1e-9)
            .count();

        let frame_count = (duration * fps).round() as u64;
        let cost_estimate = frame_count as f64 * active_clips.max(1) as f64;

        segments.push(RenderSegment::new(
            segments.len(),
            start,
            end,
            frame_count,
            cost_estimate,
        ));
    }

    let total_frames = segments.iter().map(|s| s.frame_count).sum();

    RenderPlan {
        segments,
        total_frames,
        total_duration,
        settings: settings.clone(),
    }
}

// ---------------------------------------------------------------------------
// Settings validation
// ---------------------------------------------------------------------------

/// Validates render settings before plan execution.
///
/// Checks that:
/// - Output format is a supported container (mp4, mkv, webm, mov, avi)
/// - Resolution is non-zero
/// - Codec is in the supported list
/// - Quality preset is recognised
/// - FPS is positive
///
/// Returns `Ok(())` on success or an error message describing the problem.
pub fn validate_render_settings(settings: &RenderSettings) -> Result<(), String> {
    if settings.output_format.is_empty() {
        return Err("output_format must not be empty".into());
    }
    if !OUTPUT_FORMATS.contains(&settings.output_format.as_str()) {
        return Err(format!(
            "unsupported output_format '{}'; allowed: {}",
            settings.output_format,
            OUTPUT_FORMATS.join(", ")
        ));
    }
    if settings.width == 0 || settings.height == 0 {
        return Err(format!(
            "resolution must be non-zero, got {}x{}",
            settings.width, settings.height
        ));
    }
    if !VIDEO_CODECS.contains(&settings.codec.as_str()) {
        return Err(format!(
            "unsupported codec '{}'; allowed: {}",
            settings.codec,
            VIDEO_CODECS.join(", ")
        ));
    }
    if !QUALITY_PRESETS.contains(&settings.quality_preset.as_str()) {
        return Err(format!(
            "unsupported quality_preset '{}'; allowed: {}",
            settings.quality_preset,
            QUALITY_PRESETS.join(", ")
        ));
    }
    if settings.fps <= 0.0 {
        return Err(format!("fps must be positive, got {}", settings.fps));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// PyO3 function bindings
// ---------------------------------------------------------------------------

/// Builds a render plan from composition data.
///
/// Decomposes the timeline into ordered segments with frame counts and cost
/// estimates. Uses composition timeline logic for transition clamping.
///
/// Args:
///     clips: List of CompositionClip with timeline positions.
///     transitions: List of TransitionSpec for adjacent clip pairs.
///     layout: Optional LayoutSpec for spatial composition.
///     audio_mix: Optional AudioMixSpec for audio mixing.
///     output_width: Output width in pixels.
///     output_height: Output height in pixels.
///     settings: RenderSettings controlling format, resolution, codec, fps.
///
/// Returns:
///     A RenderPlan with segments, total_frames, total_duration, and settings.
#[pyfunction]
#[pyo3(name = "build_render_plan")]
pub fn py_build_render_plan(
    clips: Vec<CompositionClip>,
    transitions: Vec<TransitionSpec>,
    layout: Option<LayoutSpec>,
    audio_mix: Option<AudioMixSpec>,
    output_width: u32,
    output_height: u32,
    settings: RenderSettings,
) -> RenderPlan {
    build_render_plan(
        &clips,
        &transitions,
        layout.as_ref(),
        audio_mix.as_ref(),
        output_width,
        output_height,
        &settings,
    )
}

/// Validates render settings before execution.
///
/// Checks output format, resolution, codec, quality preset, and fps.
///
/// Args:
///     settings: RenderSettings to validate.
///
/// Raises:
///     ValueError: If any setting is invalid, with a descriptive message.
#[pyfunction]
#[pyo3(name = "validate_render_settings")]
pub fn py_validate_render_settings(settings: &RenderSettings) -> PyResult<()> {
    validate_render_settings(settings).map_err(PyValueError::new_err)
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ffmpeg::transitions::TransitionType;

    fn make_clip(index: usize, start: f64, end: f64) -> CompositionClip {
        CompositionClip::new(index, start, end, 0, 0)
    }

    fn make_transition(duration: f64) -> TransitionSpec {
        TransitionSpec::new(TransitionType::Fade, duration, 0.0)
    }

    fn default_settings() -> RenderSettings {
        RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0)
    }

    // -- Empty input --

    #[test]
    fn empty_clips_returns_empty_plan() {
        let plan = build_render_plan(&[], &[], None, None, 1920, 1080, &default_settings());
        assert!(plan.segments.is_empty());
        assert_eq!(plan.total_frames, 0);
        assert!((plan.total_duration - 0.0).abs() < 1e-9);
    }

    // -- Single clip --

    #[test]
    fn single_clip_produces_one_segment() {
        let clips = vec![make_clip(0, 0.0, 5.0)];
        let plan = build_render_plan(&clips, &[], None, None, 1920, 1080, &default_settings());
        assert_eq!(plan.segments.len(), 1);
        assert!((plan.segments[0].timeline_start - 0.0).abs() < 1e-9);
        assert!((plan.segments[0].timeline_end - 5.0).abs() < 1e-9);
        assert_eq!(plan.segments[0].frame_count, 150); // 5s * 30fps
        assert_eq!(plan.total_frames, 150);
        assert!((plan.total_duration - 5.0).abs() < 1e-9);
    }

    // -- Multi-clip, no transitions --

    #[test]
    fn two_clips_no_transitions_two_segments() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 3.0)];
        let plan = build_render_plan(&clips, &[], None, None, 1920, 1080, &default_settings());
        assert_eq!(plan.segments.len(), 2);
        // Segment 0: 0-5s
        assert!((plan.segments[0].timeline_start - 0.0).abs() < 1e-9);
        assert!((plan.segments[0].timeline_end - 5.0).abs() < 1e-9);
        assert_eq!(plan.segments[0].frame_count, 150);
        // Segment 1: 5-8s
        assert!((plan.segments[1].timeline_start - 5.0).abs() < 1e-9);
        assert!((plan.segments[1].timeline_end - 8.0).abs() < 1e-9);
        assert_eq!(plan.segments[1].frame_count, 90);
        // Totals
        assert_eq!(plan.total_frames, 240); // 8s * 30fps
        assert!((plan.total_duration - 8.0).abs() < 1e-9);
    }

    // -- Transition-containing composition --

    #[test]
    fn two_clips_with_transition_three_segments() {
        // Clips: A=5s, B=5s, transition=1s
        // Positioned: A=0-5, B=4-9 -> boundaries [0, 4, 5, 9]
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let transitions = vec![make_transition(1.0)];
        let plan =
            build_render_plan(&clips, &transitions, None, None, 1920, 1080, &default_settings());
        assert_eq!(plan.segments.len(), 3);
        // Segment 0: 0-4 (clip A only)
        assert!((plan.segments[0].timeline_start - 0.0).abs() < 1e-9);
        assert!((plan.segments[0].timeline_end - 4.0).abs() < 1e-9);
        assert_eq!(plan.segments[0].frame_count, 120);
        // Segment 1: 4-5 (transition, both clips active)
        assert!((plan.segments[1].timeline_start - 4.0).abs() < 1e-9);
        assert!((plan.segments[1].timeline_end - 5.0).abs() < 1e-9);
        assert_eq!(plan.segments[1].frame_count, 30);
        // Transition segment has higher cost (2 active clips)
        assert!((plan.segments[1].cost_estimate - 60.0).abs() < 1e-9);
        // Segment 2: 5-9 (clip B only)
        assert!((plan.segments[2].timeline_start - 5.0).abs() < 1e-9);
        assert!((plan.segments[2].timeline_end - 9.0).abs() < 1e-9);
        assert_eq!(plan.segments[2].frame_count, 120);
        // Total: 9s * 30fps = 270
        assert_eq!(plan.total_frames, 270);
        assert!((plan.total_duration - 9.0).abs() < 1e-9);
    }

    // -- Segments cover full duration without gaps or overlaps (FR-002) --

    #[test]
    fn segments_sum_equals_total_duration() {
        let clips = vec![
            make_clip(0, 0.0, 5.0),
            make_clip(1, 0.0, 4.0),
            make_clip(2, 0.0, 6.0),
        ];
        let transitions = vec![make_transition(1.0), make_transition(2.0)];
        let plan =
            build_render_plan(&clips, &transitions, None, None, 1920, 1080, &default_settings());
        let segment_sum: f64 = plan.segments.iter().map(|s| s.duration()).sum();
        assert!(
            (segment_sum - plan.total_duration).abs() < 1e-9,
            "segment sum {} != total duration {}",
            segment_sum,
            plan.total_duration
        );
    }

    #[test]
    fn segments_contiguous_no_gaps() {
        let clips = vec![
            make_clip(0, 0.0, 5.0),
            make_clip(1, 0.0, 4.0),
            make_clip(2, 0.0, 6.0),
        ];
        let transitions = vec![make_transition(1.0), make_transition(2.0)];
        let plan =
            build_render_plan(&clips, &transitions, None, None, 1920, 1080, &default_settings());
        for i in 1..plan.segments.len() {
            assert!(
                (plan.segments[i].timeline_start - plan.segments[i - 1].timeline_end).abs() < 1e-9,
                "gap between segment {} and {}",
                i - 1,
                i
            );
        }
    }

    // -- Frame counts match FPS × duration --

    #[test]
    fn frame_counts_match_fps_times_duration() {
        let clips = vec![make_clip(0, 0.0, 10.0)];
        let settings =
            RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 24.0);
        let plan = build_render_plan(&clips, &[], None, None, 1920, 1080, &settings);
        assert_eq!(plan.segments[0].frame_count, 240); // 10s * 24fps
    }

    // -- Segment indices are sequential --

    #[test]
    fn segment_indices_sequential() {
        let clips = vec![make_clip(0, 0.0, 3.0), make_clip(1, 0.0, 4.0)];
        let transitions = vec![make_transition(1.0)];
        let plan =
            build_render_plan(&clips, &transitions, None, None, 1920, 1080, &default_settings());
        for (i, seg) in plan.segments.iter().enumerate() {
            assert_eq!(seg.index, i);
        }
    }

    // -- validate_render_settings --

    #[test]
    fn valid_settings_pass() {
        assert!(validate_render_settings(&default_settings()).is_ok());
    }

    #[test]
    fn all_supported_formats_pass() {
        for fmt in OUTPUT_FORMATS {
            let settings =
                RenderSettings::new(fmt.to_string(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
            assert!(validate_render_settings(&settings).is_ok(), "format {fmt} should pass");
        }
    }

    #[test]
    fn all_supported_codecs_pass() {
        for codec in VIDEO_CODECS {
            let settings =
                RenderSettings::new("mp4".into(), 1920, 1080, codec.to_string(), "medium".into(), 30.0);
            assert!(
                validate_render_settings(&settings).is_ok(),
                "codec {codec} should pass"
            );
        }
    }

    #[test]
    fn empty_format_rejected() {
        let settings =
            RenderSettings::new("".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("output_format"), "error: {err}");
    }

    #[test]
    fn unsupported_format_rejected() {
        let settings =
            RenderSettings::new("flv".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("unsupported"), "error: {err}");
    }

    #[test]
    fn zero_width_rejected() {
        let settings =
            RenderSettings::new("mp4".into(), 0, 1080, "libx264".into(), "medium".into(), 30.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("resolution"), "error: {err}");
    }

    #[test]
    fn zero_height_rejected() {
        let settings =
            RenderSettings::new("mp4".into(), 1920, 0, "libx264".into(), "medium".into(), 30.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("resolution"), "error: {err}");
    }

    #[test]
    fn unsupported_codec_rejected() {
        let settings =
            RenderSettings::new("mp4".into(), 1920, 1080, "rawvideo".into(), "medium".into(), 30.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("codec"), "error: {err}");
    }

    #[test]
    fn unsupported_preset_rejected() {
        let settings =
            RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "turbo".into(), 30.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("quality_preset"), "error: {err}");
    }

    #[test]
    fn zero_fps_rejected() {
        let settings =
            RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 0.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("fps"), "error: {err}");
    }

    #[test]
    fn negative_fps_rejected() {
        let settings =
            RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), -1.0);
        let err = validate_render_settings(&settings).unwrap_err();
        assert!(err.contains("fps"), "error: {err}");
    }

    // -- RenderSegment::duration() --

    #[test]
    fn segment_duration() {
        let seg = RenderSegment::new(0, 1.0, 4.5, 105, 105.0);
        assert!((seg.duration() - 3.5).abs() < 1e-9);
    }

    // -- RenderPlan repr --

    #[test]
    fn render_plan_repr() {
        let plan = RenderPlan {
            segments: vec![RenderSegment::new(0, 0.0, 5.0, 150, 150.0)],
            total_frames: 150,
            total_duration: 5.0,
            settings: default_settings(),
        };
        let repr = plan.__repr__();
        assert!(repr.contains("segments=1"));
        assert!(repr.contains("frames=150"));
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

    fn arb_settings() -> impl Strategy<Value = RenderSettings> {
        (
            prop_oneof![
                Just("mp4".to_string()),
                Just("mkv".to_string()),
                Just("webm".to_string()),
            ],
            1u32..=7680,
            1u32..=4320,
            prop_oneof![
                Just("libx264".to_string()),
                Just("libx265".to_string()),
                Just("libvpx-vp9".to_string()),
            ],
            prop_oneof![
                Just("fast".to_string()),
                Just("medium".to_string()),
                Just("slow".to_string()),
            ],
            prop_oneof![Just(24.0f64), Just(30.0), Just(60.0)],
        )
            .prop_map(
                |(output_format, width, height, codec, quality_preset, fps)| {
                    RenderSettings::new(output_format, width, height, codec, quality_preset, fps)
                },
            )
    }

    proptest! {
        /// FR-002: Segments always cover full timeline duration.
        #[test]
        fn segments_cover_full_duration(
            clips in arb_clips(1, 10),
            transitions in proptest::collection::vec(arb_transition(), 0..=9),
        ) {
            let settings = RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
            let plan = build_render_plan(&clips, &transitions, None, None, 1920, 1080, &settings);
            let segment_sum: f64 = plan.segments.iter().map(|s| s.duration()).sum();
            prop_assert!(
                (segment_sum - plan.total_duration).abs() < 1e-6,
                "segment sum {} != total duration {}", segment_sum, plan.total_duration
            );
        }

        /// Segments are contiguous (no gaps or overlaps).
        #[test]
        fn segments_contiguous(
            clips in arb_clips(1, 10),
            transitions in proptest::collection::vec(arb_transition(), 0..=9),
        ) {
            let settings = RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
            let plan = build_render_plan(&clips, &transitions, None, None, 1920, 1080, &settings);
            for i in 1..plan.segments.len() {
                let gap = (plan.segments[i].timeline_start - plan.segments[i - 1].timeline_end).abs();
                prop_assert!(gap < 1e-9, "gap {} between segments {} and {}", gap, i - 1, i);
            }
        }

        /// No panics with arbitrary inputs.
        #[test]
        fn no_panics_random_inputs(
            clips in arb_clips(0, 10),
            transitions in proptest::collection::vec(arb_transition(), 0..=9),
        ) {
            let settings = RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
            let _ = build_render_plan(&clips, &transitions, None, None, 1920, 1080, &settings);
        }

        /// Validation never panics on arbitrary settings.
        #[test]
        fn validation_never_panics(
            output_format in "[a-z]{0,10}",
            width in 0u32..=10000,
            height in 0u32..=10000,
            codec in "[a-z0-9_-]{0,20}",
            preset in "[a-z]{0,15}",
            fps in -100.0f64..=200.0,
        ) {
            let settings = RenderSettings::new(output_format, width, height, codec, preset, fps);
            let _ = validate_render_settings(&settings);
        }

        /// Valid settings always pass validation.
        #[test]
        fn valid_settings_always_pass(
            settings in arb_settings(),
        ) {
            prop_assert!(validate_render_settings(&settings).is_ok(),
                "valid settings should pass: {:?}", settings);
        }

        /// FR-004: Zero-length clips, single-clip, all-transition-overlap, mismatched durations.
        #[test]
        fn extreme_composition_inputs(
            clip_count in 1usize..=5,
            clip_dur in 0.01f64..=100.0,
            trans_dur in 0.0f64..=200.0,
        ) {
            let clips: Vec<CompositionClip> = (0..clip_count)
                .map(|i| CompositionClip::new(i, 0.0, clip_dur, 0, 0))
                .collect();
            let transitions: Vec<TransitionSpec> = (0..clip_count.saturating_sub(1))
                .map(|_| TransitionSpec::new(TransitionType::Fade, trans_dur, 0.0))
                .collect();
            let settings = RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
            let plan = build_render_plan(&clips, &transitions, None, None, 1920, 1080, &settings);
            // Segments should still cover full duration
            let segment_sum: f64 = plan.segments.iter().map(|s| s.duration()).sum();
            prop_assert!(
                (segment_sum - plan.total_duration).abs() < 1e-6,
                "segment sum {} != total duration {}", segment_sum, plan.total_duration
            );
        }
    }
}

// ---------------------------------------------------------------------------
// PyO3 binding tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod pyo3_tests {
    use super::*;

    #[test]
    fn test_build_render_plan_pyo3() {
        pyo3::prepare_freethreaded_python();
        pyo3::Python::with_gil(|_py| {
            let clips = vec![
                CompositionClip::new(0, 0.0, 5.0, 0, 0),
                CompositionClip::new(1, 0.0, 5.0, 0, 0),
            ];
            let settings =
                RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
            let plan = build_render_plan(&clips, &[], None, None, 1920, 1080, &settings);
            assert_eq!(plan.segments.len(), 2);
            assert_eq!(plan.total_frames, 300);
        });
    }

    #[test]
    fn test_validate_render_settings_pyo3() {
        pyo3::prepare_freethreaded_python();
        pyo3::Python::with_gil(|_py| {
            let valid =
                RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
            assert!(validate_render_settings(&valid).is_ok());

            let invalid =
                RenderSettings::new("".into(), 0, 0, "rawvideo".into(), "turbo".into(), 0.0);
            assert!(validate_render_settings(&invalid).is_err());
        });
    }
}

// ---------------------------------------------------------------------------
// Contract tests (serialization round-trip)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod contract_tests {
    use super::*;

    /// Tests that RenderPlan can round-trip through a manual JSON-like
    /// representation, verifying structural integrity without adding serde.
    #[test]
    fn render_plan_structural_round_trip() {
        let settings =
            RenderSettings::new("mp4".into(), 1920, 1080, "libx264".into(), "medium".into(), 30.0);
        let segments = vec![
            RenderSegment::new(0, 0.0, 4.0, 120, 120.0),
            RenderSegment::new(1, 4.0, 5.0, 30, 60.0),
            RenderSegment::new(2, 5.0, 9.0, 120, 120.0),
        ];
        let plan = RenderPlan {
            segments: segments.clone(),
            total_frames: 270,
            total_duration: 9.0,
            settings: settings.clone(),
        };

        // "Serialize" to field values
        let seg_data: Vec<(usize, f64, f64, u64, f64)> = plan
            .segments
            .iter()
            .map(|s| {
                (
                    s.index,
                    s.timeline_start,
                    s.timeline_end,
                    s.frame_count,
                    s.cost_estimate,
                )
            })
            .collect();

        // "Deserialize" back
        let restored_segments: Vec<RenderSegment> = seg_data
            .into_iter()
            .map(|(idx, start, end, frames, cost)| RenderSegment::new(idx, start, end, frames, cost))
            .collect();
        let restored = RenderPlan {
            segments: restored_segments,
            total_frames: plan.total_frames,
            total_duration: plan.total_duration,
            settings: RenderSettings::new(
                plan.settings.output_format.clone(),
                plan.settings.width,
                plan.settings.height,
                plan.settings.codec.clone(),
                plan.settings.quality_preset.clone(),
                plan.settings.fps,
            ),
        };

        assert_eq!(plan, restored);
    }
}
