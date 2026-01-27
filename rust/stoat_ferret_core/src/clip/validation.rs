//! Clip validation logic with actionable error messages.
//!
//! This module provides comprehensive validation for video clips, including:
//!
//! - Structural validation (non-empty source path, valid in/out points)
//! - Temporal bounds validation (points within source duration)
//! - Batch validation for multiple clips
//!
//! # Error Messages
//!
//! All validation errors include:
//! - The specific field that failed validation
//! - A human-readable message explaining the problem
//! - The actual value that caused the error
//! - The expected value or constraint
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::clip::{Clip, validation};
//! use stoat_ferret_core::timeline::{Position, Duration};
//!
//! // Create an invalid clip (out_point <= in_point)
//! let clip = Clip::new(
//!     "video.mp4".to_string(),
//!     Position::from_frames(100),
//!     Position::from_frames(50),
//!     None,
//! );
//!
//! let errors = validation::validate_clip(&clip);
//! assert_eq!(errors.len(), 1);
//! assert_eq!(errors[0].field, "out_point");
//! ```

use super::Clip;
use pyo3::prelude::*;
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pyfunction};

/// A validation error with detailed information about what went wrong.
///
/// Each error includes the field name, a human-readable message, and optionally
/// the actual and expected values to help users understand and fix the problem.
///
/// Note: This is distinct from the `ValidationError` exception type in the module root.
/// This struct provides detailed validation failure information as data.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::clip::validation::ValidationError;
///
/// // Error with just a message
/// let err = ValidationError::new("source_path", "Source path cannot be empty");
/// assert_eq!(err.field, "source_path");
/// assert!(err.actual.is_none());
///
/// // Error with actual and expected values
/// let err = ValidationError::with_values(
///     "out_point",
///     "Out point must be greater than in point",
///     "50",
///     ">100",
/// );
/// assert_eq!(err.actual, Some("50".to_string()));
/// assert_eq!(err.expected, Some(">100".to_string()));
/// ```
#[gen_stub_pyclass]
#[pyclass(name = "ClipValidationError")]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationError {
    /// The name of the field that failed validation.
    #[pyo3(get)]
    pub field: String,
    /// A human-readable message explaining the validation failure.
    #[pyo3(get)]
    pub message: String,
    /// The actual value that failed validation (optional).
    #[pyo3(get)]
    pub actual: Option<String>,
    /// The expected value or constraint (optional).
    #[pyo3(get)]
    pub expected: Option<String>,
}

impl ValidationError {
    /// Creates a new validation error with just a field and message.
    ///
    /// # Arguments
    ///
    /// * `field` - The name of the field that failed validation
    /// * `message` - A human-readable explanation of the error
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::clip::validation::ValidationError;
    ///
    /// let err = ValidationError::new("source_path", "Source path cannot be empty");
    /// assert_eq!(err.field, "source_path");
    /// assert_eq!(err.message, "Source path cannot be empty");
    /// ```
    pub fn new(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            field: field.into(),
            message: message.into(),
            actual: None,
            expected: None,
        }
    }

    /// Creates a validation error with actual and expected values.
    ///
    /// Use this when you can provide specific values to help the user
    /// understand what went wrong and how to fix it.
    ///
    /// # Arguments
    ///
    /// * `field` - The name of the field that failed validation
    /// * `message` - A human-readable explanation of the error
    /// * `actual` - The actual value that was provided
    /// * `expected` - The expected value or constraint
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::clip::validation::ValidationError;
    ///
    /// let err = ValidationError::with_values(
    ///     "in_point",
    ///     "In point exceeds source duration",
    ///     "150",
    ///     "<100",
    /// );
    /// println!("{}", err);
    /// // Output: "in_point: In point exceeds source duration (got: 150, expected: <100)"
    /// ```
    pub fn with_values(
        field: impl Into<String>,
        message: impl Into<String>,
        actual: impl Into<String>,
        expected: impl Into<String>,
    ) -> Self {
        Self {
            field: field.into(),
            message: message.into(),
            actual: Some(actual.into()),
            expected: Some(expected.into()),
        }
    }
}

#[pymethods]
impl ValidationError {
    /// Creates a new validation error from Python.
    ///
    /// # Arguments
    ///
    /// * `field` - The name of the field that failed validation
    /// * `message` - A human-readable explanation of the error
    #[new]
    fn py_new(field: String, message: String) -> Self {
        Self::new(field, message)
    }

    /// Creates a validation error with actual and expected values.
    ///
    /// # Arguments
    ///
    /// * `field` - The name of the field that failed validation
    /// * `message` - A human-readable explanation of the error
    /// * `actual` - The actual value that was provided
    /// * `expected` - The expected value or constraint
    #[staticmethod]
    fn with_values_py(field: String, message: String, actual: String, expected: String) -> Self {
        Self::with_values(field, message, actual, expected)
    }

    /// Returns a string representation of the validation error.
    fn __repr__(&self) -> String {
        format!("{}", self)
    }

    /// Returns a string representation of the validation error.
    fn __str__(&self) -> String {
        format!("{}", self)
    }
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.field, self.message)?;
        match (&self.actual, &self.expected) {
            (Some(actual), Some(expected)) => {
                write!(f, " (got: {}, expected: {})", actual, expected)?;
            }
            (Some(actual), None) => {
                write!(f, " (got: {})", actual)?;
            }
            _ => {}
        }
        Ok(())
    }
}

impl std::error::Error for ValidationError {}

/// Validates a single clip and returns all validation errors.
///
/// This function checks:
/// - Source path is non-empty
/// - Out point is greater than in point
/// - In point is within source duration (if source duration is known)
/// - Out point is within source duration (if source duration is known)
///
/// # Arguments
///
/// * `clip` - The clip to validate
///
/// # Returns
///
/// A vector of validation errors. Empty if the clip is valid.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::clip::{Clip, validation};
/// use stoat_ferret_core::timeline::{Position, Duration};
///
/// // Valid clip
/// let valid_clip = Clip::new(
///     "video.mp4".to_string(),
///     Position::from_frames(0),
///     Position::from_frames(100),
///     Some(Duration::from_frames(200)),
/// );
/// assert!(validation::validate_clip(&valid_clip).is_empty());
///
/// // Invalid clip - empty source path
/// let invalid_clip = Clip::new(
///     "".to_string(),
///     Position::from_frames(0),
///     Position::from_frames(100),
///     None,
/// );
/// let errors = validation::validate_clip(&invalid_clip);
/// assert_eq!(errors.len(), 1);
/// assert_eq!(errors[0].field, "source_path");
/// ```
pub fn validate_clip(clip: &Clip) -> Vec<ValidationError> {
    let mut errors = Vec::new();

    // FR-001: Validate source path is non-empty
    if clip.source_path.is_empty() {
        errors.push(ValidationError::new(
            "source_path",
            "Source path cannot be empty. Provide a valid path to the source media file.",
        ));
    }

    // FR-001: Validate out_point > in_point
    if clip.out_point <= clip.in_point {
        errors.push(ValidationError::with_values(
            "out_point",
            "Out point must be greater than in point. Adjust out point to be after in point.",
            clip.out_point.frames().to_string(),
            format!(">{}", clip.in_point.frames()),
        ));
    }

    // FR-002: Validate temporal bounds (only if source duration is known)
    if let Some(source_dur) = clip.source_duration {
        // In-point must be within source duration
        if clip.in_point.frames() >= source_dur.frames() {
            errors.push(ValidationError::with_values(
                "in_point",
                "In point exceeds source duration. Set in point to a frame within the source file.",
                clip.in_point.frames().to_string(),
                format!("<{}", source_dur.frames()),
            ));
        }

        // Out-point must be within source duration
        if clip.out_point.frames() > source_dur.frames() {
            errors.push(ValidationError::with_values(
                "out_point",
                "Out point exceeds source duration. Set out point to at most the source duration.",
                clip.out_point.frames().to_string(),
                format!("<={}", source_dur.frames()),
            ));
        }
    }

    errors
}

/// A validation result for a single clip in a batch, including its index.
///
/// This allows batch validation to report which clips failed and where they
/// are in the original list.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::clip::{Clip, validation};
/// use stoat_ferret_core::timeline::{Position, Duration};
///
/// let clips = vec![
///     Clip::new("valid.mp4".to_string(), Position::from_frames(0), Position::from_frames(100), None),
///     Clip::new("".to_string(), Position::from_frames(0), Position::from_frames(100), None),
/// ];
///
/// let results = validation::validate_clips(&clips);
/// assert_eq!(results.len(), 1);
/// assert_eq!(results[0].clip_index, 1);
/// ```
#[derive(Debug, Clone)]
pub struct ClipValidationError {
    /// The 0-based index of the clip in the original list.
    pub clip_index: usize,
    /// The validation errors for this clip.
    pub errors: Vec<ValidationError>,
}

/// Validates a list of clips and returns all validation errors.
///
/// Unlike single-clip validation, this function collects errors from all clips
/// and reports which clip index each error belongs to. This enables batch
/// processing where all errors can be shown at once.
///
/// # Arguments
///
/// * `clips` - A slice of clips to validate
///
/// # Returns
///
/// A vector of `ClipValidationError` structs, one for each clip that has errors.
/// Clips with no errors are not included in the result.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::clip::{Clip, validation};
/// use stoat_ferret_core::timeline::{Position, Duration};
///
/// let clips = vec![
///     Clip::new("good.mp4".to_string(), Position::from_frames(0), Position::from_frames(100), None),
///     Clip::new("".to_string(), Position::from_frames(0), Position::from_frames(100), None),
///     Clip::new("bad.mp4".to_string(), Position::from_frames(100), Position::from_frames(50), None),
/// ];
///
/// let results = validation::validate_clips(&clips);
/// assert_eq!(results.len(), 2);  // Two clips have errors
/// assert_eq!(results[0].clip_index, 1);  // Second clip (empty path)
/// assert_eq!(results[1].clip_index, 2);  // Third clip (out < in)
/// ```
pub fn validate_clips(clips: &[Clip]) -> Vec<ClipValidationError> {
    clips
        .iter()
        .enumerate()
        .filter_map(|(i, clip)| {
            let errors = validate_clip(clip);
            if errors.is_empty() {
                None
            } else {
                Some(ClipValidationError {
                    clip_index: i,
                    errors,
                })
            }
        })
        .collect()
}

/// Validates a single clip and returns all validation errors (Python wrapper).
///
/// This function checks:
/// - Source path is non-empty
/// - Out point is greater than in point
/// - In point is within source duration (if source duration is known)
/// - Out point is within source duration (if source duration is known)
///
/// # Arguments
///
/// * `clip` - The clip to validate
///
/// # Returns
///
/// A list of validation errors. Empty if the clip is valid.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "validate_clip")]
pub fn py_validate_clip(clip: &Clip) -> Vec<ValidationError> {
    validate_clip(clip)
}

/// Validates a list of clips and returns all validation errors (Python wrapper).
///
/// Unlike single-clip validation, this function collects errors from all clips
/// and reports which clip index each error belongs to.
///
/// # Arguments
///
/// * `clips` - A list of clips to validate
///
/// # Returns
///
/// A list of tuples containing (clip_index, validation_error) for each error found.
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "validate_clips")]
pub fn py_validate_clips(clips: Vec<Clip>) -> Vec<(usize, ValidationError)> {
    let results = validate_clips(&clips);
    // Flatten to (index, error) tuples for easier Python consumption
    results
        .into_iter()
        .flat_map(|result| {
            result
                .errors
                .into_iter()
                .map(move |err| (result.clip_index, err))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::timeline::{Duration, Position};

    // ========================================================================
    // ValidationError tests
    // ========================================================================

    #[test]
    fn test_validation_error_new() {
        let err = ValidationError::new("field", "message");
        assert_eq!(err.field, "field");
        assert_eq!(err.message, "message");
        assert!(err.actual.is_none());
        assert!(err.expected.is_none());
    }

    #[test]
    fn test_validation_error_with_values() {
        let err = ValidationError::with_values("field", "message", "actual", "expected");
        assert_eq!(err.field, "field");
        assert_eq!(err.message, "message");
        assert_eq!(err.actual, Some("actual".to_string()));
        assert_eq!(err.expected, Some("expected".to_string()));
    }

    #[test]
    fn test_validation_error_display_basic() {
        let err = ValidationError::new("field", "message");
        assert_eq!(format!("{}", err), "field: message");
    }

    #[test]
    fn test_validation_error_display_with_values() {
        let err = ValidationError::with_values("field", "message", "10", ">20");
        assert_eq!(
            format!("{}", err),
            "field: message (got: 10, expected: >20)"
        );
    }

    #[test]
    fn test_validation_error_equality() {
        let err1 = ValidationError::new("field", "message");
        let err2 = ValidationError::new("field", "message");
        let err3 = ValidationError::new("other", "message");
        assert_eq!(err1, err2);
        assert_ne!(err1, err3);
    }

    // ========================================================================
    // validate_clip tests - FR-001: Clip Structure
    // ========================================================================

    #[test]
    fn test_valid_clip() {
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(0),
            Position::from_frames(100),
            Some(Duration::from_frames(200)),
        );
        let errors = validate_clip(&clip);
        assert!(errors.is_empty());
    }

    #[test]
    fn test_empty_source_path() {
        let clip = Clip::new(
            "".to_string(),
            Position::from_frames(0),
            Position::from_frames(100),
            None,
        );
        let errors = validate_clip(&clip);
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].field, "source_path");
        assert!(errors[0].message.contains("cannot be empty"));
    }

    #[test]
    fn test_out_point_equal_to_in_point() {
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(50),
            Position::from_frames(50),
            None,
        );
        let errors = validate_clip(&clip);
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].field, "out_point");
        assert!(errors[0].message.contains("must be greater than in point"));
        assert_eq!(errors[0].actual, Some("50".to_string()));
        assert_eq!(errors[0].expected, Some(">50".to_string()));
    }

    #[test]
    fn test_out_point_less_than_in_point() {
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(100),
            Position::from_frames(50),
            None,
        );
        let errors = validate_clip(&clip);
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].field, "out_point");
        assert_eq!(errors[0].actual, Some("50".to_string()));
        assert_eq!(errors[0].expected, Some(">100".to_string()));
    }

    // ========================================================================
    // validate_clip tests - FR-002: Temporal Bounds
    // ========================================================================

    #[test]
    fn test_in_point_exceeds_source_duration() {
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(200),
            Position::from_frames(250),
            Some(Duration::from_frames(100)),
        );
        let errors = validate_clip(&clip);
        // Should have both in_point and out_point errors
        assert!(errors.len() >= 1);
        let in_err = errors.iter().find(|e| e.field == "in_point");
        assert!(in_err.is_some());
        let in_err = in_err.unwrap();
        assert!(in_err.message.contains("exceeds source duration"));
        assert_eq!(in_err.actual, Some("200".to_string()));
        assert_eq!(in_err.expected, Some("<100".to_string()));
    }

    #[test]
    fn test_out_point_exceeds_source_duration() {
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(50),
            Position::from_frames(150),
            Some(Duration::from_frames(100)),
        );
        let errors = validate_clip(&clip);
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].field, "out_point");
        assert!(errors[0].message.contains("exceeds source duration"));
        assert_eq!(errors[0].actual, Some("150".to_string()));
        assert_eq!(errors[0].expected, Some("<=100".to_string()));
    }

    #[test]
    fn test_in_point_at_source_duration_boundary() {
        // in_point at exactly source_duration should be invalid (>= check)
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(100),
            Position::from_frames(150),
            Some(Duration::from_frames(100)),
        );
        let errors = validate_clip(&clip);
        let in_err = errors.iter().find(|e| e.field == "in_point");
        assert!(in_err.is_some());
    }

    #[test]
    fn test_out_point_at_source_duration_boundary() {
        // out_point at exactly source_duration should be valid (<= check)
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(50),
            Position::from_frames(100),
            Some(Duration::from_frames(100)),
        );
        let errors = validate_clip(&clip);
        assert!(errors.is_empty());
    }

    #[test]
    fn test_unknown_source_duration_skips_bounds_check() {
        // When source_duration is None, bounds checks should be skipped
        let clip = Clip::new(
            "video.mp4".to_string(),
            Position::from_frames(1000),
            Position::from_frames(2000),
            None,
        );
        let errors = validate_clip(&clip);
        assert!(errors.is_empty());
    }

    // ========================================================================
    // validate_clip tests - FR-003: Multiple Errors
    // ========================================================================

    #[test]
    fn test_multiple_errors() {
        // Clip with empty path, invalid in/out points, and exceeding bounds
        let clip = Clip::new(
            "".to_string(),
            Position::from_frames(200),
            Position::from_frames(100),
            Some(Duration::from_frames(150)),
        );
        let errors = validate_clip(&clip);
        // Should have: empty path, out <= in, in >= source, out > source (4 errors)
        assert!(errors.len() >= 3);

        let fields: Vec<&str> = errors.iter().map(|e| e.field.as_str()).collect();
        assert!(fields.contains(&"source_path"));
        assert!(fields.contains(&"out_point"));
        assert!(fields.contains(&"in_point"));
    }

    // ========================================================================
    // validate_clips tests - FR-004: Batch Validation
    // ========================================================================

    #[test]
    fn test_batch_all_valid() {
        let clips = vec![
            Clip::new(
                "a.mp4".to_string(),
                Position::from_frames(0),
                Position::from_frames(100),
                None,
            ),
            Clip::new(
                "b.mp4".to_string(),
                Position::from_frames(10),
                Position::from_frames(50),
                None,
            ),
        ];
        let results = validate_clips(&clips);
        assert!(results.is_empty());
    }

    #[test]
    fn test_batch_some_invalid() {
        let clips = vec![
            Clip::new(
                "valid.mp4".to_string(),
                Position::from_frames(0),
                Position::from_frames(100),
                None,
            ),
            Clip::new(
                "".to_string(), // Invalid: empty path
                Position::from_frames(0),
                Position::from_frames(100),
                None,
            ),
            Clip::new(
                "valid2.mp4".to_string(),
                Position::from_frames(0),
                Position::from_frames(100),
                None,
            ),
            Clip::new(
                "invalid.mp4".to_string(),
                Position::from_frames(100),
                Position::from_frames(50), // Invalid: out < in
                None,
            ),
        ];
        let results = validate_clips(&clips);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].clip_index, 1);
        assert_eq!(results[1].clip_index, 3);
    }

    #[test]
    fn test_batch_all_invalid() {
        let clips = vec![
            Clip::new(
                "".to_string(),
                Position::from_frames(0),
                Position::from_frames(100),
                None,
            ),
            Clip::new(
                "".to_string(),
                Position::from_frames(0),
                Position::from_frames(100),
                None,
            ),
        ];
        let results = validate_clips(&clips);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].clip_index, 0);
        assert_eq!(results[1].clip_index, 1);
    }

    #[test]
    fn test_batch_empty_list() {
        let clips: Vec<Clip> = vec![];
        let results = validate_clips(&clips);
        assert!(results.is_empty());
    }

    #[test]
    fn test_batch_preserves_all_errors_per_clip() {
        let clips = vec![Clip::new(
            "".to_string(),
            Position::from_frames(100),
            Position::from_frames(50),
            None,
        )];
        let results = validate_clips(&clips);
        assert_eq!(results.len(), 1);
        // Should have at least 2 errors: empty path and out <= in
        assert!(results[0].errors.len() >= 2);
    }
}
