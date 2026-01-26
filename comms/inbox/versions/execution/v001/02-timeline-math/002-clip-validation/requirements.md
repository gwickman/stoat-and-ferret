# Clip Validation Logic

## Goal
Implement validation logic for video clips with comprehensive, actionable error messages.

## Requirements

### FR-001: Clip Structure
- Define Clip struct with source_path, in_point, out_point, source_duration
- Validate source path is non-empty
- Validate in_point >= 0 (always true with u64)
- Validate out_point > in_point
- Validate duration > 0

### FR-002: Temporal Bounds
- In-point must be within source duration (when known)
- Out-point must be within source duration (when known)
- Support unknown source duration (skip bounds validation)

### FR-003: Error Messages
- Each error must identify the specific field
- Include actual vs expected values
- Suggest corrective action

### FR-004: Batch Validation
- Validate list of clips
- Return all errors, not just first
- Include clip index in errors

## Acceptance Criteria
- [ ] All validation rules implemented
- [ ] Error messages are actionable
- [ ] Batch validation returns all errors
- [ ] Unit tests cover all error cases