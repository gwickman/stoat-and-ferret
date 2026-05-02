# v053 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: gui-e2e-playwright-suite

**Path:** `C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret/comms/inbox/versions/execution/v053/01-gui-e2e-playwright-suite/`
**Goal:** Implement a comprehensive Playwright E2E test suite covering all critical Phase 6 GUI workflows — workspace layout persistence, settings/shortcuts, batch panel rendering, keyboard navigation, WCAG AA accessibility, and the seed endpoint roundtrip. All 6 journeys run in CI on every PR merge via the existing `e2e` and `ci-a11y` jobs.

**Features:**

- 001-workspace-settings-journeys: Test workspace layout and settings persistence across page reloads (localStorage persistence for presets, panel sizes, theme, and keyboard shortcuts)
- 002-batch-seed-journeys: Test batch panel WebSocket event handling and seed endpoint roundtrip testing workflow
- 003-keyboard-accessibility-enhancement: Enhance keyboard navigation testing and validate comprehensive accessibility compliance across all Phase 6 routes
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret/comms/outbox/
- Follow AGENTS.md for implementation process
