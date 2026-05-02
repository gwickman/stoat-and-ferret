# Feature 003: keyboard-accessibility-enhancement

## Goal

Enhance keyboard navigation testing (J604) and comprehensive WCAG AA accessibility validation (J605) across all Phase 6 routes. Verify skip-links, focus order, and keyboard shortcuts work correctly, and that all interactive elements meet WCAG 2.1 Level AA accessibility standards. Apply LRN-356 element-level focus assertions (instead of Tab simulation) for reliable testing in headless Chromium.

## Background

**Backlog Item:** BL-297 (E2E Playwright tests for critical GUI workflows)

**User Context:** Users rely on keyboard navigation and screen readers to access the application. This feature validates that:
- Skip-links allow keyboard users to jump to main content
- Focus order is logical and reflects visual layout
- All controls are keyboard accessible (no mouse-only interactions)
- All visual elements meet WCAG 2.1 Level AA color contrast and semantic HTML standards

**Prior Work:**
- v052 (BL-296) completed WCAG AA fixes: added AccessibilityWrapper, useAnnounce hook, ARIA landmarks, semantic HTML
- v052 Feature 004 created initial axe-core audit and keyboard navigation tests (J604, J605 partially exist)
- Task 007 identified axe baseline violations: color-contrast, select-name (to be excluded via `disableRules()`)
- LRN-356 documented element-level focus assertion pattern for headless Chromium reliability

Feature 003 expands J604/J605 to cover all Phase 6 routes and applies LRN-356 pattern.

## Functional Requirements

**FR-001: Skip-Link Functionality**
- On page load, skip-link should be invisible (visually off-screen via CSS)
- Tab to skip-link, verify it becomes visible and focusable
- Click skip-link, verify focus moves to main content area (not top of page)
- Keyboard users can reach main content without tabbing through header navigation
- Skip-link must be the first focusable element on the page (semantic HTML)

**FR-002: Focus Order Validation**
- Tab through all interactive elements on each Phase 6 route (edit, library, effects, preview, render/batch)
- Use element-level assertions: read `document.activeElement?.id` after each Tab press
- Verify focus order matches visual layout (left-to-right, top-to-bottom, or semantic grouping)
- Verify focus traps in modals: Tab stays within modal, does not escape to background
- Verify focus restoration: after closing modal, focus returns to triggering button

**FR-003: Keyboard Shortcut Accessibility**
- All keyboard shortcuts from settingsStore (Ctrl+1/2/3 for presets, Ctrl+, for settings) must be announced
- Settings panel must display shortcut hints (e.g., "Press Ctrl+1 to switch to edit preset")
- Shortcuts should not conflict with browser shortcuts (Ctrl+S, Ctrl+F, etc.)
- Custom rebinding must prevent reserved keys (Ctrl+S, Ctrl+T, Ctrl+W, etc.)

**FR-004: WCAG AA Compliance — Color Contrast**
- All text must have minimum 4.5:1 contrast ratio for normal text, 3:1 for large text
- Disabled elements may have lower contrast (acceptable per WCAG)
- Run axe-core audit on all routes to catch violations
- Pre-implementation baseline scan identifies known violations; exclude via `disableRules("color-contrast")` if unavoidable

**FR-005: WCAG AA Compliance — Semantic HTML**
- Form inputs must have associated labels (implicit or explicit `<label>` or `aria-label`)
- Buttons must have accessible names (text content or `aria-label`)
- Links must have visible text content (no `<a href="#">`)
- Headings must be properly nested (no skipping levels: `<h1>` → `<h3>`)
- Lists must use semantic `<ul>/<ol>/<li>` elements (not `<div>` role="list")

**FR-006: WCAG AA Compliance — Interactive Elements**
- All custom interactive components (sliders, comboboxes, tabs) must have proper ARIA roles
- Focus visible: all focusable elements must have visible focus indicator (`:focus-visible` style or outline)
- Touch targets: interactive elements must be ≥44×44 CSS pixels (or equivalent)
- State announcement: status changes (job complete, error, loading) must be announced via `aria-live` regions

**FR-007: Regression Assertions on Existing Routes**
- Verify J401–J404 (workspace routing) and J501–J504 (GUI features) don't break with accessibility enhancements
- Run smoke test on all existing routes to confirm no layout or functionality regressions
- Assert no new violations introduced by J604/J605 enhancements

## Non-Functional Requirements

**NFR-001: Test Reliability**
- Focus assertion pattern must work in headless Chromium (LRN-356 element-level, not Tab simulation)
- No flaky tests; all focus assertions must be deterministic (not timing-sensitive)

**NFR-002: Axe-Core Coverage**
- Comprehensive axe-core scans on all Phase 6 routes (edit, library, effects, preview, render/batch)
- Include dynamic routes (settings panel open, modal visible, dropdown expanded)
- Document known violations and exclusions in `disableRules()` calls

**NFR-003: Browser Compatibility**
- Tests run on Chromium (tested in CI `ci-a11y` job)
- Focus visible `:focus-visible` CSS selector supported in Chromium ≥86 (satisfied)

## Framework Decisions

Per FRAMEWORK_CONTEXT.md:

**Accessibility Testing Patterns (§3, Frontend):**
- Axe-core is the canonical pattern for automated accessibility auditing (already installed in v052)
- Element-level DOM assertions are preferred over testing implementation (internal state)
- `aria-live` regions are the approved pattern for announcing dynamic status changes

**Testing Patterns — Element-Level Focus Assertions (§3, Frontend, Testing, LRN-356):**
- Use `page.evaluate(() => document.activeElement?.id)` to read focus state from browser context
- Use `page.keyboard.press("Tab")` to navigate between elements
- **Do NOT** use Tab dispatch simulation (`element.focus() + keyboard.press("Tab")`) — unreliable in headless
- Verify focus order via sequence of element ID assertions, not implementation internals

**Startup Phases — Accessibility Initialization (not directly applicable but informative):**
- Accessibility infrastructure (AccessibilityWrapper, useAnnounce) is initialized in v052
- v053 tests assume this infrastructure exists; no startup changes needed

## Out of Scope

- Modifying skip-link or focus order implementation (assumed correct from v052)
- Integrating screen reader testing (NVDA, JAWS) — beyond scope of Playwright E2E
- Creating custom ARIA annotations (beyond WCAG AA baseline requirements)
- Testing mobile/touch accessibility (scope limited to keyboard + screen reader)

## Test Requirements

**Test Files:**
- Enhance `tests/e2e/keyboard-navigation.spec.ts` — expand skip-link and focus order tests to all Phase 6 routes using LRN-356 pattern
- Enhance `tests/e2e/accessibility.spec.ts` — add axe-core scans for settings panel and dynamic states; document known violations
- Create `tests/e2e/focus-restoration.spec.ts` — test focus traps and restoration in modals/dialogs
- Update `tests/e2e/workspace-routing.spec.ts`, `tests/e2e/workspace-layout.spec.ts` with regression assertions (confirm no accessibility or layout breakage)

**Test Strategy (per Task 006):**
- Pre-implementation: Run baseline axe-core scan on all Phase 6 routes with settings panel open; document violations in implementation plan
- Use Playwright `waitForLoadState("networkidle")` to ensure dynamic content loads before assertions
- Use `page.evaluate()` to read focus state from browser context (not internal component state)
- No mocking of accessibility libraries; real DOM and ARIA attributes
- Timeout: longer waits for axe-core audit completion (can take 5–10 seconds per route)

## Reference

See `C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret\comms\outbox\versions\design\v053\005-research\` for supporting evidence:
- Keyboard navigation patterns from v052 (Q13–14, findings 13–14): element-level assertions, LRN-356 pattern
- Axe-core infrastructure verified (Q15–16, findings 15–16): @axe-core/playwright v4.11.1 installed, J605 partially exists
- Existing J604/J605 tests (finding 8): 8 E2E test files present; J604 and J605 already exist and need expansion
- Accessibility testing setup (finding 16): axe scans on 6 routes, `disableRules()` for color-contrast, select-name
- Known accessibility fixes from v052 (Task 003 findings, retrospective): WCAG AA baseline with known exclusions