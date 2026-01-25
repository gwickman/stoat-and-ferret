# Clip Validation Logic

## Goal
Implement validation logic for video clips with comprehensive, actionable error messages.

## Requirements

### FR-001: Clip Structure
- Validate source path exists (placeholder for now)
- Validate in-point >= 0
- Validate out-point > in-point
- Validate duration > 0

### FR-002: Temporal Bounds
- In-point must be within source duration (when known)
- Out-point must be within source duration (when known)
- Support unknown source duration (defer validation)

### FR-003: Error Messages
- Each error must identify the specific field
- Include actual vs expected values
- Suggest corrective action

### FR-004: Batch Validation
- Validate list of clips
- Return all errors, not just first
- Include clip index in errors

## Error Format
```rust
pub struct ValidationError {
    field: String,
    message: String,
    actual: Option<String>,
    expected: Option<String>,
}
```

## Acceptance Criteria
- [ ] All validation rules implemented
- [ ] Error messages are actionable
- [ ] Batch validation returns all errors
- [ ] Unit tests cover all error cases