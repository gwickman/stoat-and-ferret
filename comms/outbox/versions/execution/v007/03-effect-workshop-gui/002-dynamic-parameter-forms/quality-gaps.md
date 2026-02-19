# Quality Gaps: 002-dynamic-parameter-forms

## Pre-existing Flaky E2E Test

**File:** `gui/e2e/project-creation.spec.ts:31`
**Issue:** The `toBeHidden` assertion for `create-project-modal` times out. The modal remains visible after form submission. This test fails intermittently on CI (failed 3/3 attempts on this PR, also fails on `main` branch run 22188785818).

**Impact on this feature:** None. The failing test is for the project creation modal, completely unrelated to the effect parameter form. All feature-specific checks pass (frontend vitest, tsc, ruff, mypy, pytest).

**Recommendation:** Fix the flaky E2E test separately. The `create-project-modal` dismiss timing may need a longer timeout or a `waitForSelector` approach.
