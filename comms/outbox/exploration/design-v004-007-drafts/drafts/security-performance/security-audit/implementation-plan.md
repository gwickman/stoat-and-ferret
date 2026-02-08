# Implementation Plan — security-audit

## Overview

Conduct security audit of Rust sanitization functions, document findings, and implement critical remediation (ALLOWED_SCAN_ROOTS).

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `docs/design/09-security-audit.md` | Audit findings document |
| Modify | `src/stoat_ferret/api/services/scan.py` | Add ALLOWED_SCAN_ROOTS check |
| Modify | `src/stoat_ferret/settings.py` | Add ALLOWED_SCAN_ROOTS config |
| Create | `tests/test_security/test_path_validation.py` | Path traversal and injection tests |
| Create | `tests/test_security/test_input_sanitization.py` | Filter text and whitelist tests |
| Create | `tests/test_security/__init__.py` | Package init |

## Implementation Stages

### Stage 1: Audit
Systematically review each Rust sanitization function against known attack vectors. Document findings for: `escape_filter_text`, `validate_path`, `validate_crf`, `validate_speed`, `validate_volume`, `validate_video_codec`, `validate_audio_codec`, `validate_preset`.

### Stage 2: Security Tests
Write security-focused tests for path traversal (`../`, `..\\`, URL-encoded variants), null byte injection, shell injection in filter text, and whitelist bypass attempts.

### Stage 3: Remediation
Add `ALLOWED_SCAN_ROOTS` to settings with sensible defaults. Add path validation check in `scan_directory()` to reject paths outside allowed roots. This is ~20 lines of Python.

### Stage 4: Audit Document
Publish `docs/design/09-security-audit.md` with structured findings: function, attack vector, coverage status, and any remaining gaps.

## Quality Gates

- Security tests: 11–16 tests
- Audit document complete with no placeholder text
- ALLOWED_SCAN_ROOTS remediation implemented
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| Scope creep into Rust changes | Stick to Python-layer remediation per architecture decision |
| Missing attack vectors | Follow OWASP testing guide for file upload/path traversal |

## Commit Message

```
feat: add security audit with path validation and scan root restrictions
```
