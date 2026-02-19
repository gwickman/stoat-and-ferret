Fix the flaky E2E test in gui/e2e/project-creation.spec.ts at line 31.

## Problem

The test intermittently fails with a `toBeHidden` assertion timeout on the project creation modal. It fails on main (GitHub Actions run 22188785818) independent of any feature branch. Likely cause: timing-dependent modal animation or state cleanup between tests.

## Investigation Steps

1. Read gui/e2e/project-creation.spec.ts and understand what line 31 is asserting
2. Look at the project creation modal component to understand its show/hide lifecycle
3. Identify why `toBeHidden` would time out — check for animations, async state updates, or missing cleanup
4. Check if other E2E tests have similar patterns that work reliably

## Fix Requirements

- Make the toBeHidden assertion reliable without increasing timeouts excessively
- Ensure modal state is properly cleaned up between tests
- Do NOT change the functional behavior being tested
- Run the E2E tests locally to verify the fix if possible (npm run test:e2e or npx playwright test from gui/)

## Output Requirements

Create findings in comms/outbox/exploration/fix-flaky-e2e-test/:

### README.md (required)
First paragraph: Summary of root cause and fix applied.
Then: Details of what was changed and why.

### root-cause.md
Analysis of why the test was flaky — what timing/state issue caused it.

### fix-details.md
What code changes were made, with before/after snippets.

## Guidelines
- Under 200 lines per document
- Include code snippets
- Commit the fix AND the exploration docs separately

## When Complete
git add gui/e2e/project-creation.spec.ts
git commit -m "fix: resolve flaky toBeHidden assertion in project-creation E2E test (BL-055)"
git add comms/outbox/exploration/fix-flaky-e2e-test/
git commit -m "exploration: fix-flaky-e2e-test complete"
