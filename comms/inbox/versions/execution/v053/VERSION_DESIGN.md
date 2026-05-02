# v053 Version Design

## Overview

**Version:** v053
**Title:** E2E Playwright Tests - Comprehensive test suite for Phase 6 GUI workflows including workspace layout persistence, settings, batch panel rendering, keyboard navigation, and accessibility validation
**Themes:** 1

## Backlog Items

- [BL-297](C:\Users\grant\Documents\projects\auto-dev-projects\stoat-and-ferret\docs\auto-dev/BACKLOG.md#bl-297)

## Design Context

### Rationale

v053 delivers L-sized test-infrastructure work covering critical GUI workflows. Isolated as a single test-focused version to avoid regression risk from concurrent L-sized features. Builds on v052 accessibility infrastructure completion.

### Constraints

- Pure test-infrastructure — no production code changes to src/ or gui/src/
- All 6 journeys exercise existing Phase 6 APIs completed in v044 and v052
- Playwright infrastructure (config, axe-core, testing libraries) already installed
- CI integration via existing e2e and ci-a11y jobs

### Assumptions

- STOAT_TESTING_MODE env var will be added to ci.yml e2e job for J606 to function
- Element-level focus assertions (LRN-356 pattern) will be used instead of Tab simulation for J604
- Headless Chromium will require 2-3 CI cycles for J604/J605 integration

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-gui-e2e-playwright-suite | Implement comprehensive Playwright E2E test suite covering all critical Phase 6 GUI workflows — workspace layout persistence, settings/shortcuts, batch panel rendering, keyboard navigation, WCAG AA accessibility, and the seed endpoint roundtrip. | 3 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (gui-e2e-playwright-suite): Implement comprehensive Playwright E2E test suite covering all critical Phase 6 GUI workflows — workspace layout persistence, settings/shortcuts, batch panel rendering, keyboard navigation, WCAG AA accessibility, and the seed endpoint roundtrip.
