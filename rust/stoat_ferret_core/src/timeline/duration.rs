//! Timeline duration representation.
//!
//! This module provides a [`Duration`] type that represents a span of time
//! on a timeline as a frame count, ensuring frame-accurate durations.

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

use super::{FrameRate, Position};

/// A duration on the timeline represented as a frame count.
///
/// Using frame counts as the internal representation ensures frame-accurate
/// durations without floating-point precision issues. Conversions to/from
/// seconds are available when needed for display or user input.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::timeline::{Duration, Position, FrameRate};
///
/// let fps = FrameRate::FPS_24;
///
/// // Create duration from frames
/// let dur = Duration::from_frames(48);
/// assert_eq!(dur.frames(), 48);
/// assert_eq!(dur.to_seconds(fps), 2.0);
///
/// // Calculate duration between two positions
/// let start = Position::from_frames(10);
/// let end = Position::from_frames(34);
/// let dur = Duration::between(start, end).unwrap();
/// assert_eq!(dur.frames(), 24);
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct Duration(u64);

impl Duration {
    /// Zero duration (0 frames).
    pub const ZERO: Self = Self(0);

    /// Creates a new duration from a frame count.
    ///
    /// # Arguments
    ///
    /// * `frames` - The number of frames
    #[must_use]
    pub fn from_frames(frames: u64) -> Self {
        Self(frames)
    }

    /// Creates a new duration from seconds and frame rate.
    ///
    /// The seconds value is converted to the nearest frame count.
    ///
    /// # Arguments
    ///
    /// * `seconds` - Duration in seconds
    /// * `fps` - The frame rate to use for conversion
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{Duration, FrameRate};
    ///
    /// let fps = FrameRate::FPS_30;
    /// let dur = Duration::from_seconds(1.0, fps);
    /// assert_eq!(dur.frames(), 30);
    /// ```
    #[must_use]
    pub fn from_seconds(seconds: f64, fps: FrameRate) -> Self {
        // frames = seconds * (numerator / denominator)
        // Using round() to get the nearest frame count
        let frames =
            (seconds * f64::from(fps.numerator()) / f64::from(fps.denominator())).round() as u64;
        Self(frames)
    }

    /// Calculates the duration between two positions.
    ///
    /// Returns `None` if `end` is before `start`.
    ///
    /// # Arguments
    ///
    /// * `start` - The start position
    /// * `end` - The end position
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{Duration, Position};
    ///
    /// let start = Position::from_frames(10);
    /// let end = Position::from_frames(50);
    /// let dur = Duration::between(start, end).unwrap();
    /// assert_eq!(dur.frames(), 40);
    ///
    /// // Returns None if end is before start
    /// let invalid = Duration::between(end, start);
    /// assert!(invalid.is_none());
    /// ```
    #[must_use]
    pub fn between(start: Position, end: Position) -> Option<Self> {
        if end.frames() >= start.frames() {
            Some(Self(end.frames() - start.frames()))
        } else {
            None
        }
    }

    /// Returns the frame count.
    #[must_use]
    pub fn frames(&self) -> u64 {
        self.0
    }

    /// Converts the duration to seconds at the given frame rate.
    ///
    /// # Arguments
    ///
    /// * `fps` - The frame rate to use for conversion
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{Duration, FrameRate};
    ///
    /// let fps = FrameRate::FPS_24;
    /// let dur = Duration::from_frames(24);
    /// assert_eq!(dur.to_seconds(fps), 1.0);
    /// ```
    #[must_use]
    pub fn to_seconds(&self, fps: FrameRate) -> f64 {
        // seconds = frames * (denominator / numerator)
        self.0 as f64 * f64::from(fps.denominator()) / f64::from(fps.numerator())
    }

    /// Calculates the end position given a start position and this duration.
    ///
    /// # Arguments
    ///
    /// * `start` - The start position
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::timeline::{Duration, Position};
    ///
    /// let start = Position::from_frames(10);
    /// let dur = Duration::from_frames(20);
    /// let end = dur.end_position(start);
    /// assert_eq!(end.frames(), 30);
    /// ```
    #[must_use]
    pub fn end_position(&self, start: Position) -> Position {
        Position::from_frames(start.frames() + self.0)
    }
}

#[pymethods]
impl Duration {
    /// Creates a new duration from a frame count.
    ///
    /// # Arguments
    ///
    /// * `frames` - The number of frames
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

    /// Creates a new duration from seconds and frame rate.
    ///
    /// # Arguments
    ///
    /// * `seconds` - Duration in seconds
    /// * `fps` - The frame rate to use for conversion
    #[staticmethod]
    fn from_secs(seconds: f64, fps: &FrameRate) -> Self {
        Self::from_seconds(seconds, *fps)
    }

    /// Converts the duration to seconds at the given frame rate.
    ///
    /// # Arguments
    ///
    /// * `fps` - The frame rate to use for conversion
    fn as_secs(&self, fps: &FrameRate) -> f64 {
        self.to_seconds(*fps)
    }

    /// Calculates the duration between two positions.
    ///
    /// # Arguments
    ///
    /// * `start` - The start position
    /// * `end` - The end position
    ///
    /// # Raises
    ///
    /// ValueError: If end is before start
    #[staticmethod]
    fn between_positions(start: &Position, end: &Position) -> PyResult<Self> {
        Self::between(*start, *end)
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("end position is before start"))
    }

    /// Calculates the end position given a start position.
    ///
    /// # Arguments
    ///
    /// * `start` - The start position
    fn end_pos(&self, start: &Position) -> Position {
        self.end_position(*start)
    }

    /// Returns the zero duration constant.
    #[staticmethod]
    fn zero() -> Self {
        Self::ZERO
    }

    /// Returns a string representation of the duration.
    fn __repr__(&self) -> String {
        format!("Duration(frames={})", self.0)
    }

    /// Compares two durations for equality.
    fn __eq__(&self, other: &Self) -> bool {
        self.0 == other.0
    }

    /// Compares two durations for ordering.
    fn __lt__(&self, other: &Self) -> bool {
        self.0 < other.0
    }

    /// Compares two durations for ordering.
    fn __le__(&self, other: &Self) -> bool {
        self.0 <= other.0
    }

    /// Compares two durations for ordering.
    fn __gt__(&self, other: &Self) -> bool {
        self.0 > other.0
    }

    /// Compares two durations for ordering.
    fn __ge__(&self, other: &Self) -> bool {
        self.0 >= other.0
    }

    /// Returns a hash of the duration.
    fn __hash__(&self) -> u64 {
        self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_from_frames() {
        let dur = Duration::from_frames(100);
        assert_eq!(dur.frames(), 100);
    }

    #[test]
    fn test_zero_constant() {
        assert_eq!(Duration::ZERO.frames(), 0);
    }

    #[test]
    fn test_from_seconds_24fps() {
        let fps = FrameRate::FPS_24;

        let dur = Duration::from_seconds(0.0, fps);
        assert_eq!(dur.frames(), 0);

        let dur = Duration::from_seconds(1.0, fps);
        assert_eq!(dur.frames(), 24);

        let dur = Duration::from_seconds(2.5, fps);
        assert_eq!(dur.frames(), 60);
    }

    #[test]
    fn test_from_seconds_30fps() {
        let fps = FrameRate::FPS_30;

        let dur = Duration::from_seconds(1.0, fps);
        assert_eq!(dur.frames(), 30);

        let dur = Duration::from_seconds(0.5, fps);
        assert_eq!(dur.frames(), 15);
    }

    #[test]
    fn test_to_seconds_24fps() {
        let fps = FrameRate::FPS_24;

        let dur = Duration::from_frames(0);
        assert_eq!(dur.to_seconds(fps), 0.0);

        let dur = Duration::from_frames(24);
        assert_eq!(dur.to_seconds(fps), 1.0);

        let dur = Duration::from_frames(60);
        assert_eq!(dur.to_seconds(fps), 2.5);
    }

    #[test]
    fn test_between_valid() {
        let start = Position::from_frames(10);
        let end = Position::from_frames(50);
        let dur = Duration::between(start, end).unwrap();
        assert_eq!(dur.frames(), 40);
    }

    #[test]
    fn test_between_same_position() {
        let pos = Position::from_frames(10);
        let dur = Duration::between(pos, pos).unwrap();
        assert_eq!(dur.frames(), 0);
    }

    #[test]
    fn test_between_invalid() {
        let start = Position::from_frames(50);
        let end = Position::from_frames(10);
        assert!(Duration::between(start, end).is_none());
    }

    #[test]
    fn test_end_position() {
        let start = Position::from_frames(10);
        let dur = Duration::from_frames(20);
        let end = dur.end_position(start);
        assert_eq!(end.frames(), 30);
    }

    #[test]
    fn test_end_position_zero_duration() {
        let start = Position::from_frames(10);
        let dur = Duration::ZERO;
        let end = dur.end_position(start);
        assert_eq!(end, start);
    }

    #[test]
    fn test_ordering() {
        let dur1 = Duration::from_frames(10);
        let dur2 = Duration::from_frames(20);
        let dur3 = Duration::from_frames(10);

        assert!(dur1 < dur2);
        assert!(dur2 > dur1);
        assert!(dur1 <= dur3);
        assert!(dur1 >= dur3);
        assert_eq!(dur1, dur3);
    }

    #[test]
    fn test_round_trip() {
        let fps = FrameRate::FPS_24;

        for frame in [0u64, 1, 24, 100, 1000, 86400 * 24] {
            let dur = Duration::from_frames(frame);
            let seconds = dur.to_seconds(fps);
            let back = Duration::from_seconds(seconds, fps);
            assert_eq!(dur, back, "Round trip failed for frame {}", frame);
        }
    }
}
