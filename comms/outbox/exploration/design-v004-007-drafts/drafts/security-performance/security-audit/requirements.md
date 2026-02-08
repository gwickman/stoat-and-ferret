# Requirements — security-audit

## Goal

Audit Rust path validation, input sanitization, and `escape_filter_text` for security gaps.

## Background

M1.9 specifies a security review of Rust sanitization. The Rust core handles user-provided file paths and filter text. Key functions are documented in `004-research/codebase-patterns.md` §Rust Sanitization. Known gap: `validate_path` (`sanitize/mod.rs:230-238`) only checks empty and null bytes — no path traversal, symlink, or directory allowlist checks. Comment at line 206 defers full validation to Python layer. R4 investigation confirmed the gap is real but bounded: ~20 lines of Python for `ALLOWED_SCAN_ROOTS`.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | Review covers path traversal, null byte injection, and shell injection vectors in Rust core | BL-025 |
| FR-2 | Audit document published in `docs/` with findings and coverage assessment | BL-025 |
| FR-3 | Identified gaps addressed with new tests or code fixes | BL-025 |
| FR-4 | `ALLOWED_SCAN_ROOTS` configuration added to scan service for path validation | BL-025 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Audit document follows structured format: function, attack vector, coverage, finding |
| NFR-2 | Security tests cover OWASP-relevant attack vectors |
| NFR-3 | No changes to Rust `validate_path` — deferred-to-Python architecture is correct |

## Out of Scope

- Full penetration testing of the application
- Network security or authentication (no auth exists yet)
- Third-party dependency audit (cargo-audit, pip-audit)
- Modifying Rust validation functions beyond documenting gaps

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Security | Path traversal: `../`, `..\\`, encoded variants against validate_path | 3–5 |
| Security | Null byte injection: `\x00` in paths and filter text | 2–3 |
| Security | Shell injection: backticks, `$()`, pipes in filter text | 2–3 |
| Security | Symlink following: path resolves through symlinks | 1–2 |
| Security | Whitelist bypass: invalid codec/preset/format values | 2–3 |
