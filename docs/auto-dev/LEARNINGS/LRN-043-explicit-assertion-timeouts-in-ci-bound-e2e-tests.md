## Context

Playwright E2E tests use default assertion timeouts (typically 5 seconds) that assume local execution speed. CI environments (GitHub Actions) have variable performance characteristics where API responses plus React re-renders can exceed default timeouts.

## Learning

Every state-transition assertion in E2E specs (`toBeHidden()`, `toBeVisible()`, `toHaveText()`, etc.) should have an explicit timeout proportional to the expected operation duration. Default timeouts cause intermittent CI failures that are difficult to diagnose and block PR merges unpredictably. Apply explicit timeouts consistently from the start rather than waiting for CI failures to surface them.

## Evidence

In v008, a flaky `toBeHidden()` assertion in `project-creation.spec.ts` intermittently failed in CI with the default 5-second timeout. Adding `{ timeout: 10_000 }` fixed the flake. The project already had this pattern in other specs (`scan.spec.ts`, `effect-workshop.spec.ts`), validating the approach. The fix was a single line change — the cost of applying it proactively across all E2E specs is minimal.

## Application

When writing or reviewing E2E tests:
1. Add explicit `{ timeout: 10_000 }` (or appropriate value) to all state-transition assertions
2. Match existing timeout patterns in the codebase for consistency
3. Prefer explicit timeouts over retry loops — they're simpler and more predictable
4. Audit existing E2E specs periodically for assertions using default timeouts