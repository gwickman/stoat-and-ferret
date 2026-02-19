# Requirements: e2e-effect-workshop-tests

## Goal

E2E tests covering catalog browse, parameter config, preview, apply/edit/remove effects, and WCAG AA accessibility.

## Background

Backlog Item: BL-052

The effect workshop comprises multiple GUI components (catalog, form generator, preview, builder workflow) that must work together end-to-end. No E2E tests cover this workflow. The v005 Playwright infrastructure (with axe-core accessibility testing) provides the foundation. Tests navigate via client-side routing to work around the missing SPA fallback (LRN-023).

## Functional Requirements

**FR-001**: E2E test browses effect catalog and selects an effect
- AC: Test navigates to effect workshop via client-side clicks
- AC: Effect catalog loads and displays available effects
- AC: Test clicks on an effect to select it

**FR-002**: E2E test configures parameters and verifies filter preview updates in real time
- AC: Parameter form rendered for selected effect
- AC: Test changes parameter values
- AC: Filter string preview panel updates after parameter change

**FR-003**: E2E test applies effect to a clip and verifies effect stack display
- AC: Test selects a target clip
- AC: Test clicks "Apply" to add effect
- AC: Effect appears in the clip's effect stack

**FR-004**: E2E test edits and removes an applied effect successfully
- AC: Test clicks "Edit" on an applied effect
- AC: Parameter form opens with current values pre-filled
- AC: Test updates a parameter and saves
- AC: Test clicks "Remove" on an applied effect
- AC: Confirmation dialog appears, test confirms
- AC: Effect removed from stack

**FR-005**: Accessibility checks (WCAG AA) pass for all form components
- AC: axe-core scan reports no WCAG AA violations on effect catalog
- AC: axe-core scan reports no WCAG AA violations on parameter form
- AC: All form inputs have associated labels
- AC: Color contrast meets AA ratio (4.5:1)
- AC: Keyboard navigation works through full workflow (Tab, Enter, Space)

## Non-Functional Requirements

**NFR-001**: E2E tests complete in under 60 seconds total
- Metric: Full test suite runs within CI timeout

**NFR-002**: Tests are stable (no flaky failures)
- Metric: Tests pass consistently in CI across platforms

## Out of Scope

- Performance benchmarking
- Cross-browser testing (Playwright runs Chromium by default)
- Mobile viewport testing

## Test Requirements

E2E tests (Playwright):
- ~1 test: Browse catalog and select effect
- ~1 test: Configure parameters and verify preview
- ~1 test: Apply effect to clip and verify stack
- ~1 test: Edit applied effect
- ~1 test: Remove applied effect with confirmation
- ~1 test: WCAG AA axe-core scan

Accessibility assertions integrated within E2E tests:
- All form inputs have labels
- Color contrast meets AA
- Keyboard navigation through full workflow

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `codebase-patterns.md`: E2E test patterns, Playwright + axe-core, client-side navigation