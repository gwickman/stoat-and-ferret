//! Multi-clip timeline composition calculator.
//!
//! Calculates clip positions on a timeline accounting for transition overlaps.
//! Transition durations are clamped to prevent negative-duration clips.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::compose::timeline::{
//!     CompositionClip, TransitionSpec, calculate_composition_positions,
//!     calculate_timeline_duration,
//! };
//! use stoat_ferret_core::ffmpeg::transitions::TransitionType;
//!
//! let clips = vec![
//!     CompositionClip::new(0, 0.0, 5.0, 0, 0),
//!     CompositionClip::new(1, 5.0, 10.0, 0, 0),
//! ];
//! let transitions = vec![
//!     TransitionSpec::new(TransitionType::Fade, 1.0, 0.0),
//! ];
//! let result = calculate_composition_positions(&clips, &transitions);
//! assert_eq!(result.len(), 2);
//! // Second clip starts 1s earlier due to transition overlap
//! assert!((result[1].timeline_start - 4.0).abs() < 1e-9);
//! ```

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use crate::ffmpeg::transitions::TransitionType;

/// A clip positioned on the composition timeline.
///
/// Represents a single input clip with its calculated timeline position,
/// track assignment, and z-ordering for multi-layer composition.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct CompositionClip {
    /// Index of the input source (0-based).
    #[pyo3(get)]
    pub input_index: usize,
    /// Start time on the composition timeline in seconds.
    #[pyo3(get)]
    pub timeline_start: f64,
    /// End time on the composition timeline in seconds.
    #[pyo3(get)]
    pub timeline_end: f64,
    /// Track index for multi-track layouts.
    #[pyo3(get)]
    pub track_index: u32,
    /// Z-order for layering (higher = on top).
    #[pyo3(get)]
    pub z_index: i32,
}

#[pymethods]
impl CompositionClip {
    /// Creates a new CompositionClip.
    ///
    /// Args:
    ///     input_index: Index of the input source (0-based).
    ///     timeline_start: Start time in seconds.
    ///     timeline_end: End time in seconds.
    ///     track_index: Track index for multi-track layouts.
    ///     z_index: Z-order for layering.
    #[new]
    pub fn py_new(
        input_index: usize,
        timeline_start: f64,
        timeline_end: f64,
        track_index: u32,
        z_index: i32,
    ) -> Self {
        Self::new(
            input_index,
            timeline_start,
            timeline_end,
            track_index,
            z_index,
        )
    }

    /// Returns the duration of this clip in seconds.
    #[pyo3(name = "duration")]
    fn py_duration(&self) -> f64 {
        self.duration()
    }
}

impl CompositionClip {
    /// Creates a new CompositionClip.
    pub fn new(
        input_index: usize,
        timeline_start: f64,
        timeline_end: f64,
        track_index: u32,
        z_index: i32,
    ) -> Self {
        Self {
            input_index,
            timeline_start,
            timeline_end,
            track_index,
            z_index,
        }
    }

    /// Returns the duration of this clip in seconds.
    pub fn duration(&self) -> f64 {
        self.timeline_end - self.timeline_start
    }
}

/// Specifies a transition between two adjacent clips.
///
/// The transition duration defines how much the clips overlap on the timeline.
/// Duration is clamped during calculation to prevent negative-duration clips.
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct TransitionSpec {
    /// The type of transition effect.
    #[pyo3(get)]
    pub transition_type: TransitionType,
    /// Duration of the transition overlap in seconds.
    #[pyo3(get)]
    pub duration: f64,
    /// Offset adjustment for transition timing in seconds.
    #[pyo3(get)]
    pub offset: f64,
}

#[pymethods]
impl TransitionSpec {
    /// Creates a new TransitionSpec.
    ///
    /// Args:
    ///     transition_type: The type of transition effect.
    ///     duration: Duration of the transition overlap in seconds.
    ///     offset: Offset adjustment for transition timing.
    #[new]
    pub fn py_new(transition_type: TransitionType, duration: f64, offset: f64) -> Self {
        Self::new(transition_type, duration, offset)
    }
}

impl TransitionSpec {
    /// Creates a new TransitionSpec.
    pub fn new(transition_type: TransitionType, duration: f64, offset: f64) -> Self {
        Self {
            transition_type,
            duration,
            offset,
        }
    }
}

/// Clamps a transition duration so it doesn't exceed either adjacent clip's duration.
fn clamp_transition_duration(
    transition_duration: f64,
    clip_a_duration: f64,
    clip_b_duration: f64,
) -> f64 {
    transition_duration
        .min(clip_a_duration)
        .min(clip_b_duration)
        .max(0.0)
}

/// Calculates composition positions for clips with transition overlaps.
///
/// For each adjacent pair of clips, the transition duration creates an overlap
/// where the outgoing clip's end region and incoming clip's start region play
/// simultaneously. Transition durations are clamped to
/// `min(clip_n.duration, clip_n+1.duration)` to prevent negative-duration clips.
///
/// Returns a new `Vec<CompositionClip>` with adjusted timeline positions.
/// Empty input returns empty output. Single-clip input returns unchanged.
pub fn calculate_composition_positions(
    clips: &[CompositionClip],
    transitions: &[TransitionSpec],
) -> Vec<CompositionClip> {
    if clips.is_empty() {
        return Vec::new();
    }

    let mut result = Vec::with_capacity(clips.len());

    // First clip keeps its original position
    let first = &clips[0];
    let mut current_start = first.timeline_start;
    let mut current_end = first.timeline_start + first.duration();
    result.push(CompositionClip::new(
        first.input_index,
        current_start,
        current_end,
        first.track_index,
        first.z_index,
    ));

    for i in 1..clips.len() {
        let clip = &clips[i];
        let clip_duration = clip.duration();

        // Get transition overlap for this pair (if available)
        let overlap = if i - 1 < transitions.len() {
            let prev_duration = result[i - 1].duration();
            clamp_transition_duration(transitions[i - 1].duration, prev_duration, clip_duration)
        } else {
            0.0
        };

        // New clip starts where previous ended minus the overlap
        current_start = current_end - overlap;
        current_end = current_start + clip_duration;

        result.push(CompositionClip::new(
            clip.input_index,
            current_start,
            current_end,
            clip.track_index,
            clip.z_index,
        ));
    }

    result
}

/// Calculates the total timeline duration accounting for transition overlaps.
///
/// The total duration is the sum of all clip durations minus the sum of all
/// clamped transition overlaps.
pub fn calculate_timeline_duration(
    clips: &[CompositionClip],
    transitions: &[TransitionSpec],
) -> f64 {
    if clips.is_empty() {
        return 0.0;
    }

    let positions = calculate_composition_positions(clips, transitions);
    // Duration is from start of first clip to end of last clip
    let first_start = positions[0].timeline_start;
    let last_end = positions[positions.len() - 1].timeline_end;
    last_end - first_start
}

// ---------------------------------------------------------------------------
// PyO3 function bindings
// ---------------------------------------------------------------------------

/// Calculates composition positions for clips with transition overlaps.
///
/// For each adjacent pair of clips, the transition duration creates an overlap.
/// Transition durations are clamped to min(clip_n.duration, clip_n+1.duration).
///
/// Args:
///     clips: List of CompositionClip objects with input positions.
///     transitions: List of TransitionSpec objects for adjacent pairs.
///
/// Returns:
///     List of CompositionClip with adjusted timeline positions.
#[pyfunction]
#[pyo3(name = "calculate_composition_positions")]
fn py_calculate_composition_positions(
    clips: Vec<CompositionClip>,
    transitions: Vec<TransitionSpec>,
) -> Vec<CompositionClip> {
    calculate_composition_positions(&clips, &transitions)
}

/// Calculates total timeline duration accounting for transition overlaps.
///
/// Args:
///     clips: List of CompositionClip objects.
///     transitions: List of TransitionSpec objects for adjacent pairs.
///
/// Returns:
///     Total duration in seconds.
#[pyfunction]
#[pyo3(name = "calculate_timeline_duration")]
fn py_calculate_timeline_duration(
    clips: Vec<CompositionClip>,
    transitions: Vec<TransitionSpec>,
) -> f64 {
    calculate_timeline_duration(&clips, &transitions)
}

/// Registers timeline composition types and functions with the Python module.
pub fn register(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<CompositionClip>()?;
    m.add_class::<TransitionSpec>()?;
    m.add_function(wrap_pyfunction!(py_calculate_composition_positions, m)?)?;
    m.add_function(wrap_pyfunction!(py_calculate_timeline_duration, m)?)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_clip(index: usize, start: f64, end: f64) -> CompositionClip {
        CompositionClip::new(index, start, end, 0, 0)
    }

    fn make_transition(duration: f64) -> TransitionSpec {
        TransitionSpec::new(TransitionType::Fade, duration, 0.0)
    }

    // -- CompositionClip tests --

    #[test]
    fn clip_fields_accessible() {
        let clip = CompositionClip::new(2, 1.0, 6.0, 1, 3);
        assert_eq!(clip.input_index, 2);
        assert!((clip.timeline_start - 1.0).abs() < 1e-9);
        assert!((clip.timeline_end - 6.0).abs() < 1e-9);
        assert_eq!(clip.track_index, 1);
        assert_eq!(clip.z_index, 3);
    }

    #[test]
    fn clip_duration() {
        let clip = CompositionClip::new(0, 2.0, 7.0, 0, 0);
        assert!((clip.duration() - 5.0).abs() < 1e-9);
    }

    // -- TransitionSpec tests --

    #[test]
    fn transition_fields_accessible() {
        let t = TransitionSpec::new(TransitionType::Wipeleft, 1.5, 0.25);
        assert_eq!(t.transition_type, TransitionType::Wipeleft);
        assert!((t.duration - 1.5).abs() < 1e-9);
        assert!((t.offset - 0.25).abs() < 1e-9);
    }

    // -- Empty input --

    #[test]
    fn empty_input_returns_empty() {
        let result = calculate_composition_positions(&[], &[]);
        assert!(result.is_empty());
        assert!((calculate_timeline_duration(&[], &[]) - 0.0).abs() < 1e-9);
    }

    // -- Single clip --

    #[test]
    fn single_clip_unchanged() {
        let clips = vec![make_clip(0, 0.0, 5.0)];
        let result = calculate_composition_positions(&clips, &[]);
        assert_eq!(result.len(), 1);
        assert!((result[0].timeline_start - 0.0).abs() < 1e-9);
        assert!((result[0].timeline_end - 5.0).abs() < 1e-9);
        assert!((calculate_timeline_duration(&clips, &[]) - 5.0).abs() < 1e-9);
    }

    // -- Two clips, no transitions --

    #[test]
    fn two_clips_no_transitions_concatenated() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 3.0)];
        let result = calculate_composition_positions(&clips, &[]);
        assert_eq!(result.len(), 2);
        assert!((result[0].timeline_start - 0.0).abs() < 1e-9);
        assert!((result[0].timeline_end - 5.0).abs() < 1e-9);
        assert!((result[1].timeline_start - 5.0).abs() < 1e-9);
        assert!((result[1].timeline_end - 8.0).abs() < 1e-9);
        assert!((calculate_timeline_duration(&clips, &[]) - 8.0).abs() < 1e-9);
    }

    // -- Two clips with 1s transition --

    #[test]
    fn two_clips_with_transition() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let transitions = vec![make_transition(1.0)];
        let result = calculate_composition_positions(&clips, &transitions);
        assert_eq!(result.len(), 2);
        assert!((result[0].timeline_start - 0.0).abs() < 1e-9);
        assert!((result[0].timeline_end - 5.0).abs() < 1e-9);
        assert!((result[1].timeline_start - 4.0).abs() < 1e-9);
        assert!((result[1].timeline_end - 9.0).abs() < 1e-9);
        assert!((calculate_timeline_duration(&clips, &transitions) - 9.0).abs() < 1e-9);
    }

    // -- Three clips with varying transitions --

    #[test]
    fn three_clips_with_varying_transitions() {
        let clips = vec![
            make_clip(0, 0.0, 5.0),
            make_clip(1, 0.0, 4.0),
            make_clip(2, 0.0, 6.0),
        ];
        let transitions = vec![make_transition(1.0), make_transition(2.0)];
        let result = calculate_composition_positions(&clips, &transitions);
        assert_eq!(result.len(), 3);
        // Clip 0: 0-5
        assert!((result[0].timeline_start - 0.0).abs() < 1e-9);
        assert!((result[0].timeline_end - 5.0).abs() < 1e-9);
        // Clip 1: starts at 5-1=4, ends at 4+4=8
        assert!((result[1].timeline_start - 4.0).abs() < 1e-9);
        assert!((result[1].timeline_end - 8.0).abs() < 1e-9);
        // Clip 2: starts at 8-2=6, ends at 6+6=12
        assert!((result[2].timeline_start - 6.0).abs() < 1e-9);
        assert!((result[2].timeline_end - 12.0).abs() < 1e-9);
        // Total: 12 - 0 = 12  (15 total - 1 - 2 transitions)
        assert!((calculate_timeline_duration(&clips, &transitions) - 12.0).abs() < 1e-9);
    }

    // -- Transition clamping --

    #[test]
    fn transition_clamped_to_shorter_clip() {
        // Clips: 2s and 3s, transition 5s -> clamped to 2s
        let clips = vec![make_clip(0, 0.0, 2.0), make_clip(1, 0.0, 3.0)];
        let transitions = vec![make_transition(5.0)];
        let result = calculate_composition_positions(&clips, &transitions);
        // Transition clamped to min(2, 3) = 2
        assert!((result[1].timeline_start - 0.0).abs() < 1e-9);
        assert!((result[1].timeline_end - 3.0).abs() < 1e-9);
        // Duration: 2 + 3 - 2 = 3
        assert!((calculate_timeline_duration(&clips, &transitions) - 3.0).abs() < 1e-9);
    }

    #[test]
    fn transition_equal_to_clip_duration() {
        // Clips: 3s and 5s, transition exactly 3s
        let clips = vec![make_clip(0, 0.0, 3.0), make_clip(1, 0.0, 5.0)];
        let transitions = vec![make_transition(3.0)];
        let result = calculate_composition_positions(&clips, &transitions);
        // Clamped to min(3, 5) = 3, so clip 1 starts at 3-3=0
        assert!((result[1].timeline_start - 0.0).abs() < 1e-9);
        assert!((result[1].timeline_end - 5.0).abs() < 1e-9);
        // No negative durations
        assert!(result[0].duration() > -1e-9);
        assert!(result[1].duration() > -1e-9);
    }

    // -- Zero-duration transition --

    #[test]
    fn zero_duration_transition() {
        let clips = vec![make_clip(0, 0.0, 5.0), make_clip(1, 0.0, 5.0)];
        let transitions = vec![make_transition(0.0)];
        let result = calculate_composition_positions(&clips, &transitions);
        // Same as no transition
        assert!((result[1].timeline_start - 5.0).abs() < 1e-9);
        assert!((result[1].timeline_end - 10.0).abs() < 1e-9);
        assert!((calculate_timeline_duration(&clips, &transitions) - 10.0).abs() < 1e-9);
    }

    // -- Preserves metadata --

    #[test]
    fn preserves_input_index_and_track() {
        let clips = vec![
            CompositionClip::new(3, 0.0, 5.0, 1, 2),
            CompositionClip::new(7, 0.0, 4.0, 1, 5),
        ];
        let result = calculate_composition_positions(&clips, &[]);
        assert_eq!(result[0].input_index, 3);
        assert_eq!(result[0].track_index, 1);
        assert_eq!(result[0].z_index, 2);
        assert_eq!(result[1].input_index, 7);
        assert_eq!(result[1].track_index, 1);
        assert_eq!(result[1].z_index, 5);
    }
}

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
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
        fn no_panics_random_inputs(
            clips in arb_clips(1, 10),
            transitions in proptest::collection::vec(arb_transition(), 0..=9),
        ) {
            let _ = calculate_composition_positions(&clips, &transitions);
            let _ = calculate_timeline_duration(&clips, &transitions);
        }

        #[test]
        fn total_duration_non_negative(
            clips in arb_clips(1, 10),
            transitions in proptest::collection::vec(arb_transition(), 0..=9),
        ) {
            let duration = calculate_timeline_duration(&clips, &transitions);
            prop_assert!(duration >= 0.0, "Duration must be non-negative: {}", duration);
        }

        #[test]
        fn start_times_non_negative_and_monotonic(
            clips in arb_clips(1, 10),
            transitions in proptest::collection::vec(arb_transition(), 0..=9),
        ) {
            let result = calculate_composition_positions(&clips, &transitions);
            for (i, clip) in result.iter().enumerate() {
                prop_assert!(
                    clip.timeline_start >= -1e-9,
                    "Clip {} start must be non-negative: {}", i, clip.timeline_start
                );
                if i > 0 {
                    prop_assert!(
                        clip.timeline_start >= result[i - 1].timeline_start - 1e-9,
                        "Clip {} start ({}) must be >= clip {} start ({})",
                        i, clip.timeline_start, i - 1, result[i - 1].timeline_start
                    );
                }
            }
        }

        #[test]
        fn total_duration_lte_sum_of_clip_durations(
            clips in arb_clips(1, 10),
            transitions in proptest::collection::vec(arb_transition(), 0..=9),
        ) {
            let sum_durations: f64 = clips.iter().map(|c| c.duration()).sum();
            let total = calculate_timeline_duration(&clips, &transitions);
            prop_assert!(
                total <= sum_durations + 1e-9,
                "Total {} must be <= sum of durations {}", total, sum_durations
            );
        }

        #[test]
        fn transition_clamping_prevents_negative_durations(
            clip_a_dur in 0.1f64..=300.0,
            clip_b_dur in 0.1f64..=300.0,
            trans_dur in 0.0f64..=600.0,
        ) {
            let clips = vec![
                CompositionClip::new(0, 0.0, clip_a_dur, 0, 0),
                CompositionClip::new(1, 0.0, clip_b_dur, 0, 0),
            ];
            let transitions = vec![TransitionSpec::new(TransitionType::Fade, trans_dur, 0.0)];
            let result = calculate_composition_positions(&clips, &transitions);
            for (i, clip) in result.iter().enumerate() {
                prop_assert!(
                    clip.duration() >= -1e-9,
                    "Clip {} has negative duration: {}", i, clip.duration()
                );
            }
        }
    }
}
