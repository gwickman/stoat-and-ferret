# Theme: gui-e2e-playwright-suite

## Goal

Implement a comprehensive Playwright E2E test suite covering all critical Phase 6 GUI workflows — workspace layout persistence, settings/shortcuts, batch panel rendering, keyboard navigation, WCAG AA accessibility, and the seed endpoint roundtrip. All 6 journeys run in CI on every PR merge via the existing `e2e` and `ci-a11y` jobs.

## Design Artifacts

See `C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret\comms\outbox\versions\design\v053\` for full design analysis:
- **Logical Design**: `006-logical-design/README.md` — theme/feature breakdown, 3 features, 6 journeys
- **Risk Assessment**: `007-critical-thinking/README.md` — all risks resolved or mitigated
- **Research Findings**: `005-research/README.md` — localStorage keys, WebSocket schema, CI setup

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 1 | workspace-settings-journeys | BL-297 | Test workspace layout and settings persistence (J601–J602) |
| 2 | batch-seed-journeys | BL-297 | Test batch panel WebSocket events and seed endpoint roundtrip (J603, J606) |
| 3 | keyboard-accessibility-enhancement | BL-297 | Enhance keyboard navigation and validate WCAG AA compliance (J604–J605) |

## Dependencies

**No inter-feature code dependencies.** Features 1 and 2 can execute in parallel. Feature 3 is recommended last — the axe baseline scan (pre-implementation) is most useful after all new routes from Features 1–2 are available.

**External Dependencies (all met):**
- v044 completion (WorkspaceLayout, Presets, Settings, Batch Panel)
- v052 completion (WCAG AA fixes, accessibility infrastructure)
- v040 completion (Seed endpoint)

## Technical Approach

### Playwright E2E Framework
- **Config**: `gui/playwright.config.ts` with `baseURL: http://localhost:8765/gui/` and `reuseExistingServer` flag
- **Infrastructure**: Existing `e2e` job in CI; separate `ci-a11y` job for accessibility tests
- **Dependencies**: `@playwright/test`, `@axe-core/playwright` v4.11.1 already in package.json

### localStorage Persistence Pattern (J601–J602)
- Clear storage, set workspace preset, resize panels, reload page
- Assert panel sizes persist in `stoat-workspace-layout` JSON via `workspaceStore`
- Verify theme and shortcuts persist in `stoat-theme` and `stoat-shortcuts` keys

### WebSocket Event Testing Pattern (J603)
- Verify batch form submits to render API (HTTP POST)
- Listen for `render_progress` WebSocket events with schema: `{job_id, progress, eta_seconds, speed_ratio, frame_count, fps, encoder_name, encoder_type}`
- Assert progress bar updates in BatchJobList as events arrive

### Element-Level Focus Assertions (J604)
- Use LRN-356 pattern: `document.activeElement?.id` inspection, NOT Tab dispatch simulation
- Verify focus order via tabindex validation and `:focus-visible` CSS class
- Skip-link and focus order tests already exist; Feature 3 expands to Phase 6 routes

### Axe-Core Accessibility Scanning (J605)
- Use `@axe-core/playwright` to scan all Phase 6 routes for WCAG 2.1 Level AA violations
- Pre-implementation: Run baseline scan to identify violations and populate `disableRules()` (color-contrast, select-name already known)
- Use `waitForSeparatorReady()` helper for react-resizable-panels false positives

### Seed Endpoint Testing (J606)
- Verify endpoint schema: `POST /api/v1/testing/seed` → `{fixture_id, fixture_type, name}`
- Test full roundtrip: POST create → verify in Library → DELETE cleanup
- Confirm `seeded_` prefix enforced; requires `STOAT_TESTING_MODE=true` in CI

## Risks

| Risk | Mitigation |
|------|----------|
| **WebSocket batch event schema TBD** | Task 007 verified schema as `render_progress` with confirmed field names; J603 can assert specific values |
| **Headless Chromium focus assertions unreliable** | LRN-356 pattern (element-level assertions) adopted; 2–3 CI cycles budgeted for stabilization |
| **STOAT_TESTING_MODE missing from ci.yml** | Feature 002 must add env var to e2e job; otherwise J606 fails with HTTP 403 |
| **Axe baseline violations unknown** | Feature 3 executor runs baseline scan pre-implementation; violations added to `disableRules()` as discovered |
| **Parallel workers in CI** | `playwright.config.ts` sets `workers: 1` in CI; parallel fixture collision impossible; local runs use `Date.now()` naming |

## Quality Gates

- **Playwright tests**: `npx playwright test` in CI `e2e` and `ci-a11y` jobs
- **Accessibility validation**: axe-core audit on all Phase 6 routes (J605)
- **No production code impact**: All tests are additive; no src/ or gui/src/ changes

## CI Integration

**Existing CI jobs:**
- `e2e`: Runs `npx playwright test` after backend startup and frontend build (port 8765)
- `ci-a11y`: Dedicated accessibility job runs `npx playwright test e2e/accessibility.spec.ts e2e/keyboard-navigation.spec.ts`

**Feature 002 addition:** Add `env: STOAT_TESTING_MODE: "true"` to e2e job's "Run E2E tests" step to unblock J606.