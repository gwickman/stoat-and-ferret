# Requirements - 002: E2E Test Suite

## Goal

Write E2E tests covering navigation between tabs, scan trigger from library browser, project creation flow, and WCAG AA accessibility checks via `@axe-core/playwright`.

## Background

With Playwright infrastructure established (Feature 001), this feature writes the actual E2E test suite. BL-036 requires at least 3 E2E tests covering navigation, scan trigger, and project creation, plus accessibility checks (WCAG AA).

**Backlog Item:** BL-036

## Functional Requirements

**FR-001: Navigation test**
E2E test verifying navigation between Dashboard, Library, and Projects tabs with correct URL routing and panel rendering.
- AC: Test navigates between all tabs and verifies each panel loads correctly

**FR-002: Scan trigger test**
E2E test verifying scan trigger from library browser: open scan modal, enter directory path, submit, and verify scan feedback.
- AC: Test triggers a scan from the library browser and verifies progress feedback

**FR-003: Project creation test**
E2E test verifying project creation flow: open modal, fill form with valid settings, submit, and verify project appears in list.
- AC: Test creates a project via the modal and verifies it appears in the project list

**FR-004: WCAG AA accessibility checks**
Accessibility checks using `@axe-core/playwright` with `withTags(['wcag2a', 'wcag2aa'])` on each main view (dashboard, library, projects).
- AC: No WCAG AA violations on dashboard, library, and projects views

## Non-Functional Requirements

**NFR-001: Test stability**
E2E tests pass reliably with CI retries (max 2 retries). No flaky tests.
- Metric: Test pass rate > 95% across 20 consecutive runs

## Out of Scope

- Performance benchmarking via E2E tests
- Visual regression snapshots
- API-level integration tests (covered by pytest)
- WebSocket E2E tests (mock WebSocket in E2E; real WebSocket tested in pytest)

## Test Requirements

| Category | Requirements |
|----------|-------------|
| E2E tests | Navigation between Dashboard, Library, Projects tabs; scan trigger from library browser initiates scan and shows feedback; project creation flow (open modal, fill form, submit, verify in list) |
| Accessibility | `@axe-core/playwright` WCAG AA checks pass on each main view (dashboard, library, projects) |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.