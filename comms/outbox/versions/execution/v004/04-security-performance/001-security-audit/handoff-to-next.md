# Handoff: 001-security-audit → Next Feature

## What Was Done

- Security audit of all Rust sanitization functions (8 functions reviewed)
- Added `ALLOWED_SCAN_ROOTS` setting with `validate_scan_path()` enforcement
- Published audit document at `docs/design/09-security-audit.md`
- Added 35 security tests in `tests/test_security/`

## Key Decisions

- **No Rust changes**: The `validate_path` gap (no path traversal check) is
  by design. Python owns business logic; Rust owns low-level safety.
- **Empty allowlist = all allowed**: Default `allowed_scan_roots = []` permits
  all directories for backwards compatibility. Production deployments should
  configure this.
- **403 for scan root violations**: The scan endpoint returns HTTP 403 with
  `PATH_NOT_ALLOWED` code when a path is outside allowed roots.

## What to Watch For

- If authentication is added later, `ALLOWED_SCAN_ROOTS` should work in
  conjunction with user-level permissions.
- The `get_settings()` function uses `@lru_cache`, so `ALLOWED_SCAN_ROOTS`
  is read once at startup. Restart the server to apply config changes.
