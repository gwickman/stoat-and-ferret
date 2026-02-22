# Theme 02: ci-stability — Retrospective

## Summary

Fixed the flaky E2E test that intermittently blocked CI merges by adding an explicit 10-second timeout to the `toBeHidden()` assertion in the project-creation Playwright spec. This was a single, precisely-scoped change — one line in one file — that eliminates a recurring false-positive CI failure observed during v007 execution.

## Deliverables

| Feature | Status | Acceptance | Notes |
|---------|--------|------------|-------|
| 001-flaky-e2e-fix | Complete | 3/3 pass | Added `{ timeout: 10_000 }` to `toBeHidden()` in `gui/e2e/project-creation.spec.ts:37` |

All quality gates (ruff, mypy, pytest, tsc) passed on first iteration.

## Metrics

- **Source files changed:** 1 (`gui/e2e/project-creation.spec.ts`)
- **Net lines of code:** 1 line modified (timeout parameter added)
- **Test count:** No new tests — the fix is to the E2E test itself

## Key Decisions

### Timeout value selection
**Context:** The default Playwright assertion timeout of 5 seconds was insufficient in CI (GitHub Actions) where API response + React re-render can exceed that window.
**Choice:** Set explicit timeout to 10,000ms.
**Outcome:** Matches the project's established pattern — `scan.spec.ts` uses `10000` and `effect-workshop.spec.ts` uses `10_000` for similar assertions. Consistent and proportionate.

### No retry loop or test restructuring
**Context:** Could have wrapped the assertion in a retry loop or restructured the test flow.
**Choice:** Added only the timeout parameter, preserving the existing test structure.
**Outcome:** Minimal change, lowest risk. FR-002 ("no retry loops required") was an explicit acceptance criterion.

## Learnings

### What Went Well
- The fix was well-scoped as a single theme with a single feature — no wasted effort
- Root cause was clearly identified during v007 (documented in BL-055), making the fix straightforward
- Existing codebase already had the pattern (other specs with explicit timeouts), so the approach was validated by precedent

### What Could Improve
- This flake could have been caught earlier by applying explicit timeouts consistently across all E2E assertions from the start, rather than waiting for CI failures to surface them

### Patterns Discovered
- **Explicit assertion timeouts in CI-bound E2E tests:** Default Playwright timeouts assume local execution speed. GitHub Actions environments are slower and less predictable — every `toBeHidden()`, `toBeVisible()`, or similar state-transition assertion in E2E specs should have an explicit timeout proportional to the expected operation

## Technical Debt

- No quality-gaps.md files were generated — the feature passed cleanly
- No new technical debt introduced by this theme
- NFR-001 ("10 consecutive CI runs without flake") is a post-merge validation criterion — long-term flake recurrence should be monitored

## Action Items

- [ ] Audit remaining E2E specs for assertions using default timeouts that could flake in CI environments
- [ ] Monitor CI runs post-merge to confirm the flake is resolved (NFR-001 validation)
