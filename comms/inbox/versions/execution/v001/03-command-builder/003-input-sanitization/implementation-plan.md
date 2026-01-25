# Implementation Plan: Input Sanitization

## Step 1: Create Sanitization Module
Create `rust/stoat_ferret_core/src/sanitize/mod.rs`:

```rust
pub mod text;
pub mod path;
pub mod bounds;
```

## Step 2: Implement Text Escaping
Create `text.rs`:

```rust
/// Escape text for use in FFmpeg filter parameters
pub fn escape_filter_text(input: &str) -> String {
    let mut result = String::with_capacity(input.len() * 2);
    for c in input.chars() {
        match c {
            '\\' => result.push_str("\\\\"),
            '\'' => result.push_str("'\\''"),
            ':' => result.push_str("\\:"),
            '[' => result.push_str("\\["),
            ']' => result.push_str("\\]"),
            ';' => result.push_str("\\;"),
            '\n' => result.push_str("\\n"),
            '\r' => result.push_str("\\r"),
            _ => result.push(c),
        }
    }
    result
}

/// Escape text for use in drawtext filter
pub fn escape_drawtext(input: &str) -> String {
    // Additional escaping for drawtext
    escape_filter_text(input)
        .replace('%', "\\%")  // Percent for time codes
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_escape_colon() {
        assert_eq!(escape_filter_text("hello:world"), "hello\\:world");
    }

    #[test]
    fn test_escape_quotes() {
        assert_eq!(escape_filter_text("it's"), "it'\\''s");
    }
}
```

## Step 3: Implement Path Validation
Create `path.rs`:

```rust
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PathError {
    EmptyPath,
    ContainsNull,
    OutsideAllowedDirectory,
    CanonicalizeError(String),
}

/// Validate a path is within allowed directories
pub fn validate_path(
    path: &Path,
    allowed_dirs: &[PathBuf],
) -> Result<PathBuf, PathError> {
    // Check for null bytes
    if path.to_string_lossy().contains('\0') {
        return Err(PathError::ContainsNull);
    }

    // Canonicalize to resolve .. and symlinks
    let canonical = path.canonicalize()
        .map_err(|e| PathError::CanonicalizeError(e.to_string()))?;

    // Check against allowed directories
    let is_allowed = allowed_dirs.iter()
        .any(|allowed| canonical.starts_with(allowed));

    if !is_allowed {
        return Err(PathError::OutsideAllowedDirectory);
    }

    Ok(canonical)
}

/// Validate path without canonicalization (for non-existent output files)
pub fn validate_output_path(
    path: &Path,
    allowed_dirs: &[PathBuf],
) -> Result<PathBuf, PathError> {
    // Check for null bytes
    if path.to_string_lossy().contains('\0') {
        return Err(PathError::ContainsNull);
    }

    // Get parent and canonicalize that
    let parent = path.parent().ok_or(PathError::EmptyPath)?;
    let canonical_parent = parent.canonicalize()
        .map_err(|e| PathError::CanonicalizeError(e.to_string()))?;

    let is_allowed = allowed_dirs.iter()
        .any(|allowed| canonical_parent.starts_with(allowed));

    if !is_allowed {
        return Err(PathError::OutsideAllowedDirectory);
    }

    Ok(canonical_parent.join(path.file_name().unwrap()))
}
```

## Step 4: Implement Parameter Bounds
Create `bounds.rs`:

```rust
use std::ops::RangeInclusive;

#[derive(Debug, Clone, PartialEq)]
pub enum BoundsError {
    OutOfRange { name: String, value: f64, range: RangeInclusive<f64> },
    InvalidValue { name: String, value: String, allowed: Vec<String> },
}

pub fn validate_speed(speed: f64) -> Result<f64, BoundsError> {
    let range = 0.25..=4.0;
    if range.contains(&speed) {
        Ok(speed)
    } else {
        Err(BoundsError::OutOfRange {
            name: "speed".to_string(),
            value: speed,
            range,
        })
    }
}

pub fn validate_crf(crf: u8) -> Result<u8, BoundsError> {
    if crf <= 51 {
        Ok(crf)
    } else {
        Err(BoundsError::OutOfRange {
            name: "crf".to_string(),
            value: crf as f64,
            range: 0.0..=51.0,
        })
    }
}

const VALID_PRESETS: &[&str] = &[
    "ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow", "placebo",
];

pub fn validate_preset(preset: &str) -> Result<&str, BoundsError> {
    if VALID_PRESETS.contains(&preset) {
        Ok(preset)
    } else {
        Err(BoundsError::InvalidValue {
            name: "preset".to_string(),
            value: preset.to_string(),
            allowed: VALID_PRESETS.iter().map(|s| s.to_string()).collect(),
        })
    }
}

const VALID_CODECS: &[&str] = &[
    "libx264", "libx265", "libvpx", "libvpx-vp9", "libaom-av1",
    "aac", "libopus", "libmp3lame", "copy",
];

pub fn validate_codec(codec: &str) -> Result<&str, BoundsError> { ... }
```

## Step 5: Integrate with Command Builder
Use sanitization in command builder's build() method.

## Verification
- Escape functions handle all special characters
- Path validation rejects traversal attempts
- Parameter validation rejects out-of-range values