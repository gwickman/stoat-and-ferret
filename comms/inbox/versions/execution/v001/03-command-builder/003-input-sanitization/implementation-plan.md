# Implementation Plan: Input Sanitization

## Step 1: Create Sanitization Module
`rust/stoat_ferret_core/src/sanitize/mod.rs`

## Step 2: Text Escaping
```rust
/// Escape text for FFmpeg filter parameters
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
```

## Step 3: Path Validation
```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PathError {
    Empty,
    ContainsNull,
}

pub fn validate_path(path: &str) -> Result<(), PathError> {
    if path.is_empty() {
        return Err(PathError::Empty);
    }
    if path.contains('\0') {
        return Err(PathError::ContainsNull);
    }
    Ok(())
}
```

## Step 4: Parameter Bounds
```rust
#[derive(Debug, Clone, PartialEq)]
pub enum BoundsError {
    OutOfRange { name: String, value: f64, min: f64, max: f64 },
    InvalidValue { name: String, value: String, allowed: Vec<String> },
}

pub fn validate_crf(crf: u8) -> Result<u8, BoundsError> {
    if crf <= 51 {
        Ok(crf)
    } else {
        Err(BoundsError::OutOfRange {
            name: "crf".into(),
            value: crf as f64,
            min: 0.0,
            max: 51.0,
        })
    }
}

pub fn validate_speed(speed: f64) -> Result<f64, BoundsError> {
    if (0.25..=4.0).contains(&speed) {
        Ok(speed)
    } else {
        Err(BoundsError::OutOfRange {
            name: "speed".into(),
            value: speed,
            min: 0.25,
            max: 4.0,
        })
    }
}
```

## Step 5: Whitelist Validation
```rust
const VIDEO_CODECS: &[&str] = &[
    "libx264", "libx265", "libvpx", "libvpx-vp9", "libaom-av1", "copy",
];

const AUDIO_CODECS: &[&str] = &[
    "aac", "libopus", "libmp3lame", "copy",
];

const PRESETS: &[&str] = &[
    "ultrafast", "superfast", "veryfast", "faster", "fast",
    "medium", "slow", "slower", "veryslow", "placebo",
];

pub fn validate_video_codec(codec: &str) -> Result<&str, BoundsError> {
    if VIDEO_CODECS.contains(&codec) {
        Ok(codec)
    } else {
        Err(BoundsError::InvalidValue {
            name: "video_codec".into(),
            value: codec.into(),
            allowed: VIDEO_CODECS.iter().map(|s| s.to_string()).collect(),
        })
    }
}

pub fn validate_preset(preset: &str) -> Result<&str, BoundsError> {
    if PRESETS.contains(&preset) {
        Ok(preset)
    } else {
        Err(BoundsError::InvalidValue {
            name: "preset".into(),
            value: preset.into(),
            allowed: PRESETS.iter().map(|s| s.to_string()).collect(),
        })
    }
}
```

## Step 6: Unit Tests
Test escape sequences, path validation, bounds checking.

## Verification
- Escape functions handle all special characters
- Path validation rejects null bytes
- Parameter validation rejects out-of-range values