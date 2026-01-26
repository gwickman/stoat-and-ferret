# Implementation Plan: Clip Validation

## Step 1: Define ValidationError
`rust/stoat_ferret_core/src/clip/validation.rs`:
```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationError {
    pub field: String,
    pub message: String,
    pub actual: Option<String>,
    pub expected: Option<String>,
}

impl ValidationError {
    pub fn new(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            field: field.into(),
            message: message.into(),
            actual: None,
            expected: None,
        }
    }

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

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.field, self.message)?;
        if let (Some(actual), Some(expected)) = (&self.actual, &self.expected) {
            write!(f, " (got: {}, expected: {})", actual, expected)?;
        } else if let Some(actual) = &self.actual {
            write!(f, " (got: {})", actual)?;
        }
        Ok(())
    }
}
```

## Step 2: Define Clip
`rust/stoat_ferret_core/src/clip/mod.rs`:
```rust
use crate::timeline::{Duration, Position};

pub mod validation;

#[derive(Debug, Clone)]
pub struct Clip {
    pub source_path: String,
    pub in_point: Position,
    pub out_point: Position,
    pub source_duration: Option<Duration>,
}

impl Clip {
    pub fn duration(&self) -> Option<Duration> {
        Duration::between(self.in_point, self.out_point)
    }
}
```

## Step 3: Implement Validator
```rust
pub fn validate_clip(clip: &Clip) -> Vec<ValidationError> {
    let mut errors = Vec::new();

    if clip.source_path.is_empty() {
        errors.push(ValidationError::new(
            "source_path",
            "Source path cannot be empty",
        ));
    }

    if clip.out_point <= clip.in_point {
        errors.push(ValidationError::with_values(
            "out_point",
            "Out point must be greater than in point",
            clip.out_point.frames().to_string(),
            format!(">{}", clip.in_point.frames()),
        ));
    }

    if let Some(source_dur) = clip.source_duration {
        if clip.in_point.frames() >= source_dur.frames() {
            errors.push(ValidationError::with_values(
                "in_point",
                "In point exceeds source duration",
                clip.in_point.frames().to_string(),
                format!("<{}", source_dur.frames()),
            ));
        }
        if clip.out_point.frames() > source_dur.frames() {
            errors.push(ValidationError::with_values(
                "out_point",
                "Out point exceeds source duration",
                clip.out_point.frames().to_string(),
                format!("<={}", source_dur.frames()),
            ));
        }
    }

    errors
}
```

## Step 4: Batch Validation
```rust
#[derive(Debug, Clone)]
pub struct ClipValidationError {
    pub clip_index: usize,
    pub errors: Vec<ValidationError>,
}

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
```

## Step 5: Unit Tests
Test each validation rule, error message format, and batch behavior.

## Verification
- All validation cases covered
- Error messages include field, actual, expected
- Batch validation returns all errors