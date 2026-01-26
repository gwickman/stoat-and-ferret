//! Input sanitization and validation for FFmpeg commands.
//!
//! This module provides functions to safely escape user input and validate
//! parameters before inclusion in FFmpeg commands. All user-provided input
//! should be sanitized using these functions before being used in filter
//! strings or command arguments.
//!
//! # Text Escaping
//!
//! The [`escape_filter_text`] function escapes special characters that have
//! meaning in FFmpeg filter syntax:
//!
//! ```
//! use stoat_ferret_core::sanitize::escape_filter_text;
//!
//! let text = "Hello; World: [test]";
//! let escaped = escape_filter_text(text);
//! assert_eq!(escaped, r"Hello\; World\: \[test\]");
//! ```
//!
//! # Path Validation
//!
//! The [`validate_path`] function ensures paths are safe to use:
//!
//! ```
//! use stoat_ferret_core::sanitize::{validate_path, PathError};
//!
//! assert!(validate_path("input.mp4").is_ok());
//! assert_eq!(validate_path(""), Err(PathError::Empty));
//! ```
//!
//! # Parameter Bounds
//!
//! Validation functions ensure numeric parameters are within valid ranges:
//!
//! ```
//! use stoat_ferret_core::sanitize::{validate_crf, validate_speed, validate_volume};
//!
//! assert!(validate_crf(23).is_ok());
//! assert!(validate_speed(1.5).is_ok());
//! assert!(validate_volume(1.0).is_ok());
//! ```
//!
//! # Codec/Preset Validation
//!
//! Whitelist validation ensures only known-safe codec and preset values are used:
//!
//! ```
//! use stoat_ferret_core::sanitize::{validate_video_codec, validate_preset};
//!
//! assert!(validate_video_codec("libx264").is_ok());
//! assert!(validate_preset("fast").is_ok());
//! ```

use std::fmt;

/// Errors that can occur when validating a file path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PathError {
    /// The path is empty.
    Empty,
    /// The path contains a null byte.
    ContainsNull,
}

impl fmt::Display for PathError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PathError::Empty => write!(f, "Path cannot be empty"),
            PathError::ContainsNull => write!(f, "Path cannot contain null bytes"),
        }
    }
}

impl std::error::Error for PathError {}

/// Errors that can occur when validating parameter bounds or values.
#[derive(Debug, Clone, PartialEq)]
pub enum BoundsError {
    /// A numeric parameter is outside its valid range.
    OutOfRange {
        /// The parameter name.
        name: String,
        /// The provided value.
        value: f64,
        /// The minimum valid value.
        min: f64,
        /// The maximum valid value.
        max: f64,
    },
    /// A string parameter is not in the allowed set of values.
    InvalidValue {
        /// The parameter name.
        name: String,
        /// The provided value.
        value: String,
        /// The allowed values.
        allowed: Vec<String>,
    },
}

impl fmt::Display for BoundsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BoundsError::OutOfRange {
                name,
                value,
                min,
                max,
            } => {
                write!(
                    f,
                    "{name} value {value} is out of range (must be {min}-{max})"
                )
            }
            BoundsError::InvalidValue {
                name,
                value,
                allowed,
            } => {
                write!(
                    f,
                    "{name} value '{value}' is not valid. Allowed: {}",
                    allowed.join(", ")
                )
            }
        }
    }
}

impl std::error::Error for BoundsError {}

/// Escapes special characters in text for use in FFmpeg filter parameters.
///
/// FFmpeg filter syntax uses several characters with special meaning. This
/// function escapes them so they are treated as literal characters.
///
/// # Escaped Characters
///
/// - `\` → `\\` (backslash)
/// - `'` → `'\''` (single quote - close, escape, open)
/// - `:` → `\:` (colon - parameter separator)
/// - `[` → `\[` (open bracket - stream label)
/// - `]` → `\]` (close bracket - stream label)
/// - `;` → `\;` (semicolon - chain separator)
/// - newline → `\n`
/// - carriage return → `\r`
///
/// # Arguments
///
/// * `input` - The text to escape
///
/// # Returns
///
/// The escaped text safe for use in FFmpeg filter parameters.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::escape_filter_text;
///
/// // Basic escaping
/// let text = "Hello; World";
/// assert_eq!(escape_filter_text(text), r"Hello\; World");
///
/// // Multiple special characters
/// let text = "text: [value]";
/// assert_eq!(escape_filter_text(text), r"text\: \[value\]");
///
/// // Newlines
/// let text = "line1\nline2";
/// assert_eq!(escape_filter_text(text), r"line1\nline2");
///
/// // UTF-8 is preserved
/// let text = "Hello, 世界!";
/// assert_eq!(escape_filter_text(text), "Hello, 世界!");
/// ```
#[must_use]
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

/// Validates that a file path is safe to use.
///
/// This function performs basic safety checks on paths:
/// - Rejects empty paths
/// - Rejects paths containing null bytes
///
/// Note: Full directory allowlist validation (restricting to specific
/// directories) is deferred to the Python layer.
///
/// # Arguments
///
/// * `path` - The path to validate
///
/// # Returns
///
/// `Ok(())` if the path is valid, or a `PathError` describing the issue.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::{validate_path, PathError};
///
/// // Valid paths
/// assert!(validate_path("input.mp4").is_ok());
/// assert!(validate_path("/path/to/file.mp4").is_ok());
/// assert!(validate_path("C:\\Users\\file.mp4").is_ok());
///
/// // Invalid paths
/// assert_eq!(validate_path(""), Err(PathError::Empty));
/// assert_eq!(validate_path("file\0.mp4"), Err(PathError::ContainsNull));
/// ```
pub fn validate_path(path: &str) -> Result<(), PathError> {
    if path.is_empty() {
        return Err(PathError::Empty);
    }
    if path.contains('\0') {
        return Err(PathError::ContainsNull);
    }
    Ok(())
}

/// Validates a CRF (Constant Rate Factor) value.
///
/// CRF is used for quality-based encoding with codecs like libx264 and libx265.
/// Valid range is 0-51, where:
/// - 0 = lossless
/// - 18 = visually lossless
/// - 23 = default
/// - 51 = worst quality
///
/// # Arguments
///
/// * `crf` - The CRF value to validate
///
/// # Returns
///
/// The validated CRF value, or a `BoundsError` if out of range.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::validate_crf;
///
/// assert_eq!(validate_crf(0), Ok(0));   // Lossless
/// assert_eq!(validate_crf(23), Ok(23)); // Default
/// assert_eq!(validate_crf(51), Ok(51)); // Maximum
/// assert!(validate_crf(52).is_err());   // Out of range
/// ```
pub fn validate_crf(crf: u8) -> Result<u8, BoundsError> {
    if crf <= 51 {
        Ok(crf)
    } else {
        Err(BoundsError::OutOfRange {
            name: "crf".into(),
            value: f64::from(crf),
            min: 0.0,
            max: 51.0,
        })
    }
}

/// Validates a speed multiplier for video playback.
///
/// Used with the `setpts` filter to change video speed. Valid range is 0.25-4.0:
/// - 0.25 = 4x slower (quarter speed)
/// - 1.0 = normal speed
/// - 4.0 = 4x faster
///
/// # Arguments
///
/// * `speed` - The speed multiplier to validate
///
/// # Returns
///
/// The validated speed value, or a `BoundsError` if out of range.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::validate_speed;
///
/// assert_eq!(validate_speed(0.25), Ok(0.25)); // Quarter speed
/// assert_eq!(validate_speed(1.0), Ok(1.0));   // Normal
/// assert_eq!(validate_speed(4.0), Ok(4.0));   // 4x speed
/// assert!(validate_speed(0.1).is_err());      // Too slow
/// assert!(validate_speed(5.0).is_err());      // Too fast
/// ```
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

/// Validates an audio volume multiplier.
///
/// Used with the `volume` filter to adjust audio levels. Valid range is 0.0-10.0:
/// - 0.0 = muted
/// - 1.0 = normal volume
/// - 10.0 = 10x amplification (use with caution)
///
/// # Arguments
///
/// * `volume` - The volume multiplier to validate
///
/// # Returns
///
/// The validated volume value, or a `BoundsError` if out of range.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::validate_volume;
///
/// assert_eq!(validate_volume(0.0), Ok(0.0));   // Muted
/// assert_eq!(validate_volume(1.0), Ok(1.0));   // Normal
/// assert_eq!(validate_volume(10.0), Ok(10.0)); // Max amplification
/// assert!(validate_volume(-0.1).is_err());     // Negative
/// assert!(validate_volume(11.0).is_err());     // Too loud
/// ```
pub fn validate_volume(volume: f64) -> Result<f64, BoundsError> {
    if (0.0..=10.0).contains(&volume) {
        Ok(volume)
    } else {
        Err(BoundsError::OutOfRange {
            name: "volume".into(),
            value: volume,
            min: 0.0,
            max: 10.0,
        })
    }
}

/// Allowed video codecs.
const VIDEO_CODECS: &[&str] = &[
    "libx264",
    "libx265",
    "libvpx",
    "libvpx-vp9",
    "libaom-av1",
    "copy",
];

/// Allowed audio codecs.
const AUDIO_CODECS: &[&str] = &["aac", "libopus", "libmp3lame", "copy"];

/// Allowed encoding presets.
const PRESETS: &[&str] = &[
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
    "placebo",
];

/// Validates a video codec name.
///
/// Only known-safe video codec names are allowed to prevent command injection.
///
/// # Allowed Codecs
///
/// - `libx264` - H.264/AVC encoder
/// - `libx265` - H.265/HEVC encoder
/// - `libvpx` - VP8 encoder
/// - `libvpx-vp9` - VP9 encoder
/// - `libaom-av1` - AV1 encoder
/// - `copy` - Stream copy (no re-encoding)
///
/// # Arguments
///
/// * `codec` - The codec name to validate
///
/// # Returns
///
/// The validated codec name, or a `BoundsError` if not in the allowed list.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::validate_video_codec;
///
/// assert_eq!(validate_video_codec("libx264"), Ok("libx264"));
/// assert_eq!(validate_video_codec("copy"), Ok("copy"));
/// assert!(validate_video_codec("unknown").is_err());
/// ```
pub fn validate_video_codec(codec: &str) -> Result<&str, BoundsError> {
    if VIDEO_CODECS.contains(&codec) {
        Ok(codec)
    } else {
        Err(BoundsError::InvalidValue {
            name: "video_codec".into(),
            value: codec.into(),
            allowed: VIDEO_CODECS.iter().map(|s| (*s).to_string()).collect(),
        })
    }
}

/// Validates an audio codec name.
///
/// Only known-safe audio codec names are allowed to prevent command injection.
///
/// # Allowed Codecs
///
/// - `aac` - Advanced Audio Coding
/// - `libopus` - Opus encoder
/// - `libmp3lame` - MP3 encoder
/// - `copy` - Stream copy (no re-encoding)
///
/// # Arguments
///
/// * `codec` - The codec name to validate
///
/// # Returns
///
/// The validated codec name, or a `BoundsError` if not in the allowed list.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::validate_audio_codec;
///
/// assert_eq!(validate_audio_codec("aac"), Ok("aac"));
/// assert_eq!(validate_audio_codec("copy"), Ok("copy"));
/// assert!(validate_audio_codec("unknown").is_err());
/// ```
pub fn validate_audio_codec(codec: &str) -> Result<&str, BoundsError> {
    if AUDIO_CODECS.contains(&codec) {
        Ok(codec)
    } else {
        Err(BoundsError::InvalidValue {
            name: "audio_codec".into(),
            value: codec.into(),
            allowed: AUDIO_CODECS.iter().map(|s| (*s).to_string()).collect(),
        })
    }
}

/// Validates an encoding preset name.
///
/// Presets control the encoding speed/quality tradeoff. Only known-safe
/// preset names are allowed.
///
/// # Allowed Presets
///
/// From fastest to slowest:
/// - `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`
/// - `medium` (default)
/// - `slow`, `slower`, `veryslow`, `placebo`
///
/// # Arguments
///
/// * `preset` - The preset name to validate
///
/// # Returns
///
/// The validated preset name, or a `BoundsError` if not in the allowed list.
///
/// # Examples
///
/// ```
/// use stoat_ferret_core::sanitize::validate_preset;
///
/// assert_eq!(validate_preset("fast"), Ok("fast"));
/// assert_eq!(validate_preset("medium"), Ok("medium"));
/// assert!(validate_preset("unknown").is_err());
/// ```
pub fn validate_preset(preset: &str) -> Result<&str, BoundsError> {
    if PRESETS.contains(&preset) {
        Ok(preset)
    } else {
        Err(BoundsError::InvalidValue {
            name: "preset".into(),
            value: preset.into(),
            allowed: PRESETS.iter().map(|s| (*s).to_string()).collect(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========== Text escaping tests ==========

    #[test]
    fn test_escape_filter_text_empty() {
        assert_eq!(escape_filter_text(""), "");
    }

    #[test]
    fn test_escape_filter_text_no_special() {
        assert_eq!(escape_filter_text("hello world"), "hello world");
    }

    #[test]
    fn test_escape_filter_text_backslash() {
        assert_eq!(escape_filter_text(r"path\to\file"), r"path\\to\\file");
    }

    #[test]
    fn test_escape_filter_text_single_quote() {
        assert_eq!(escape_filter_text("it's"), "it'\\''s");
    }

    #[test]
    fn test_escape_filter_text_colon() {
        assert_eq!(escape_filter_text("key:value"), r"key\:value");
    }

    #[test]
    fn test_escape_filter_text_brackets() {
        assert_eq!(escape_filter_text("[input]"), r"\[input\]");
    }

    #[test]
    fn test_escape_filter_text_semicolon() {
        assert_eq!(escape_filter_text("a;b"), r"a\;b");
    }

    #[test]
    fn test_escape_filter_text_newline() {
        assert_eq!(escape_filter_text("line1\nline2"), r"line1\nline2");
    }

    #[test]
    fn test_escape_filter_text_carriage_return() {
        assert_eq!(escape_filter_text("line1\rline2"), r"line1\rline2");
    }

    #[test]
    fn test_escape_filter_text_mixed() {
        assert_eq!(
            escape_filter_text("text: [value]; end"),
            r"text\: \[value\]\; end"
        );
    }

    #[test]
    fn test_escape_filter_text_utf8() {
        assert_eq!(escape_filter_text("Hello, 世界!"), "Hello, 世界!");
        // Colon is escaped
        assert_eq!(escape_filter_text("émoji: 🎬"), r"émoji\: 🎬");
    }

    #[test]
    fn test_escape_filter_text_utf8_with_special() {
        assert_eq!(escape_filter_text("日本語: テスト"), r"日本語\: テスト");
    }

    #[test]
    fn test_escape_filter_text_all_special() {
        // Input: \ ' : [ ] ;
        // After escaping: \\ '\'' \: \[ \] \;
        let input = "\\':[];";
        let expected = "\\\\'\\''\\:\\[\\]\\;";
        assert_eq!(escape_filter_text(input), expected);
    }

    // ========== Path validation tests ==========

    #[test]
    fn test_validate_path_valid() {
        assert!(validate_path("input.mp4").is_ok());
        assert!(validate_path("/path/to/file.mp4").is_ok());
        assert!(validate_path("C:\\Users\\file.mp4").is_ok());
        assert!(validate_path("file with spaces.mp4").is_ok());
        assert!(validate_path("文件.mp4").is_ok());
    }

    #[test]
    fn test_validate_path_empty() {
        assert_eq!(validate_path(""), Err(PathError::Empty));
    }

    #[test]
    fn test_validate_path_null_byte() {
        assert_eq!(validate_path("file\0.mp4"), Err(PathError::ContainsNull));
        assert_eq!(validate_path("\0"), Err(PathError::ContainsNull));
        assert_eq!(
            validate_path("path/to\0/file"),
            Err(PathError::ContainsNull)
        );
    }

    #[test]
    fn test_path_error_display() {
        assert_eq!(PathError::Empty.to_string(), "Path cannot be empty");
        assert_eq!(
            PathError::ContainsNull.to_string(),
            "Path cannot contain null bytes"
        );
    }

    // ========== CRF validation tests ==========

    #[test]
    fn test_validate_crf_valid() {
        assert_eq!(validate_crf(0), Ok(0));
        assert_eq!(validate_crf(23), Ok(23));
        assert_eq!(validate_crf(51), Ok(51));
    }

    #[test]
    fn test_validate_crf_invalid() {
        let result = validate_crf(52);
        assert!(result.is_err());
        match result.unwrap_err() {
            BoundsError::OutOfRange { name, value, .. } => {
                assert_eq!(name, "crf");
                assert_eq!(value, 52.0);
            }
            _ => panic!("Expected OutOfRange error"),
        }
    }

    #[test]
    fn test_validate_crf_max_invalid() {
        assert!(validate_crf(255).is_err());
    }

    // ========== Speed validation tests ==========

    #[test]
    fn test_validate_speed_valid() {
        assert_eq!(validate_speed(0.25), Ok(0.25));
        assert_eq!(validate_speed(1.0), Ok(1.0));
        assert_eq!(validate_speed(2.5), Ok(2.5));
        assert_eq!(validate_speed(4.0), Ok(4.0));
    }

    #[test]
    fn test_validate_speed_too_slow() {
        let result = validate_speed(0.1);
        assert!(result.is_err());
        match result.unwrap_err() {
            BoundsError::OutOfRange { name, min, max, .. } => {
                assert_eq!(name, "speed");
                assert_eq!(min, 0.25);
                assert_eq!(max, 4.0);
            }
            _ => panic!("Expected OutOfRange error"),
        }
    }

    #[test]
    fn test_validate_speed_too_fast() {
        assert!(validate_speed(4.1).is_err());
        assert!(validate_speed(10.0).is_err());
    }

    #[test]
    fn test_validate_speed_zero() {
        assert!(validate_speed(0.0).is_err());
    }

    #[test]
    fn test_validate_speed_negative() {
        assert!(validate_speed(-1.0).is_err());
    }

    // ========== Volume validation tests ==========

    #[test]
    fn test_validate_volume_valid() {
        assert_eq!(validate_volume(0.0), Ok(0.0));
        assert_eq!(validate_volume(0.5), Ok(0.5));
        assert_eq!(validate_volume(1.0), Ok(1.0));
        assert_eq!(validate_volume(5.0), Ok(5.0));
        assert_eq!(validate_volume(10.0), Ok(10.0));
    }

    #[test]
    fn test_validate_volume_negative() {
        let result = validate_volume(-0.1);
        assert!(result.is_err());
        match result.unwrap_err() {
            BoundsError::OutOfRange { name, min, max, .. } => {
                assert_eq!(name, "volume");
                assert_eq!(min, 0.0);
                assert_eq!(max, 10.0);
            }
            _ => panic!("Expected OutOfRange error"),
        }
    }

    #[test]
    fn test_validate_volume_too_loud() {
        assert!(validate_volume(10.1).is_err());
        assert!(validate_volume(100.0).is_err());
    }

    // ========== Video codec validation tests ==========

    #[test]
    fn test_validate_video_codec_valid() {
        assert_eq!(validate_video_codec("libx264"), Ok("libx264"));
        assert_eq!(validate_video_codec("libx265"), Ok("libx265"));
        assert_eq!(validate_video_codec("libvpx"), Ok("libvpx"));
        assert_eq!(validate_video_codec("libvpx-vp9"), Ok("libvpx-vp9"));
        assert_eq!(validate_video_codec("libaom-av1"), Ok("libaom-av1"));
        assert_eq!(validate_video_codec("copy"), Ok("copy"));
    }

    #[test]
    fn test_validate_video_codec_invalid() {
        let result = validate_video_codec("unknown");
        assert!(result.is_err());
        match result.unwrap_err() {
            BoundsError::InvalidValue {
                name,
                value,
                allowed,
            } => {
                assert_eq!(name, "video_codec");
                assert_eq!(value, "unknown");
                assert!(allowed.contains(&"libx264".to_string()));
            }
            _ => panic!("Expected InvalidValue error"),
        }
    }

    #[test]
    fn test_validate_video_codec_case_sensitive() {
        // Codecs are case-sensitive
        assert!(validate_video_codec("LIBX264").is_err());
        assert!(validate_video_codec("LibX264").is_err());
    }

    #[test]
    fn test_validate_video_codec_injection_attempt() {
        assert!(validate_video_codec("libx264; rm -rf /").is_err());
        assert!(validate_video_codec("$(whoami)").is_err());
    }

    // ========== Audio codec validation tests ==========

    #[test]
    fn test_validate_audio_codec_valid() {
        assert_eq!(validate_audio_codec("aac"), Ok("aac"));
        assert_eq!(validate_audio_codec("libopus"), Ok("libopus"));
        assert_eq!(validate_audio_codec("libmp3lame"), Ok("libmp3lame"));
        assert_eq!(validate_audio_codec("copy"), Ok("copy"));
    }

    #[test]
    fn test_validate_audio_codec_invalid() {
        let result = validate_audio_codec("unknown");
        assert!(result.is_err());
        match result.unwrap_err() {
            BoundsError::InvalidValue {
                name,
                value,
                allowed,
            } => {
                assert_eq!(name, "audio_codec");
                assert_eq!(value, "unknown");
                assert!(allowed.contains(&"aac".to_string()));
            }
            _ => panic!("Expected InvalidValue error"),
        }
    }

    #[test]
    fn test_validate_audio_codec_case_sensitive() {
        assert!(validate_audio_codec("AAC").is_err());
        assert!(validate_audio_codec("Aac").is_err());
    }

    // ========== Preset validation tests ==========

    #[test]
    fn test_validate_preset_valid() {
        let presets = [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
            "placebo",
        ];
        for preset in presets {
            assert_eq!(validate_preset(preset), Ok(preset));
        }
    }

    #[test]
    fn test_validate_preset_invalid() {
        let result = validate_preset("unknown");
        assert!(result.is_err());
        match result.unwrap_err() {
            BoundsError::InvalidValue {
                name,
                value,
                allowed,
            } => {
                assert_eq!(name, "preset");
                assert_eq!(value, "unknown");
                assert!(allowed.contains(&"fast".to_string()));
            }
            _ => panic!("Expected InvalidValue error"),
        }
    }

    #[test]
    fn test_validate_preset_case_sensitive() {
        assert!(validate_preset("Fast").is_err());
        assert!(validate_preset("MEDIUM").is_err());
    }

    // ========== BoundsError display tests ==========

    #[test]
    fn test_bounds_error_out_of_range_display() {
        let error = BoundsError::OutOfRange {
            name: "crf".into(),
            value: 52.0,
            min: 0.0,
            max: 51.0,
        };
        assert_eq!(
            error.to_string(),
            "crf value 52 is out of range (must be 0-51)"
        );
    }

    #[test]
    fn test_bounds_error_invalid_value_display() {
        let error = BoundsError::InvalidValue {
            name: "codec".into(),
            value: "unknown".into(),
            allowed: vec!["aac".into(), "opus".into()],
        };
        assert_eq!(
            error.to_string(),
            "codec value 'unknown' is not valid. Allowed: aac, opus"
        );
    }
}
