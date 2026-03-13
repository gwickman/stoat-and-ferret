# C4 Code Level: Sanitize Module

**Source:** `rust/stoat_ferret_core/src/sanitize/mod.rs`
**Component:** Rust Core

## Purpose

Input sanitization and validation functions to safely escape user input and validate parameters before inclusion in FFmpeg commands. All user-provided input should be sanitized before use in filter strings or command arguments.

## Public Interface

### Functions

#### Text Escaping

**`escape_filter_text(input: &str) -> String`**
- Escapes special characters in FFmpeg filter parameter text
- Escapes: `\` → `\\`, `'` → `'\''`, `:` → `\:`, `[` → `\[`, `]` → `\]`, `;` → `\;`, `\n` → `\n`, `\r` → `\r`
- Preserves UTF-8 characters
- Python binding: `escape_filter_text(text: str) -> str`

#### Path Validation

**`validate_path(path: &str) -> Result<(), PathError>`**
- Validates that a file path is safe to use
- Rejects empty paths → `PathError::Empty`
- Rejects paths containing null bytes → `PathError::ContainsNull`
- Note: Full directory allowlist validation deferred to Python layer
- Python binding: `validate_path(path: str) -> None` (raises ValueError)

#### Numeric Parameter Validation

**`validate_crf(crf: u8) -> Result<u8, BoundsError>`**
- Validates CRF (Constant Rate Factor) value
- Valid range: 0-51
- 0 = lossless, 18 = visually lossless, 23 = default, 51 = worst
- Python binding: `validate_crf(crf: int) -> int`

**`validate_speed(speed: f64) -> Result<f64, BoundsError>`**
- Validates video speed multiplier
- Valid range: 0.25-4.0
- 0.25 = quarter speed, 1.0 = normal, 4.0 = 4x faster
- Python binding: `validate_speed(speed: float) -> float`

**`validate_volume(volume: f64) -> Result<f64, BoundsError>`**
- Validates audio volume multiplier
- Valid range: 0.0-10.0
- 0.0 = muted, 1.0 = normal, 10.0 = 10x amplification
- Python binding: `validate_volume(volume: float) -> float`

#### Codec/Preset Validation (Whitelist)

**`validate_video_codec(codec: &str) -> Result<&str, BoundsError>`**
- Validates video codec against whitelist
- Allowed: libx264, libx265, libvpx, libvpx-vp9, libaom-av1, copy
- Python binding: `validate_video_codec(codec: str) -> str`

**`validate_audio_codec(codec: &str) -> Result<&str, BoundsError>`**
- Validates audio codec against whitelist
- Allowed: aac, libopus, libmp3lame, copy
- Python binding: `validate_audio_codec(codec: str) -> str`

**`validate_preset(preset: &str) -> Result<&str, BoundsError>`**
- Validates encoding preset against whitelist
- Allowed: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo
- Python binding: `validate_preset(preset: str) -> str`

### Error Types

#### `PathError`
- `PathError::Empty` — Path is empty
- `PathError::ContainsNull` — Path contains null byte (\0)
- Display: "Path cannot be empty" / "Path cannot contain null bytes"

#### `BoundsError`
Two variants:

**`OutOfRange { name: String, value: f64, min: f64, max: f64 }`**
- Numeric parameter outside valid range
- Display: "{name} value {value} is out of range (must be {min}-{max})"
- Example: "crf value 52 is out of range (must be 0-51)"

**`InvalidValue { name: String, value: String, allowed: Vec<String> }`**
- String parameter not in allowed whitelist
- Display: "{name} value '{value}' is not valid. Allowed: {allowed.join(", ")}"
- Example: "codec value 'unknown' is not valid. Allowed: libx264, libx265, ..."

## Dependencies

### Internal Crate Dependencies

None — sanitize module is self-contained and provides no functionality dependent on other crate modules.

### External Crate Dependencies

- **pyo3** — PyO3 Python bindings
- **pyo3_stub_gen** — Stub generation support

## Key Implementation Details

### Filter Text Escaping

FFmpeg filters use special characters with specific meaning. The escape function handles:

1. **Backslash (`\`)** → `\\` — Escape the escape character itself
2. **Single quote (`'`)** → `'\''` — FFmpeg quote escaping (close, escape, open)
3. **Colon (`:`)** → `\:` — Parameter separator in filter syntax
4. **Brackets (`[` and `]`)** → `\[` and `\]` — Stream label delimiters
5. **Semicolon (`;`)** → `\;` — Filter chain separator
6. **Newline (`\n`)** → `\n` — Escape for readability
7. **Carriage return (`\r`)** → `\r` — Escape for readability

### Security Model

**Escaping vs. Whitelisting:**
- **Escaping (`escape_filter_text`)** — For user-provided text content (overlays, labels)
- **Whitelisting (`validate_*` functions)** — For codec/preset names to prevent injection

Whitelist validation is safer for enumerated values where users can only choose from predefined options.

### Path Validation Scope

The `validate_path` function performs basic safety checks:
- Rejects empty strings (can't be valid paths)
- Rejects null bytes (C string compatibility)

Full directory allowlist validation (restricting to specific project directories) is deferred to the Python layer for flexibility and project-specific requirements.

### Numeric Bounds Strategy

All numeric bounds are inclusive on both ends and checked with `contains()` for clarity:
```rust
if (0.0..=10.0).contains(&volume) {
    Ok(volume)
} else {
    Err(BoundsError::OutOfRange { ... })
}
```

## Relationships

**Used by:**
- `ffmpeg` module — Validates codecs, presets, CRF before building commands
- Filter builders — Escape user text before inserting in filter parameters
- Python clip/video management — Validate user input before passing to Rust

**Uses:**
- (No internal dependencies)

## Testing

Comprehensive test suite with 50+ tests including:

1. **Text escaping (10 tests):**
   - Empty string
   - No special characters
   - Individual special characters
   - UTF-8 preservation
   - Mixed special characters

2. **Path validation (5 tests):**
   - Valid paths (simple, absolute, Windows, Unicode, spaces)
   - Empty path error
   - Null byte detection

3. **CRF validation (5 tests):**
   - Valid values (0, 23, 51)
   - Out of range errors
   - Maximum value boundary

4. **Speed validation (6 tests):**
   - Valid range (0.25-4.0)
   - Too slow (0.1)
   - Too fast (4.1, 10.0)
   - Boundary cases (zero, negative)

5. **Volume validation (5 tests):**
   - Valid range (0.0-10.0)
   - Negative values error
   - Too loud (10.1, 100.0)

6. **Codec validation (6 tests):**
   - All valid video codecs (libx264, libx265, libvpx, libvpx-vp9, libaom-av1, copy)
   - Invalid codec error
   - Case sensitivity (LIBX264 fails)
   - Injection attempt rejection

7. **Audio codec validation (4 tests):**
   - All valid codecs (aac, libopus, libmp3lame, copy)
   - Invalid codec error
   - Case sensitivity

8. **Preset validation (4 tests):**
   - All valid presets
   - Invalid preset error
   - Case sensitivity

9. **Error display (2 tests):**
   - BoundsError::OutOfRange display format
   - BoundsError::InvalidValue display format

## Notes

- **Case Sensitivity:** All whitelist validation is case-sensitive. FFmpeg codec names must be exact (e.g., "libx264" not "libX264").
- **Codec "copy":** The special codec "copy" is allowed for both video and audio to support stream copying without re-encoding.
- **Injection Prevention:** While escaping prevents command injection in filter strings, whitelisting for codecs is the primary defense against misuse.
- **UTF-8 Safe:** Text escaping preserves UTF-8 characters. Only ASCII special characters are escaped.
- **Empty Codec Handling:** Validate before use in commands. No validation of empty codec strings (treated as invalid).

## Example Usage

```python
from stoat_ferret_core import (
    escape_filter_text,
    validate_video_codec,
    validate_volume,
)

# Escape user-provided text for drawtext filter
text = "Hello; [user]: it's amazing!"
escaped = escape_filter_text(text)  # "Hello\; \[user\]\: it\'s amazing!"

# Validate codec selection
try:
    codec = validate_video_codec("libx264")
except ValueError as e:
    print(f"Invalid codec: {e}")

# Validate audio volume
try:
    volume = validate_volume(1.5)  # OK
    volume = validate_volume(15.0)  # Raises ValueError
except ValueError as e:
    print(f"Invalid volume: {e}")
```
