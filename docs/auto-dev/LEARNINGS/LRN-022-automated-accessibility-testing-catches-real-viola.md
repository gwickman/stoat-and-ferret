## Context

Accessibility testing is often deferred or treated as optional. During v005 E2E test implementation, automated WCAG AA checks using axe-core were included alongside functional E2E tests.

## Learning

Include automated accessibility checks (e.g., axe-core with Playwright) as part of the E2E test suite from the start. These checks catch real WCAG violations that would otherwise ship to production. The cost of adding them is minimal compared to retrofitting accessibility later.

## Evidence

- v005 Theme 04 (e2e-test-suite): axe-core checks on dashboard, library, and projects views caught a real WCAG 4.1.2 violation — a `<select>` element missing `aria-label` in SortControls
- The violation was fixed immediately (single-line fix: added `aria-label="Sort by"`)
- Without automated checks, this violation would have persisted undetected

## Application

- Any web application with Playwright E2E tests: add `@axe-core/playwright` as a dev dependency
- Run accessibility checks on each main view/page as separate test cases
- Fix violations immediately rather than deferring — they're usually small fixes
- Consider adding to CI to prevent regression