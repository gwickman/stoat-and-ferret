# Input Sanitization

## Goal
Ensure all user-provided input is safely escaped/validated before inclusion in FFmpeg commands.

## Requirements

### FR-001: Text Escaping
- Escape special characters in filter text: \ ' : [ ]
- Handle newlines and other control characters
- Support UTF-8 text safely

### FR-002: Path Validation
- Validate paths are within allowed directories
- Canonicalize paths to resolve ..
- Reject paths containing null bytes

### FR-003: Parameter Bounds
- Speed: 0.25 to 4.0
- Volume: 0.0 to 10.0
- CRF: 0 to 51
- Preset: validate against known values

### FR-004: Whitelist Approach
- Codec names from whitelist
- Format names from whitelist
- Pixel formats from whitelist

## Acceptance Criteria
- [ ] Special characters properly escaped
- [ ] Path traversal attacks prevented
- [ ] Parameter bounds enforced
- [ ] Invalid codec/format names rejected