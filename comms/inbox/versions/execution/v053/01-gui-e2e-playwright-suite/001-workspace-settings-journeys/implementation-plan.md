# Feature 001: workspace-settings-journeys — Implementation Plan

## Overview

Implement J601 and J602 E2E tests covering workspace layout persistence (localStorage roundtrip for presets and panel sizes) and settings persistence (theme and keyboard shortcuts). Tests validate that `stoat-workspace-layout`, `stoat-theme`, and `stoat-shortcuts` keys survive page reloads, with correct state restoration. No production code changes; pure test-infrastructure work.

## Framework Guardrails

Per FRAMEWORK_CONTEXT.md:

**Frontend State Management (§3, Frontend):**
- Zustand stores (`workspaceStore`, `settingsStore`) are the source of truth for application state
- localStorage persistence is via Zustand's `persist` middleware
- E2E tests should verify Zustand → localStorage flow by reading localStorage directly (not internal store state)

**Testing Patterns (§3, Frontend, Testing):**
- Use Playwright `page.evaluate()` to read localStorage as JSON strings in the browser context
- No mocking of Zustand stores; real localStorage roundtrip testing
- Element-level DOM assertions (e.g., checking `data-theme` attribute on `<html>`) are preferred over inspecting component internals

**Playwright Configuration (§3, Frontend, Testing):**
- `gui/playwright.config.ts` defines `baseURL: http://localhost:8765/gui/` — all test URLs are relative
- `reuseExistingServer` flag handles CI server coordination; tests do not start the backend

**Quality Gates:**
- All E2E tests run in CI via the existing `e2e` job on every PR merge
- Playwright tests are part of the PR checks; they must pass before merge

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|----------|
| `tests/e2e/workspace-layout.spec.ts` | Create | J601 tests: workspace preset switch, panel resize, localStorage roundtrip, reload assertion |
| `tests/e2e/settings-persistence.spec.ts` | Create | J602 tests: theme toggle, keyboard shortcut rebinding, localStorage persistence |
| `tests/e2e/workspace-routing.spec.ts` | Modify | Add regression assertions: verify workspace layout doesn't break during routing transitions |

## Test Files

Tests to run for targeted validation (Stage 1 verification):
```
tests/e2e/workspace-layout.spec.ts tests/e2e/settings-persistence.spec.ts tests/e2e/workspace-routing.spec.ts
```

## Implementation Stages

### Stage 1: J601 — Workspace Layout Persistence

**Objectives:**
- Create workspace-layout.spec.ts with localStorage roundtrip test for presets and panel sizes
- Verify JSON structure in `stoat-workspace-layout` key
- Assert panel layout restoration after reload

**Implementation Steps:**
1. Create `tests/e2e/workspace-layout.spec.ts`
2. Test setup: navigate to `/gui/`, wait for workspace to load
3. Test: Set "edit" preset (default), manually resize effects panel to 25%, reload
4. Assert `localStorage.getItem("stoat-workspace-layout")` contains correct preset and custom size
5. Test: Switch to "review" preset via Ctrl+2, reload
6. Assert `stoat-workspace-layout.preset === "review"` and panel sizes match canonical review layout
7. Test: Return to "edit" preset, reload
8. Assert custom override persists in `sizesByPreset["edit"]` and panel layout matches custom sizes

**Verification Commands:**
```bash
npx playwright test tests/e2e/workspace-layout.spec.ts
```

### Stage 2: J602 — Settings Persistence

**Objectives:**
- Create settings-persistence.spec.ts with localStorage roundtrip test for theme and shortcuts
- Verify theme attribute on `<html>` element updates immediately
- Verify keyboard shortcut rebinding persists

**Implementation Steps:**
1. Create `tests/e2e/settings-persistence.spec.ts`
2. Test setup: navigate to `/gui/`, open settings panel (Ctrl+,)
3. Test: Toggle theme from "light" to "dark", assert `<html data-theme="dark">` updates
4. Close and reload page, assert `stoat-theme === "dark"` and theme attribute restored
5. Test: Rebind shortcut (e.g., `workspace.preset.edit` from Ctrl+1 to Ctrl+Shift+1), close settings
6. Assert settings panel closes and rebinding succeeded (no error toast)
7. Reload page, verify rebound shortcut works (Ctrl+Shift+1 switches to edit preset)
8. Verify old shortcut (Ctrl+1) no longer works
9. Assert `stoat-shortcuts` localStorage contains rebound key-to-action mapping

**Verification Commands:**
```bash
npx playwright test tests/e2e/settings-persistence.spec.ts
```

### Stage 3: Regression Assertions on Existing Routes

**Objectives:**
- Update workspace-routing.spec.ts to verify workspace layout doesn't break navigation
- Ensure F001 tests don't introduce regressions in other routing journeys

**Implementation Steps:**
1. Open `tests/e2e/workspace-routing.spec.ts`
2. Add regression test: Navigate between routes (library → effects → timeline) with custom preset active
3. Assert workspace layout persists across route transitions (no unwanted resets)
4. Verify panel visibility flags from `stoat-workspace-layout` don't interfere with route-specific layouts

**Verification Commands:**
```bash
npx playwright test tests/e2e/workspace-routing.spec.ts
```

## AC Traceability

| AC | File(s) | Stage |
|----|---------|-------|
| FR-001: Workspace Layout Persistence — initialize with default preset, switch presets, verify localStorage JSON structure on reload | `tests/e2e/workspace-layout.spec.ts` | Stage 1 |
| FR-002: Preset Switch Persistence — switch via keyboard shortcuts (Ctrl+1/2/3), verify localStorage updates, reload and assert preset matches | `tests/e2e/workspace-layout.spec.ts` | Stage 1 |
| FR-003: Theme Persistence — toggle theme, verify HTML `data-theme` attribute updates, reload and assert `stoat-theme` key persists | `tests/e2e/settings-persistence.spec.ts` | Stage 2 |
| FR-004: Keyboard Shortcut Persistence — rebind shortcut, reload and verify new binding works, assert old binding no longer active | `tests/e2e/settings-persistence.spec.ts` | Stage 2 |
| NFR-001: localStorage Performance — all operations complete without perceptible latency | `tests/e2e/workspace-layout.spec.ts`, `tests/e2e/settings-persistence.spec.ts` (implicit in real-time assertions) | Stage 1–2 |
| NFR-002: Browser Compatibility — persistence works on Chromium | CI `e2e` job runs tests on Chromium | All stages |
| NFR-003: No Data Loss — panel resizes don't corrupt JSON, preset switches preserve custom overrides | `tests/e2e/workspace-layout.spec.ts` (JSON validation), `tests/e2e/workspace-routing.spec.ts` (regression) | Stage 1, 3 |

## Quality Gates

### Pre-Implementation Checks
- Verify Zustand stores are accessible from Playwright (via `page.evaluate()` and window globals)
- Confirm `stoat-workspace-layout`, `stoat-theme`, `stoat-shortcuts` keys are set by v044+ stores
- Verify localStorage is cleared in Playwright before each test (no cross-test pollution)

### Test Execution (CI)
```bash
# Stage 1 verification
npx playwright test tests/e2e/workspace-layout.spec.ts tests/e2e/settings-persistence.spec.ts tests/e2e/workspace-routing.spec.ts
```

### CI Integration
- Tests run in the existing `e2e` job on every PR merge
- Chromium browser required; `playwright install chromium` pre-run in CI
- Tests timeout in 30s per spec (Playwright default); no custom timeout override needed

## Risks

| Risk | Probability | Mitigation |
|------|-------------|------------|
| localStorage not accessible in Playwright tests | Low | Zustand stores use standard HTML5 localStorage; `page.evaluate()` is standard pattern for reading it |
| Cross-test storage pollution | Low | Clear localStorage before each test; use `page.context().clearCookies()` + `page.evaluate()` delete |
| Preset sizes change in future versions | Medium | Test values are based on v044 PRESETS definitions; if sizes change, update hardcoded test values and commit as separate PR |
| Theme attribute not on `<html>` element | Low | Verified in research findings (Q10); theme application is direct DOM manipulation |
| Keyboard shortcut conflict detection differs from implementation | Low | Tests verify only that rebinding works; conflict detection is server-side (settingsStore validation) |

## Commit Message

```
feat(BL-297): Add E2E tests for workspace layout and settings persistence (J601–J602)

Implement J601 and J602 test journeys covering localStorage roundtrip for
workspace presets, panel sizes, theme, and keyboard shortcuts. Tests verify
state persistence across page reloads using Playwright page.evaluate() to
inspect localStorage directly. No production code changes.

Acceptance Criteria:
- FR-001: Workspace layout persists (preset, panel sizes, visibility)
- FR-002: Preset switches persist across reloads
- FR-003: Theme selection persists in localStorage
- FR-004: Keyboard shortcut rebinding persists

Test Files:
- tests/e2e/workspace-layout.spec.ts (new)
- tests/e2e/settings-persistence.spec.ts (new)
- tests/e2e/workspace-routing.spec.ts (updated with regression assertions)

Backlog: BL-297
```