//! Timeline mathematics for frame-accurate video editing.
//!
//! This module provides types and functions for precise timeline calculations:
//!
//! - [`FrameRate`] - Rational representation of frame rates (e.g., 24000/1001 for 23.976 fps)
//! - [`Position`] - A point in time represented as a frame count
//! - [`Duration`] - A span of time represented as a frame count
//! - [`TimeRange`] - A contiguous time range with overlap detection and set operations
//!
//! All types use integer frame counts internally to ensure frame-accurate
//! calculations without floating-point precision issues.
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::timeline::{FrameRate, Position, Duration};
//!
//! // Work with 24 fps footage
//! let fps = FrameRate::FPS_24;
//!
//! // Create positions from seconds
//! let start = Position::from_seconds(10.0, fps);
//! let end = Position::from_seconds(15.5, fps);
//!
//! // Calculate duration between positions
//! let duration = Duration::between(start, end).unwrap();
//! assert_eq!(duration.to_seconds(fps), 5.5);
//!
//! // Work with NTSC frame rates (23.976 fps)
//! let ntsc = FrameRate::FPS_23_976;
//! let pos = Position::from_frames(24000);
//! // 24000 frames at 24000/1001 fps = 1001 seconds
//! let seconds = pos.to_seconds(ntsc);
//! assert!((seconds - 1001.0).abs() < 1e-10);
//! ```

mod duration;
mod framerate;
mod position;
mod range;

pub use duration::Duration;
pub use framerate::FrameRate;
pub use position::Position;
pub use range::{
    find_gaps, merge_ranges, py_find_gaps, py_merge_ranges, py_total_coverage, total_coverage,
    RangeError, TimeRange,
};

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        /// Property test: frame -> seconds -> frame round-trip should be exact.
        #[test]
        fn round_trip_position_integer_fps(frames in 0u64..1_000_000_000) {
            let pos = Position::from_frames(frames);
            let fps = FrameRate::FPS_24;
            let seconds = pos.to_seconds(fps);
            let back = Position::from_seconds(seconds, fps);
            prop_assert_eq!(pos, back);
        }

        /// Property test: frame -> seconds -> frame round-trip with fractional fps.
        #[test]
        fn round_trip_position_fractional_fps(frames in 0u64..100_000_000) {
            let pos = Position::from_frames(frames);
            let fps = FrameRate::FPS_23_976;
            let seconds = pos.to_seconds(fps);
            let back = Position::from_seconds(seconds, fps);
            prop_assert_eq!(pos, back);
        }

        /// Property test: Duration::between always gives valid duration when end >= start.
        #[test]
        fn duration_between_valid(start in 0u64..1_000_000, len in 0u64..1_000_000) {
            let s = Position::from_frames(start);
            let e = Position::from_frames(start + len);
            let dur = Duration::between(s, e);
            prop_assert!(dur.is_some());
            prop_assert_eq!(dur.unwrap().frames(), len);
        }

        /// Property test: Duration::between returns None when end < start.
        #[test]
        fn duration_between_invalid(start in 1u64..1_000_000, offset in 1u64..1_000_000) {
            let s = Position::from_frames(start);
            let e = Position::from_frames(start - offset.min(start));
            if e.frames() < s.frames() {
                let dur = Duration::between(s, e);
                prop_assert!(dur.is_none());
            }
        }

        /// Property test: end_position should be inverse of Duration::between.
        #[test]
        fn end_position_inverse(start in 0u64..1_000_000, len in 0u64..1_000_000) {
            let s = Position::from_frames(start);
            let dur = Duration::from_frames(len);
            let end = dur.end_position(s);
            let back = Duration::between(s, end);
            prop_assert_eq!(back.unwrap(), dur);
        }

        /// Property test: duration round-trip should be exact.
        #[test]
        fn round_trip_duration(frames in 0u64..1_000_000_000) {
            let dur = Duration::from_frames(frames);
            let fps = FrameRate::FPS_30;
            let seconds = dur.to_seconds(fps);
            let back = Duration::from_seconds(seconds, fps);
            prop_assert_eq!(dur, back);
        }

        /// Property test: frame rate should always produce positive fps.
        #[test]
        fn frame_rate_positive(num in 1u32..1_000_000, denom in 1u32..1_000_000) {
            let fps = FrameRate::new(num, denom).unwrap();
            prop_assert!(fps.frames_per_second() > 0.0);
        }
    }

    #[test]
    fn test_common_frame_rates() {
        // Verify all common frame rate constants work correctly
        let rates = [
            (FrameRate::FPS_23_976, 23.976_023_976_023_976),
            (FrameRate::FPS_24, 24.0),
            (FrameRate::FPS_25, 25.0),
            (FrameRate::FPS_29_97, 29.97_002_997_002_997),
            (FrameRate::FPS_30, 30.0),
            (FrameRate::FPS_50, 50.0),
            (FrameRate::FPS_59_94, 59.94_005_994_005_994),
            (FrameRate::FPS_60, 60.0),
        ];

        for (fps, expected) in rates {
            let actual = fps.frames_per_second();
            assert!(
                (actual - expected).abs() < 1e-10,
                "Frame rate {:?} expected {} but got {}",
                fps,
                expected,
                actual
            );
        }
    }

    #[test]
    fn test_integration_workflow() {
        // Simulate a typical video editing workflow
        let fps = FrameRate::FPS_24;

        // User sets in-point at 5 seconds
        let in_point = Position::from_seconds(5.0, fps);
        assert_eq!(in_point.frames(), 120);

        // User sets out-point at 10.5 seconds
        let out_point = Position::from_seconds(10.5, fps);
        assert_eq!(out_point.frames(), 252);

        // Calculate clip duration
        let clip_duration = Duration::between(in_point, out_point).unwrap();
        assert_eq!(clip_duration.frames(), 132);
        assert_eq!(clip_duration.to_seconds(fps), 5.5);

        // Place clip at timeline position 1 minute
        let timeline_start = Position::from_seconds(60.0, fps);
        let timeline_end = clip_duration.end_position(timeline_start);
        assert_eq!(timeline_end.frames(), 1440 + 132);
        assert_eq!(timeline_end.to_seconds(fps), 65.5);
    }
}
