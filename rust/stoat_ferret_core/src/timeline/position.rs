//! Timeline position representation.
//!
//! This module provides a [`Position`] type that represents a point in time
//! on a timeline as a frame count, ensuring frame-accurate positioning.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::FrameRate;

/// A position on the timeline represented as a frame count.
///
/// Using frame counts as the internal representation ensures frame-accurate
/// positioning without floating-point precision issues. Conversions to/from
/// seconds are available when needed for display or user input.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::timeline::{Position, FrameRate};
///
/// let fps = FrameRate::FPS_24;
///
/// // Create position from frames
/// let pos = Position::from_frames(48);
/// assert_eq!(pos.frames(), 48);
/// assert_eq!(pos.to_seconds(fps), 2.0);
///
/// // Create position from seconds
/// let pos = Position::from_seconds(2.0, fps);
/// assert_eq!(pos.frames(), 48);
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct Position(u64);

impl Position {
    /// Position at the start of the timeline (frame 0).
    pub const ZERO: Self = Self(0);

    /// Creates a new position from a frame count.
    ///
    /// # Arguments
    ///
    /// * `frames` - The frame number (0-indexed)
    #[must_use]
    pub fn from_frames(frames: u64) -> Self {
        Self(frames)
    }

    /// Creates a new position from seconds and frame rate.
    ///
    /// The seconds value is converted to the nearest frame number.
    ///
    /// # Arguments
    ///
    /// * `seconds` - Time in seconds
    /// * `fps` - The frame rate to use for conversion
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{Position, FrameRate};
    ///
    /// let fps = FrameRate::FPS_30;
    /// let pos = Position::from_seconds(1.0, fps);
    /// assert_eq!(pos.frames(), 30);
    /// ```
    #[must_use]
    pub fn from_seconds(seconds: f64, fps: FrameRate) -> Self {
        // frames = seconds * (numerator / denominator)
        // Using round() to get the nearest frame
        let frames =
            (seconds * f64::from(fps.numerator()) / f64::from(fps.denominator())).round() as u64;
        Self(frames)
    }

    /// Returns the frame count.
    #[must_use]
    pub fn frames(&self) -> u64 {
        self.0
    }

    /// Converts the position to seconds at the given frame rate.
    ///
    /// # Arguments
    ///
    /// * `fps` - The frame rate to use for conversion
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{Position, FrameRate};
    ///
    /// let fps = FrameRate::FPS_24;
    /// let pos = Position::from_frames(24);
    /// assert_eq!(pos.to_seconds(fps), 1.0);
    /// ```
    #[must_use]
    pub fn to_seconds(&self, fps: FrameRate) -> f64 {
        // seconds = frames * (denominator / numerator)
        self.0 as f64 * f64::from(fps.denominator()) / f64::from(fps.numerator())
    }
}

#[pymethods]
impl Position {
    /// Creates a new position from a frame count.
    ///
    /// # Arguments
    ///
    /// * `frames` - The frame number (0-indexed)
    #[new]
    fn py_new(frames: u64) -> Self {
        Self::from_frames(frames)
    }

    /// Returns the frame count.
    #[getter]
    #[pyo3(name = "frames")]
    fn py_frames(&self) -> u64 {
        self.frames()
    }

    /// Creates a new position from seconds and frame rate.
    ///
    /// # Arguments
    ///
    /// * `seconds` - Time in seconds
    /// * `fps` - The frame rate to use for conversion
    #[staticmethod]
    fn from_secs(seconds: f64, fps: &FrameRate) -> Self {
        Self::from_seconds(seconds, *fps)
    }

    /// Converts the position to seconds at the given frame rate.
    ///
    /// # Arguments
    ///
    /// * `fps` - The frame rate to use for conversion
    fn as_secs(&self, fps: &FrameRate) -> f64 {
        self.to_seconds(*fps)
    }

    /// Returns the zero position constant.
    #[staticmethod]
    fn zero() -> Self {
        Self::ZERO
    }

    /// Returns a string representation of the position.
    fn __repr__(&self) -> String {
        format!("Position(frame={})", self.0)
    }

    /// Compares two positions for equality.
    fn __eq__(&self, other: &Self) -> bool {
        self.0 == other.0
    }

    /// Compares two positions for ordering.
    fn __lt__(&self, other: &Self) -> bool {
        self.0 < other.0
    }

    /// Compares two positions for ordering.
    fn __le__(&self, other: &Self) -> bool {
        self.0 <= other.0
    }

    /// Compares two positions for ordering.
    fn __gt__(&self, other: &Self) -> bool {
        self.0 > other.0
    }

    /// Compares two positions for ordering.
    fn __ge__(&self, other: &Self) -> bool {
        self.0 >= other.0
    }

    /// Returns a hash of the position.
    fn __hash__(&self) -> u64 {
        self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_from_frames() {
        let pos = Position::from_frames(100);
        assert_eq!(pos.frames(), 100);
    }

    #[test]
    fn test_zero_constant() {
        assert_eq!(Position::ZERO.frames(), 0);
    }

    #[test]
    fn test_from_seconds_24fps() {
        let fps = FrameRate::FPS_24;

        let pos = Position::from_seconds(0.0, fps);
        assert_eq!(pos.frames(), 0);

        let pos = Position::from_seconds(1.0, fps);
        assert_eq!(pos.frames(), 24);

        let pos = Position::from_seconds(2.5, fps);
        assert_eq!(pos.frames(), 60);
    }

    #[test]
    fn test_from_seconds_30fps() {
        let fps = FrameRate::FPS_30;

        let pos = Position::from_seconds(1.0, fps);
        assert_eq!(pos.frames(), 30);

        let pos = Position::from_seconds(0.5, fps);
        assert_eq!(pos.frames(), 15);
    }

    #[test]
    fn test_from_seconds_23_976fps() {
        let fps = FrameRate::FPS_23_976;

        // At 23.976 fps (24000/1001), 1001 seconds = 24000 frames
        let pos = Position::from_seconds(1001.0, fps);
        assert_eq!(pos.frames(), 24000);
    }

    #[test]
    fn test_to_seconds_24fps() {
        let fps = FrameRate::FPS_24;

        let pos = Position::from_frames(0);
        assert_eq!(pos.to_seconds(fps), 0.0);

        let pos = Position::from_frames(24);
        assert_eq!(pos.to_seconds(fps), 1.0);

        let pos = Position::from_frames(60);
        assert_eq!(pos.to_seconds(fps), 2.5);
    }

    #[test]
    fn test_to_seconds_23_976fps() {
        let fps = FrameRate::FPS_23_976;

        // 24000 frames at 24000/1001 fps = 1001 seconds
        let pos = Position::from_frames(24000);
        let seconds = pos.to_seconds(fps);
        assert!((seconds - 1001.0).abs() < 1e-10);
    }

    #[test]
    fn test_ordering() {
        let pos1 = Position::from_frames(10);
        let pos2 = Position::from_frames(20);
        let pos3 = Position::from_frames(10);

        assert!(pos1 < pos2);
        assert!(pos2 > pos1);
        assert!(pos1 <= pos3);
        assert!(pos1 >= pos3);
        assert_eq!(pos1, pos3);
    }

    #[test]
    fn test_round_trip_integer_fps() {
        let fps = FrameRate::FPS_24;

        for frame in [0u64, 1, 24, 100, 1000, 86400 * 24] {
            let pos = Position::from_frames(frame);
            let seconds = pos.to_seconds(fps);
            let back = Position::from_seconds(seconds, fps);
            assert_eq!(pos, back, "Round trip failed for frame {}", frame);
        }
    }

    #[test]
    fn test_round_trip_fractional_fps() {
        let fps = FrameRate::FPS_23_976;

        // For fractional frame rates, round-trip should work for
        // any frame count since we're using rational arithmetic
        for frame in [0u64, 1, 24, 100, 1000, 24000] {
            let pos = Position::from_frames(frame);
            let seconds = pos.to_seconds(fps);
            let back = Position::from_seconds(seconds, fps);
            assert_eq!(pos, back, "Round trip failed for frame {}", frame);
        }
    }
}
