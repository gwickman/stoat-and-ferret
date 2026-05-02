# Feature 003: keyboard-accessibility-enhancement — Implementation Plan

## Overview

Enhance keyboard navigation testing (J604) and WCAG AA accessibility validation (J605) across all Phase 6 routes (edit, library, effects, preview, render/batch). Apply LRN-356 element-level focus assertion pattern for reliable headless Chromium testing. Expand existing J604/J605 tests and add focus restoration testing. Include regression assertions to verify no accessibility or layout breakage in existing routes.

## Framework Guardrails

Per FRAMEWORK_CONTEXT.md:

**Accessibility Testing Patterns (§3, Frontend):**
- Axe-core is the canonical automated accessibility testing tool; @axe-core/playwright is installed
- Element-level DOM assertions are preferred over testing component internals
- aria-live regions are the approved pattern for dynamic status announcements

**Testing Patterns — Element-Level Focus Assertions (§3, Frontend, Testing, LRN-356):**
- Use `page.evaluate(() => document.activeElement?.id)` to read focus state from browser context
- Use `page.keyboard.press("Tab")` to navigate between elements
- **Never** use Tab dispatch simulation (`element.focus() + keyboard.press("Tab")`) in headless Chromium — unreliable
- Verify focus order via sequence of element ID assertions

**Startup Phases (informational, not directly applicable):**
- Accessibility infrastructure (AccessibilityWrapper, useAnnounce) is initialized during startup from v052
- v053 tests assume this infrastructure exists; no startup changes needed

**Quality Gates:**
- axe-core scans must be comprehensive (all routes, dynamic states)
- Known violations must be explicitly excluded via `disableRules()`; no silent failures

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|----------|
| `tests/e2e/keyboard-navigation.spec.ts` | Modify | Expand skip-link and focus order tests to all Phase 6 routes using LRN-356 element-level assertions |
| `tests/e2e/accessibility.spec.ts` | Modify | Add axe-core scans for settings panel and dynamic states; document baseline violations |
| `tests/e2e/focus-restoration.spec.ts` | Create | Test focus traps in modals/dialogs and focus restoration after close |
| `tests/e2e/workspace-routing.spec.ts` | Modify | Add regression assertions: verify accessibility/layout unchanged during routing |
| `tests/e2e/workspace-layout.spec.ts` | Modify | Add regression assertions: verify accessibility/layout unchanged during preset switches |

## Test Files

Tests to run for targeted validation (Stage 1 verification):
```
tests/e2e/keyboard-navigation.spec.ts tests/e2e/accessibility.spec.ts tests/e2e/focus-restoration.spec.ts tests/e2e/workspace-routing.spec.ts tests/e2e/workspace-layout.spec.ts
```

## Implementation Stages

### Stage 0: Pre-Implementation Baseline Scan (Blocking)

**Objectives:**
- Run axe-core baseline scan on all Phase 6 routes
- Identify pre-existing violations and document exclusions
- Populate `disableRules()` list before writing test assertions

**Implementation Steps:**
1. Start the application server locally (or in CI environment)
2. Create a temporary test script: `tests/e2e/baseline-scan.spec.ts` (not committed, for discovery only)
3. Run axe scans on each Phase 6 route:
   - `/gui/?workspace=edit` (default)
   - `/gui/?workspace=edit` with Library panel
   - `/gui/?workspace=edit` with Effects panel
   - `/gui/?workspace=edit` with Settings panel open
   - `/gui/?workspace=preview`
   - `/gui/?workspace=render` (with batch panel)
4. Document violations found (expected: color-contrast, select-name from v052)
5. **Do NOT commit baseline script; only use findings to populate implementation plan**
6. Update implementation plan below with discovered violations

**Baseline Violations Expected (from v052 retrospective):**
- `color-contrast`: Known issue with disabled buttons or certain UI elements (acceptable exclusion)
- `select-name`: Known issue with custom select components (acceptable exclusion)

**Baseline Violations to Discover:**
- `aria-required-attr`: If any required form inputs lack `required` attribute
- `label-title-only`: If any inputs have only `aria-label` without visible label
- `focus-order-semantics`: React-resizable-panels false positives (mitigation: `waitForSeparatorReady()`)

### Stage 1: J604 — Keyboard Navigation Expansion

**Objectives:**
- Expand existing keyboard-navigation.spec.ts with LRN-356 element-level focus assertions
- Test skip-links, focus order, and focus traps on all Phase 6 routes
- Verify focus restoration after modal close

**Implementation Steps:**
1. Open `tests/e2e/keyboard-navigation.spec.ts` (may already have skip-link tests from v052)
2. For each Phase 6 route (edit, library, effects, preview, render):
   a. Navigate to route via direct URL (e.g., `/gui/?workspace=edit`)
   b. Verify skip-link exists and is first focusable element
   c. Press Tab, verify skip-link is focused
   d. Press Enter, verify focus moves to main content (typically a panel or first interactive element)
   e. Continue tabbing, use `page.evaluate(() => document.activeElement?.id)` to verify focus order matches expected sequence
   f. For routes with modals (settings panel, effects form), test focus trap: Tab within modal should cycle back to first focusable element, NOT escape to background
   g. Close modal, verify focus returns to triggering button
3. Assert no unexpected focus jumps or focus loss

**Verification Commands:**
```bash
npx playwright test tests/e2e/keyboard-navigation.spec.ts
```

### Stage 2: J605 — Axe-Core Accessibility Scanning

**Objectives:**
- Expand existing accessibility.spec.ts with comprehensive axe-core scans
- Cover all Phase 6 routes including dynamic states (settings panel open, modals visible)
- Document known violations and exclusions in `disableRules()`

**Implementation Steps:**
1. Open `tests/e2e/accessibility.spec.ts` (may have initial axe scans from v052)
2. For each Phase 6 route + dynamic state combination:
   a. Navigate to route
   b. Trigger dynamic state (open settings panel, expand dropdown, etc.)
   c. Use `@axe-core/playwright` to scan: `await new AxeBuilder({ page }).analyze()`
   d. Document violations found
   e. For known violations (color-contrast, select-name), add to `disableRules(["color-contrast", "select-name"])`
   f. For new violations, investigate and either:
      - Fix in implementation (preferred)
      - Document as acceptable and exclude (rare)
3. Verify zero critical or serious violations after exclusions
4. Add `waitForSeparatorReady()` helper for react-resizable-panels false positives (from v052 pattern)

**Baseline Violations to Exclude (from discovery in Stage 0):**
```typescript
const axe = new AxeBuilder({ page })
  .disableRules(["color-contrast", "select-name"])
  .withWaitFor(/* any other exclusions discovered */);
```

**Verification Commands:**
```bash
npx playwright test tests/e2e/accessibility.spec.ts
```

### Stage 3: Focus Restoration Testing

**Objectives:**
- Create focus-restoration.spec.ts to test focus traps and restoration in modals
- Verify focus returns to correct element after modal close

**Implementation Steps:**
1. Create `tests/e2e/focus-restoration.spec.ts`
2. Test scenario 1: Settings modal
   a. Navigate to edit workspace
   b. Get ID of settings-trigger button (e.g., Ctrl+, keyboard shortcut or menu click)
   c. Open settings panel (click button or press Ctrl+,)
   d. Verify focus is within settings modal
   e. Tab within modal (focus should cycle within modal, not escape)
   f. Close settings (press Escape or click close button)
   g. Verify focus returns to settings-trigger button via `document.activeElement?.id`
3. Test scenario 2: Effects form modal
   a. Navigate to effects panel
   b. Click "Edit Effect" button to open effect settings form
   c. Get button ID before open
   d. Verify focus moves to form
   e. Tab within form (focus should stay in form)
   f. Close form (press Escape or click cancel)
   g. Verify focus returns to "Edit Effect" button
4. Verify modal focus traps don't break existing functionality

**Verification Commands:**
```bash
npx playwright test tests/e2e/focus-restoration.spec.ts
```

### Stage 4: Regression Assertions

**Objectives:**
- Add regression assertions to existing routing and layout tests
- Verify J604/J605 enhancements don't break existing functionality or introduce new violations

**Implementation Steps:**
1. Open `tests/e2e/workspace-routing.spec.ts`
   a. Add accessibility regression checks: after each route transition, verify no critical axe violations
   b. Use minimal axe scan (not full analysis, just critical checks)
2. Open `tests/e2e/workspace-layout.spec.ts`
   a. Add assertions after each preset switch: verify layout unchanged and no accessibility violations
3. Verify existing tests still pass without modification

**Verification Commands:**
```bash
npx playwright test tests/e2e/workspace-routing.spec.ts tests/e2e/workspace-layout.spec.ts
```

## AC Traceability

| AC | File(s) | Stage |
|----|---------|-------|
| FR-001: Skip-Link Functionality — visible on tab, moves focus to main content | `tests/e2e/keyboard-navigation.spec.ts` | Stage 1 |
| FR-002: Focus Order Validation — tab through routes, verify order, test focus traps in modals | `tests/e2e/keyboard-navigation.spec.ts`, `tests/e2e/focus-restoration.spec.ts` | Stage 1, 3 |
| FR-003: Keyboard Shortcut Accessibility — shortcuts announced, no conflicts with reserved keys | `tests/e2e/keyboard-navigation.spec.ts` (implicit in shortcut testing) | Stage 1 |
| FR-004: WCAG AA Compliance — Color Contrast — 4.5:1 minimum, axe-core audit | `tests/e2e/accessibility.spec.ts` (with `disableRules()` for known exclusions) | Stage 2 |
| FR-005: WCAG AA Compliance — Semantic HTML — labels, names, headings, lists | `tests/e2e/accessibility.spec.ts` (axe scans cover semantic checks) | Stage 2 |
| FR-006: WCAG AA Compliance — Interactive Elements — ARIA roles, focus visible, touch targets, state announcements | `tests/e2e/keyboard-navigation.spec.ts` (focus visible), `tests/e2e/accessibility.spec.ts` (ARIA, roles) | Stage 1–2 |
| FR-007: Regression Assertions — existing routes J401–J404, J501–J504 don't break | `tests/e2e/workspace-routing.spec.ts`, `tests/e2e/workspace-layout.spec.ts` | Stage 4 |
| NFR-001: Test Reliability — no flaky tests, LRN-356 element-level assertions | All stages (element-level assertions used throughout) | All |
| NFR-002: Axe-Core Coverage — comprehensive scans on all routes + dynamic states | `tests/e2e/accessibility.spec.ts` | Stage 2 |
| NFR-003: Browser Compatibility — tests run on Chromium with :focus-visible support | CI `ci-a11y` job runs tests on Chromium | All |

## Quality Gates

### Pre-Implementation (Stage 0)
- [ ] Baseline axe-core scan completed on all Phase 6 routes
- [ ] Known violations documented and captured in implementation plan
- [ ] `disableRules()` list finalized before writing tests

### Test Execution (All Stages)
```bash
# Stage 1 verification
npx playwright test tests/e2e/keyboard-navigation.spec.ts

# Stage 2 verification
npx playwright test tests/e2e/accessibility.spec.ts

# Stage 3 verification
npx playwright test tests/e2e/focus-restoration.spec.ts

# Stage 4 verification
npx playwright test tests/e2e/workspace-routing.spec.ts tests/e2e/workspace-layout.spec.ts

# All together
npx playwright test tests/e2e/keyboard-navigation.spec.ts tests/e2e/accessibility.spec.ts tests/e2e/focus-restoration.spec.ts tests/e2e/workspace-routing.spec.ts tests/e2e/workspace-layout.spec.ts
```

### CI Integration
- Tests run in dedicated `ci-a11y` job on every PR merge
- `ci-a11y` job runs `npx playwright test e2e/accessibility.spec.ts e2e/keyboard-navigation.spec.ts`
- Must pass without violations (or with documented exclusions only)

## Risks

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Undiscovered accessibility violations in Phase 6 routes | Medium | Stage 0 baseline scan identifies all violations; none should be missed |
| Element IDs not stable or don't exist on all routes | Medium | Pre-implementation: inspect DOM on all routes to verify element IDs for focus assertions |
| Focus restoration doesn't work in all modal types | Low | Test on both settings modal and effects form modal; similar patterns should generalize |
| Axe scans timeout or hang on complex routes | Low | Increase timeout to 60s for axe scans; complex routes may take 10–20s |
| LRN-356 pattern unreliable in CI environment | Low | Pattern is proven from v052; CI environment identical; should work immediately |
| React-resizable-panels false positives | Low | Mitigation: use `waitForSeparatorReady()` helper (from v052 pattern) |

## Commit Message

```
feat(BL-297): Enhance keyboard navigation and accessibility testing (J604–J605)

Expand keyboard navigation testing (J604) and WCAG AA accessibility validation
(J605) across all Phase 6 routes. Apply LRN-356 element-level focus assertions
for reliable headless Chromium testing. Add focus restoration testing for
modals. Include regression assertions on existing routes.

Uses element-level DOM inspection (document.activeElement) instead of Tab
simulation for focus order verification. Comprehensive axe-core scans on all
routes + dynamic states, with documented baseline violations excluded via
disableRules().

Acceptance Criteria:
- FR-001: Skip-links function correctly and move focus to main content
- FR-002: Focus order is logical and matches visual layout
- FR-003: Keyboard shortcuts are accessible and conflict-free
- FR-004: WCAG AA color contrast minimum met (4.5:1 for normal text)
- FR-005: Semantic HTML with proper labels, headings, lists
- FR-006: Interactive elements have ARIA roles, focus visible, touch targets
- FR-007: No regressions in existing routes (J401–J504)

Test Files:
- tests/e2e/keyboard-navigation.spec.ts (expanded)
- tests/e2e/accessibility.spec.ts (expanded)
- tests/e2e/focus-restoration.spec.ts (new)
- tests/e2e/workspace-routing.spec.ts (updated with regression checks)
- tests/e2e/workspace-layout.spec.ts (updated with regression checks)

Backlog: BL-297
```