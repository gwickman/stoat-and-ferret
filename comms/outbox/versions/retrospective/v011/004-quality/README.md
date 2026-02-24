# v011 Quality Gate Report

All quality gates passed on the first run. No failures detected, no fixes required.

## Python File Changes

**Python files changed in v011:** YES (4 files)

- `src/stoat_ferret/api/app.py`
- `src/stoat_ferret/api/routers/filesystem.py`
- `src/stoat_ferret/api/schemas/filesystem.py`
- `tests/test_api/test_filesystem.py`

Changes from the `001-browse-directory` feature (BL-070) adding a directory listing endpoint.

## Initial Results

| Check | Status | Return Code | Duration |
|-------|--------|-------------|----------|
| ruff | PASS | 0 | 0.06s |
| mypy | PASS | 0 | 0.42s |
| pytest (988 tests) | PASS | 0 | 24.67s |
| contract tests (30 passed, 11 skipped) | PASS | 0 | 0.66s |
| repository contract tests (147 passed) | PASS | 0 | 1.31s |

**Golden scenarios:** Not applicable — `tests/system/scenarios/` does not exist in this project.

## Failure Classification

No failures to classify.

| Test | File | Classification | Action | Backlog |
|------|------|---------------|--------|---------|
| — | — | — | — | — |

## Test Problem Fixes

None required. All tests passed on first run.

## Code Problem Deferrals

None. No code problems detected.

## Final Results

No fixes were applied, so no rerun was necessary. Initial results are final.

| Check | Status |
|-------|--------|
| ruff | PASS |
| mypy | PASS |
| pytest | PASS |
| contract tests | PASS |
| parity tests | PASS |

## Outstanding Failures

None. All quality gates pass cleanly.
