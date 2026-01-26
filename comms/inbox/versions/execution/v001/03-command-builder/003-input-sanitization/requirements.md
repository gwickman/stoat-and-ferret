# Input Sanitization

## Goal
Ensure all user-provided input is safely escaped/validated before inclusion in FFmpeg commands.

## Requirements

### FR-001: Text Escaping
- Escape special characters in filter text: \\ ' : [ ] ;
- Handle newlines and control characters
- Support UTF-8 text safely

### FR-002: Path Validation
- Reject paths containing null bytes
- Reject empty paths
- Note: Full directory allowlist validation deferred to Python layer

### FR-003: Parameter Bounds
- CRF: 0 to 51
- Speed (setpts): 0.25 to 4.0
- Volume: 0.0 to 10.0

### FR-004: Codec/Format Validation
- Video codecs: whitelist (libx264, libx265, copy, etc.)
- Audio codecs: whitelist (aac, libopus, copy, etc.)
- Presets: whitelist (ultrafast through placebo)

## Acceptance Criteria
- [ ] Special characters properly escaped
- [ ] Null bytes rejected
- [ ] Parameter bounds enforced
- [ ] Invalid codec/format/preset names rejected