# Implementation Plan: Clip Validation

## Step 1: Define Clip Structure
Create `rust/stoat_ferret_core/src/clip/mod.rs`:

```rust
use crate::timeline::{Position, Duration};

/// A clip represents a segment of source media
#[derive(Debug, Clone)]
pub struct Clip {
    pub source_path: String,
    pub in_point: Position,
    pub out_point: Position,
    pub source_duration: Option<Duration>,
}

impl Clip {
    pub fn duration(&self) -> Duration {
        Duration::between(self.in_point, self.out_point)
            .expect("out_point must be > in_point")
    }
}
```

## Step 2: Define Validation Error
```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationError {
    pub field: String,
    pub message: String,
    pub actual: Option<String>,
    pub expected: Option<String>,
}

impl ValidationError {
    pub fn new(field: &str, message: &str) -> Self { ... }
    pub fn with_values(field: &str, message: &str, actual: &str, expected: &str) -> Self { ... }
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.field, self.message)?;
        if let Some(actual) = &self.actual {
            write!(f, " (got: {}", actual)?;
            if let Some(expected) = &self.expected {
                write!(f, ", expected: {}", expected)?;
            }
            write!(f, ")")?;
        }
        Ok(())
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
            &format!("{}", clip.out_point.frames()),
            &format!(">{}", clip.in_point.frames()),
        ));
    }

    if let Some(source_dur) = clip.source_duration {
        if clip.out_point.frames() > source_dur.frames() {
            errors.push(ValidationError::with_values(
                "out_point",
                "Out point exceeds source duration",
                &format!("{}", clip.out_point.frames()),
                &format!("<={}", source_dur.frames()),
            ));
        }
    }

    errors
}
```

## Step 4: Batch Validation
```rust
pub struct ClipValidationError {
    pub clip_index: usize,
    pub errors: Vec<ValidationError>,
}

pub fn validate_clips(clips: &[Clip]) -> Vec<ClipValidationError> {
    clips.iter()
        .enumerate()
        .filter_map(|(i, clip)| {
            let errors = validate_clip(clip);
            if errors.is_empty() {
                None
            } else {
                Some(ClipValidationError { clip_index: i, errors })
            }
        })
        .collect()
}
```

## Step 5: Unit Tests
Test each validation rule and error message format.

## Verification
- All validation cases covered
- Error messages include field, actual, expected
- Batch validation returns all errors