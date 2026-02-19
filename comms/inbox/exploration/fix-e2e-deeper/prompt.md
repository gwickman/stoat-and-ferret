Investigate and fix the persistent E2E test failure in gui/e2e/project-creation.spec.ts (tracked as BL-055).

## Context

This test has been failing in CI across multiple PRs and on main, blocking v007 execution.

## Facts Gathered So Far

### From PR #88 (dynamic-parameter-forms):
- The test at line 31 fails with a `toBeHidden` assertion timeout on the create-project-modal
- Same test fails on main (GitHub Actions run 22188785818)
- Was retried 3 times without resolution
- All other quality gates pass (ruff, mypy, pytest, tsc, vitest)

### From a previous fix attempt (committed):
- A `page.waitForResponse()` was added before the click to synchronize on the POST /api/v1/projects completing before asserting toBeHidden
- Hypothesis was that the modal raced against backend latency
- This fix is currently committed in the repo

### From PR #89 (live-filter-preview), run AFTER the fix was committed:
- The same E2E test still fails
- The completion report states: "The POST /api/v1/projects call appears to fail consistently in CI (the catch block in CreateProjectModal keeps the modal open and shows the error). This is NOT a timing issue — increasing the timeout to 10s made no difference."
- Only project-creation E2E test fails; all 6 other E2E tests pass
- All unit tests, integration tests, and type checks pass across all platforms

## Your Task

1. Investigate the full chain: the E2E test, the modal component, the API endpoint, and the CI E2E environment configuration
2. Determine the actual root cause — why does POST /api/v1/projects fail in CI but work elsewhere?
3. Fix it
4. If you can run the E2E tests locally to verify, do so

## Output Requirements

Create findings in comms/outbox/exploration/fix-e2e-deeper/:

### README.md (required)
First paragraph: Summary of actual root cause and fix applied.
Then: Details of investigation and what was changed.

### investigation.md
Full investigation trail — what you checked, what you found, what you ruled out.

### fix-details.md
What code changes were made, with before/after snippets and rationale.

## Guidelines
- Under 200 lines per document
- Include code snippets
- Commit the fix AND the exploration docs separately

## When Complete
git add -A
git commit -m "fix: resolve persistent E2E project-creation failure in CI (BL-055)"
git add comms/outbox/exploration/fix-e2e-deeper/
git commit -m "exploration: fix-e2e-deeper complete"
