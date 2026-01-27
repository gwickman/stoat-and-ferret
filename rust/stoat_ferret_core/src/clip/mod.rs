//! Video clip representation and validation.
//!
//! This module provides types for representing video clips and validating them:
//!
//! - [`Clip`] - A video clip with source path, in/out points, and optional source duration
//! - [`validation`] - Validation logic and error types for clips
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::clip::{Clip, validation};
//! use stoat_ferret_core::timeline::{Position, Duration};
//!
//! // Create a clip from a source file
//! let clip = Clip::new(
//!     "video.mp4".to_string(),
//!     Position::from_frames(0),
//!     Position::from_frames(100),
//!     Some(Duration::from_frames(200)),
//! );
//!
//! // Validate the clip
//! let errors = validation::validate_clip(&clip);
//! assert!(errors.is_empty());
//! ```

pub mod validation;

use crate::timeline::{Duration, Position};
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;

/// A video clip representing a segment of a source media file.
///
/// A clip defines a portion of a source video through in and out points,
/// and optionally includes the source file's total duration for bounds validation.
///
/// # Fields
///
/// - `source_path` - Path to the source media file
/// - `in_point` - Start position within the source file (inclusive)
/// - `out_point` - End position within the source file (exclusive)
/// - `source_duration` - Total duration of the source file (optional, for validation)
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::clip::Clip;
/// use stoat_ferret_core::timeline::{Position, Duration};
///
/// let clip = Clip::new(
///     "/path/to/video.mp4".to_string(),
///     Position::from_frames(24),   // Start at frame 24
///     Position::from_frames(72),   // End at frame 72
///     Some(Duration::from_frames(100)),  // Source is 100 frames long
/// );
///
/// assert_eq!(clip.duration().unwrap().frames(), 48);
/// ```
#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Clip {
    /// Path to the source media file.
    #[pyo3(get)]
    pub source_path: String,
    /// Start position within the source file (inclusive).
    #[pyo3(get)]
    pub in_point: Position,
    /// End position within the source file (exclusive).
    #[pyo3(get)]
    pub out_point: Position,
    /// Total duration of the source file (optional, used for bounds validation).
    #[pyo3(get)]
    pub source_duration: Option<Duration>,
}

impl Clip {
    /// Creates a new clip.
    ///
    /// # Arguments
    ///
    /// * `source_path` - Path to the source media file
    /// * `in_point` - Start position within the source file
    /// * `out_point` - End position within the source file
    /// * `source_duration` - Total duration of the source file (optional)
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::clip::Clip;
    /// use stoat_ferret_core::timeline::{Position, Duration};
    ///
    /// let clip = Clip::new(
    ///     "video.mp4".to_string(),
    ///     Position::from_frames(0),
    ///     Position::from_frames(100),
    ///     None,
    /// );
    /// ```
    #[must_use]
    pub fn new(
        source_path: String,
        in_point: Position,
        out_point: Position,
        source_duration: Option<Duration>,
    ) -> Self {
        Self {
            source_path,
            in_point,
            out_point,
            source_duration,
        }
    }

    /// Calculates the duration of this clip.
    ///
    /// Returns `None` if out_point is not greater than in_point.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::clip::Clip;
    /// use stoat_ferret_core::timeline::{Position, Duration};
    ///
    /// let clip = Clip::new(
    ///     "video.mp4".to_string(),
    ///     Position::from_frames(10),
    ///     Position::from_frames(50),
    ///     None,
    /// );
    ///
    /// assert_eq!(clip.duration().unwrap().frames(), 40);
    /// ```
    #[must_use]
    pub fn duration(&self) -> Option<Duration> {
        Duration::between(self.in_point, self.out_point)
    }
}

#[pymethods]
impl Clip {
    /// Creates a new clip from Python.
    ///
    /// # Arguments
    ///
    /// * `source_path` - Path to the source media file
    /// * `in_point` - Start position within the source file
    /// * `out_point` - End position within the source file
    /// * `source_duration` - Total duration of the source file (optional)
    #[new]
    fn py_new(
        source_path: String,
        in_point: Position,
        out_point: Position,
        source_duration: Option<Duration>,
    ) -> Self {
        Self::new(source_path, in_point, out_point, source_duration)
    }

    /// Calculates the duration of this clip.
    ///
    /// Returns `None` if out_point is not greater than in_point.
    #[pyo3(name = "duration")]
    fn py_duration(&self) -> Option<Duration> {
        self.duration()
    }

    /// Returns a string representation of the clip.
    fn __repr__(&self) -> String {
        format!(
            "Clip(source_path={:?}, in_point={}, out_point={}, source_duration={:?})",
            self.source_path,
            self.in_point.frames(),
            self.out_point.frames(),
            self.source_duration.map(|d| d.frames())
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clip_new() {
        let clip = Clip::new(
            "test.mp4".to_string(),
            Position::from_frames(0),
            Position::from_frames(100),
            Some(Duration::from_frames(200)),
        );

        assert_eq!(clip.source_path, "test.mp4");
        assert_eq!(clip.in_point.frames(), 0);
        assert_eq!(clip.out_point.frames(), 100);
        assert_eq!(clip.source_duration.unwrap().frames(), 200);
    }

    #[test]
    fn test_clip_duration() {
        let clip = Clip::new(
            "test.mp4".to_string(),
            Position::from_frames(10),
            Position::from_frames(50),
            None,
        );

        assert_eq!(clip.duration().unwrap().frames(), 40);
    }

    #[test]
    fn test_clip_duration_invalid() {
        let clip = Clip::new(
            "test.mp4".to_string(),
            Position::from_frames(50),
            Position::from_frames(10),
            None,
        );

        assert!(clip.duration().is_none());
    }

    #[test]
    fn test_clip_without_source_duration() {
        let clip = Clip::new(
            "test.mp4".to_string(),
            Position::from_frames(0),
            Position::from_frames(100),
            None,
        );

        assert!(clip.source_duration.is_none());
    }
}
