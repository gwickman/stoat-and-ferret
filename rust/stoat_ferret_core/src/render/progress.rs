//! FFmpeg progress output parsing, progress calculation, and segment aggregation.
//!
//! Parses `-progress pipe:1` output for real-time progress tracking, calculates
//! completion ratio (0.0–1.0) and ETA, and aggregates multi-segment progress
//! weighted by duration.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::render::progress::{calculate_progress, aggregate_segment_progress};
//!
//! let progress = calculate_progress(500_000, 1_000_000);
//! assert!((progress - 0.5).abs() < 1e-9);
//!
//! let aggregate = aggregate_segment_progress(&[(0.5, 10.0), (1.0, 10.0)]);
//! assert!((aggregate - 0.75).abs() < 1e-9);
//! ```

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// A single progress update parsed from FFmpeg `-progress pipe:1` output.
///
/// Each block of key=value lines terminated by `progress=continue` or
/// `progress=end` produces one update. Fields that FFmpeg omits (e.g.,
/// `frame`/`fps` for audio-only streams) are `None`.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct FfmpegProgressUpdate {
    /// Frame number reached (None for audio-only streams).
    #[pyo3(get)]
    pub frame: Option<i64>,
    /// Current encoding speed in fps (None for audio-only streams).
    #[pyo3(get)]
    pub fps: Option<f64>,
    /// Output time in microseconds (primary progress metric).
    #[pyo3(get)]
    pub out_time_us: i64,
    /// Current bitrate string (e.g., "1234.5kbits/s" or "N/A").
    #[pyo3(get)]
    pub bitrate: String,
    /// Encoding speed multiplier string (e.g., "1.5x" or "N/A").
    #[pyo3(get)]
    pub speed: String,
    /// True when this is the final progress block (`progress=end`).
    #[pyo3(get)]
    pub progress_end: bool,
}

/// Calculated progress information for a render job.
///
/// Combines the raw completion ratio with optional ETA and frame counts.
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, PartialEq)]
pub struct ProgressInfo {
    /// Completion ratio clamped to [0.0, 1.0].
    #[pyo3(get)]
    pub progress: f64,
    /// Estimated seconds remaining, or None if progress is zero.
    #[pyo3(get)]
    pub eta_seconds: Option<f64>,
    /// Frames encoded so far (None if unknown).
    #[pyo3(get)]
    pub frames_done: Option<i64>,
    /// Total frames expected (None if unknown).
    #[pyo3(get)]
    pub total_frames: Option<i64>,
}

#[pymethods]
impl ProgressInfo {
    /// Creates a new ProgressInfo.
    #[new]
    #[pyo3(signature = (progress, eta_seconds=None, frames_done=None, total_frames=None))]
    fn py_new(
        progress: f64,
        eta_seconds: Option<f64>,
        frames_done: Option<i64>,
        total_frames: Option<i64>,
    ) -> Self {
        Self {
            progress: progress.clamp(0.0, 1.0),
            eta_seconds,
            frames_done,
            total_frames,
        }
    }
}

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

/// Parses FFmpeg `-progress pipe:1` output into progress updates.
///
/// Each block of `key=value` lines terminated by `progress=continue` or
/// `progress=end` produces one [`FfmpegProgressUpdate`]. Handles the
/// documented deviation where `out_time_ms` actually reports microseconds.
///
/// Leading whitespace in values (e.g., `bitrate=   1234kbits/s`) is trimmed.
pub fn parse_ffmpeg_progress(output: &str) -> Vec<FfmpegProgressUpdate> {
    let mut updates = Vec::new();
    let mut frame: Option<i64> = None;
    let mut fps: Option<f64> = None;
    let mut out_time_us: i64 = 0;
    let mut bitrate = String::from("N/A");
    let mut speed = String::from("N/A");

    for line in output.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else {
            continue;
        };
        let key = key.trim();
        let value = value.trim();

        match key {
            "frame" => {
                frame = value.parse().ok();
            }
            "fps" => {
                fps = value.parse().ok();
            }
            "out_time_us" => {
                out_time_us = value.parse().unwrap_or(0);
            }
            // NFR-002: out_time_ms actually reports microseconds, not milliseconds.
            // Use it as fallback if out_time_us wasn't set yet.
            "out_time_ms" if out_time_us == 0 => {
                out_time_us = value.parse().unwrap_or(0);
            }
            "bitrate" => {
                bitrate = value.to_string();
            }
            "speed" => {
                speed = value.to_string();
            }
            "progress" => {
                let progress_end = value == "end";
                updates.push(FfmpegProgressUpdate {
                    frame,
                    fps,
                    out_time_us,
                    bitrate: bitrate.clone(),
                    speed: speed.clone(),
                    progress_end,
                });
                // Reset for next block
                frame = None;
                fps = None;
                out_time_us = 0;
                bitrate = String::from("N/A");
                speed = String::from("N/A");
            }
            _ => {}
        }
    }

    updates
}

// ---------------------------------------------------------------------------
// Calculation
// ---------------------------------------------------------------------------

/// Calculates render progress as a ratio in [0.0, 1.0].
///
/// Returns 0.0 when `total_duration_us` is zero or negative.
/// Result is clamped to [0.0, 1.0] for all inputs.
pub fn calculate_progress(current_time_us: i64, total_duration_us: i64) -> f64 {
    if total_duration_us <= 0 {
        return 0.0;
    }
    let ratio = current_time_us as f64 / total_duration_us as f64;
    ratio.clamp(0.0, 1.0)
}

/// Estimates remaining time in seconds.
///
/// Formula: `eta = (elapsed / progress) * (1 - progress)`.
/// Returns `None` when progress is zero (cannot estimate).
pub fn estimate_eta(elapsed_seconds: f64, progress: f64) -> Option<f64> {
    if progress <= 0.0 || progress >= 1.0 {
        return None;
    }
    let total_estimated = elapsed_seconds / progress;
    Some(total_estimated * (1.0 - progress))
}

/// Aggregates per-segment progress into an overall progress ratio.
///
/// Each tuple is `(segment_progress, segment_duration)`. Segments are
/// weighted by their proportion of the total duration. Returns 0.0 if all
/// durations are zero. Result is clamped to [0.0, 1.0].
pub fn aggregate_segment_progress(segments: &[(f64, f64)]) -> f64 {
    let total_duration: f64 = segments.iter().map(|(_, d)| d.max(0.0)).sum();
    if total_duration <= 0.0 {
        return 0.0;
    }
    let weighted: f64 = segments
        .iter()
        .map(|(p, d)| p.clamp(0.0, 1.0) * d.max(0.0))
        .sum();
    (weighted / total_duration).clamp(0.0, 1.0)
}

// ---------------------------------------------------------------------------
// PyO3 bindings
// ---------------------------------------------------------------------------

/// Parses FFmpeg `-progress pipe:1` output into progress update objects.
#[pyfunction]
#[pyo3(name = "parse_ffmpeg_progress")]
pub fn py_parse_ffmpeg_progress(output: &str) -> Vec<FfmpegProgressUpdate> {
    parse_ffmpeg_progress(output)
}

/// Calculates render progress as a ratio in [0.0, 1.0].
#[pyfunction]
#[pyo3(name = "calculate_progress")]
pub fn py_calculate_progress(current_time_us: i64, total_duration_us: i64) -> f64 {
    calculate_progress(current_time_us, total_duration_us)
}

/// Estimates remaining time in seconds from elapsed time and progress ratio.
#[pyfunction]
#[pyo3(name = "estimate_eta")]
pub fn py_estimate_eta(elapsed_seconds: f64, progress: f64) -> Option<f64> {
    estimate_eta(elapsed_seconds, progress)
}

/// Aggregates per-segment progress into an overall progress ratio.
///
/// Each tuple is `(segment_progress, segment_duration)`. Segments are
/// weighted by their proportion of the total duration.
#[pyfunction]
#[pyo3(name = "aggregate_segment_progress")]
pub fn py_aggregate_segment_progress(segments: Vec<(f64, f64)>) -> f64 {
    aggregate_segment_progress(&segments)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // -- Fixtures --

    /// Real FFmpeg `-progress pipe:1` output captured from an actual encode.
    const FFMPEG_PROGRESS_FIXTURE: &str = "\
frame=0
fps=0.00
stream_0_0_q=0.0
bitrate=N/A
total_size=0
out_time_us=0
out_time_ms=0
out_time=00:00:00.000000
dup_frames=0
drop_frames=0
speed=N/A
progress=continue
frame=28
fps=0.00
stream_0_0_q=29.0
bitrate=   0.4kbits/s
total_size=48
out_time_us=866667
out_time_ms=866667
out_time=00:00:00.866667
dup_frames=0
drop_frames=0
speed=1.69x
progress=continue
frame=60
fps=58.82
stream_0_0_q=29.0
bitrate=   1.2kbits/s
total_size=200
out_time_us=2000000
out_time_ms=2000000
out_time=00:00:02.000000
dup_frames=0
drop_frames=0
speed=1.96x
progress=end";

    /// Audio-only progress output (no frame/fps fields).
    const AUDIO_ONLY_FIXTURE: &str = "\
bitrate=  128.0kbits/s
total_size=16000
out_time_us=1000000
out_time_ms=1000000
out_time=00:00:01.000000
speed=5.00x
progress=continue
bitrate=  128.0kbits/s
total_size=32000
out_time_us=2000000
out_time_ms=2000000
out_time=00:00:02.000000
speed=4.50x
progress=end";

    // -- parse_ffmpeg_progress tests --

    #[test]
    fn test_parse_full_fixture() {
        let updates = parse_ffmpeg_progress(FFMPEG_PROGRESS_FIXTURE);
        assert_eq!(updates.len(), 3);
    }

    #[test]
    fn test_parse_first_block_edge_cases() {
        let updates = parse_ffmpeg_progress(FFMPEG_PROGRESS_FIXTURE);
        let first = &updates[0];
        assert_eq!(first.frame, Some(0));
        assert_eq!(first.fps, Some(0.0));
        assert_eq!(first.out_time_us, 0);
        assert_eq!(first.bitrate, "N/A");
        assert_eq!(first.speed, "N/A");
        assert!(!first.progress_end);
    }

    #[test]
    fn test_parse_middle_block() {
        let updates = parse_ffmpeg_progress(FFMPEG_PROGRESS_FIXTURE);
        let mid = &updates[1];
        assert_eq!(mid.frame, Some(28));
        assert_eq!(mid.out_time_us, 866667);
        // Bitrate has leading whitespace trimmed
        assert_eq!(mid.bitrate, "0.4kbits/s");
        assert_eq!(mid.speed, "1.69x");
        assert!(!mid.progress_end);
    }

    #[test]
    fn test_parse_final_block_progress_end() {
        let updates = parse_ffmpeg_progress(FFMPEG_PROGRESS_FIXTURE);
        let last = &updates[2];
        assert_eq!(last.frame, Some(60));
        assert_eq!(last.out_time_us, 2_000_000);
        assert!(last.progress_end);
    }

    #[test]
    fn test_parse_audio_only() {
        let updates = parse_ffmpeg_progress(AUDIO_ONLY_FIXTURE);
        assert_eq!(updates.len(), 2);
        // Audio-only: no frame or fps
        assert_eq!(updates[0].frame, None);
        assert_eq!(updates[0].fps, None);
        assert_eq!(updates[0].out_time_us, 1_000_000);
        assert!(!updates[0].progress_end);
        assert!(updates[1].progress_end);
    }

    #[test]
    fn test_parse_empty_input() {
        let updates = parse_ffmpeg_progress("");
        assert!(updates.is_empty());
    }

    #[test]
    fn test_parse_out_time_ms_fallback() {
        // NFR-002: out_time_ms reports microseconds. If out_time_us is missing,
        // out_time_ms should be used as fallback.
        let input = "\
out_time_ms=500000
bitrate=N/A
speed=N/A
progress=continue";
        let updates = parse_ffmpeg_progress(input);
        assert_eq!(updates.len(), 1);
        assert_eq!(updates[0].out_time_us, 500_000);
    }

    #[test]
    fn test_parse_out_time_us_takes_precedence() {
        // When both out_time_us and out_time_ms are present, out_time_us wins.
        let input = "\
out_time_us=1000000
out_time_ms=999999
progress=continue";
        let updates = parse_ffmpeg_progress(input);
        assert_eq!(updates[0].out_time_us, 1_000_000);
    }

    // -- calculate_progress tests --

    #[test]
    fn test_progress_zero_time() {
        assert_eq!(calculate_progress(0, 1_000_000), 0.0);
    }

    #[test]
    fn test_progress_at_total_duration() {
        assert_eq!(calculate_progress(1_000_000, 1_000_000), 1.0);
    }

    #[test]
    fn test_progress_halfway() {
        let p = calculate_progress(500_000, 1_000_000);
        assert!((p - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_progress_zero_total() {
        assert_eq!(calculate_progress(100, 0), 0.0);
    }

    #[test]
    fn test_progress_negative_total() {
        assert_eq!(calculate_progress(100, -1), 0.0);
    }

    #[test]
    fn test_progress_clamped_above_one() {
        // current > total should clamp to 1.0
        assert_eq!(calculate_progress(2_000_000, 1_000_000), 1.0);
    }

    #[test]
    fn test_progress_negative_current() {
        // negative current should clamp to 0.0
        assert_eq!(calculate_progress(-100, 1_000_000), 0.0);
    }

    // -- estimate_eta tests --

    #[test]
    fn test_eta_at_50_percent() {
        // 10s elapsed, 50% done → 10s remaining
        let eta = estimate_eta(10.0, 0.5).unwrap();
        assert!((eta - 10.0).abs() < 1e-9);
    }

    #[test]
    fn test_eta_at_zero_progress() {
        assert!(estimate_eta(10.0, 0.0).is_none());
    }

    #[test]
    fn test_eta_at_complete() {
        assert!(estimate_eta(10.0, 1.0).is_none());
    }

    #[test]
    fn test_eta_at_25_percent() {
        // 5s elapsed, 25% done → total ~20s, remaining ~15s
        let eta = estimate_eta(5.0, 0.25).unwrap();
        assert!((eta - 15.0).abs() < 1e-9);
    }

    // -- aggregate_segment_progress tests --

    #[test]
    fn test_aggregate_equal_segments() {
        let segments = vec![(0.5, 10.0), (0.5, 10.0)];
        let agg = aggregate_segment_progress(&segments);
        assert!((agg - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_aggregate_weighted_by_duration() {
        // 10s segment at 100%, 30s segment at 0% → weighted = 10/40 = 0.25
        let segments = vec![(1.0, 10.0), (0.0, 30.0)];
        let agg = aggregate_segment_progress(&segments);
        assert!((agg - 0.25).abs() < 1e-9);
    }

    #[test]
    fn test_aggregate_single_segment() {
        let segments = vec![(0.75, 10.0)];
        let agg = aggregate_segment_progress(&segments);
        assert!((agg - 0.75).abs() < 1e-9);
    }

    #[test]
    fn test_aggregate_empty_segments() {
        let agg = aggregate_segment_progress(&[]);
        assert_eq!(agg, 0.0);
    }

    #[test]
    fn test_aggregate_zero_total_duration() {
        let segments = vec![(0.5, 0.0), (0.8, 0.0)];
        let agg = aggregate_segment_progress(&segments);
        assert_eq!(agg, 0.0);
    }

    #[test]
    fn test_aggregate_clamps_progress() {
        // Even if individual progress is clamped, the aggregate is also clamped
        let segments = vec![(1.5, 10.0)]; // invalid but we clamp
        let agg = aggregate_segment_progress(&segments);
        assert!((agg - 1.0).abs() < 1e-9);
    }

    // -- Contract tests --

    #[test]
    fn test_contract_multiple_blocks() {
        // Verify parsing of real multi-block output works end-to-end
        let updates = parse_ffmpeg_progress(FFMPEG_PROGRESS_FIXTURE);
        assert_eq!(updates.len(), 3);

        // Calculate progress at each update for a 2-second total duration
        let total_us = 2_000_000i64;
        let p0 = calculate_progress(updates[0].out_time_us, total_us);
        let p1 = calculate_progress(updates[1].out_time_us, total_us);
        let p2 = calculate_progress(updates[2].out_time_us, total_us);

        assert_eq!(p0, 0.0);
        assert!(p1 > 0.0 && p1 < 1.0);
        assert_eq!(p2, 1.0);

        // Progress should be monotonically increasing
        assert!(p0 <= p1);
        assert!(p1 <= p2);
    }

    #[test]
    fn test_contract_audio_only_no_frame() {
        let updates = parse_ffmpeg_progress(AUDIO_ONLY_FIXTURE);
        for update in &updates {
            assert!(update.frame.is_none());
            assert!(update.fps.is_none());
            assert!(update.out_time_us > 0);
        }
    }

    // -- PyO3 binding tests --

    #[test]
    fn test_pyo3_parse_ffmpeg_progress() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let result = py_parse_ffmpeg_progress(FFMPEG_PROGRESS_FIXTURE);
            assert_eq!(result.len(), 3);
            // Verify convertible to Python objects
            let py_list = pyo3::types::PyList::new(
                py,
                result.iter().map(|u| u.clone().into_pyobject(py).unwrap()),
            )
            .unwrap();
            assert_eq!(py_list.len(), 3);
        });
    }

    #[test]
    fn test_pyo3_calculate_progress() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let result = py_calculate_progress(500_000, 1_000_000);
            assert!((result - 0.5).abs() < 1e-9);
        });
    }

    #[test]
    fn test_pyo3_estimate_eta() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let result = py_estimate_eta(10.0, 0.5);
            assert_eq!(result, Some(10.0));
        });
    }

    #[test]
    fn test_pyo3_aggregate_segment_progress() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|_py| {
            let result = py_aggregate_segment_progress(vec![(0.5, 10.0), (1.0, 10.0)]);
            assert!((result - 0.75).abs() < 1e-9);
        });
    }
}

// ---------------------------------------------------------------------------
// Property-based tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        /// FR-005: calculate_progress always returns a value in [0.0, 1.0].
        #[test]
        fn progress_always_bounded(
            current in -1_000_000_000i64..=1_000_000_000i64,
            total in -1_000_000_000i64..=1_000_000_000i64,
        ) {
            let p = calculate_progress(current, total);
            prop_assert!(p >= 0.0 && p <= 1.0, "progress {} out of bounds", p);
        }

        /// FR-005: aggregate_segment_progress always returns a value in [0.0, 1.0].
        #[test]
        fn aggregate_always_bounded(
            segments in prop::collection::vec(
                (-10.0f64..=10.0, -10.0f64..=10.0),
                0..=20,
            ),
        ) {
            let agg = aggregate_segment_progress(&segments);
            prop_assert!(agg >= 0.0 && agg <= 1.0, "aggregate {} out of bounds", agg);
        }

        /// ETA is always non-negative when progress is in (0, 1).
        #[test]
        fn eta_always_non_negative(
            elapsed in 0.001f64..=10000.0,
            progress in 0.001f64..=0.999,
        ) {
            let eta = estimate_eta(elapsed, progress);
            if let Some(e) = eta {
                prop_assert!(e >= 0.0, "eta {} is negative", e);
            }
        }
    }
}
