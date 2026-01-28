# CI Path Filters (BL-017)

## Goal
Skip heavy CI jobs for docs-only commits using dorny/paths-filter.

## Requirements

### FR-001: Changes Detection Job
Add `changes` job that detects what file types changed:
- Code paths: `src/**`, `rust/**`, `tests/**`, `pyproject.toml`, `Cargo.toml`, `.github/workflows/**`
- Output: `code` boolean

### FR-002: Conditional Test Job
Make `test` job conditional on code changes:
```yaml
needs: changes
if: needs.changes.outputs.code == 'true'
```

### FR-003: CI Status Job
Add `ci-status` job that always succeeds:
- Runs after changes and test
- `if: always()`
- Satisfies branch protection required checks

### FR-004: Update Branch Protection
Document that branch protection should require `ci-status` not individual test jobs.

## Acceptance Criteria
- [ ] `changes` job detects file types
- [ ] `test` job skipped for docs-only commits
- [ ] `ci-status` job always runs
- [ ] Full test matrix runs for code changes