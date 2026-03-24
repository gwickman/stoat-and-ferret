# Playwright UAT Harness — Design Origin and Realisation

This document records the original design for browser-level E2E tests and how it was realised as the UAT journey harness.

## Original Design (Pre-Implementation)

The original plan called for a TypeScript-based Playwright test suite using `@playwright/test` as the runner, with 9 browser-level use cases, a `playwright.config.ts` for server management, and `data-testid` selectors. The design proposed:

- TypeScript test files (`*.spec.ts`) in a `gui/e2e/` directory
- `@playwright/test` runner with built-in assertions and retries
- `webServer` config in `playwright.config.ts` for automatic server startup
- 9 use cases covering health, scan, library, project, clips, effects, transitions, and delete flows

## What Was Actually Built (v022)

The UAT harness was implemented as **Python-based Playwright scripts** rather than TypeScript tests. This decision aligned the testing toolchain with the project's Python-first approach and simplified the dependency chain (no Node.js runtime needed for UAT).

### Key Differences from Original Design

| Aspect | Original Design | Actual Implementation |
|--------|----------------|----------------------|
| Language | TypeScript | Python |
| Runner | `@playwright/test` | `uat_runner.py` (custom Python orchestrator) |
| Test structure | 9 `*.spec.ts` files | 4 journey scripts (`uat_journey_201.py` – `uat_journey_204.py`) |
| Server management | `webServer` in `playwright.config.ts` | `uat_runner.py` manages subprocess directly |
| Evidence | Playwright traces + video on failure | Per-step screenshots + JSON/Markdown reports on every run |
| Scope | Individual use cases | End-to-end user journeys (each covering multiple use cases) |

### What Carried Forward

The core design principles from the original plan remain intact:

- **`data-testid` selectors** — All React components include `data-testid` attributes, and the journey scripts use `page.get_by_test_id()` for stable element selection
- **Headed/headless modes** — Developers can watch tests execute or run silently in CI
- **Depends on smoke tests** — UAT runs after API-level smoke tests pass
- **Screenshot evidence** — Visual debugging artifacts captured at each step
- **Real video files** — Same `/videos/` test files used by smoke tests

### Journey Coverage vs. Original Use Cases

The 4 journey scripts collectively cover the scope of the original 9 use cases:

| Original Use Case | Covered By |
|-------------------|------------|
| System Health | J201 (verifies app loads and serves pages) |
| Scan Directory | J201 (scan-library) |
| Browse Library | J201 (search/browse after scan) |
| Create Project | J202 (project-clip) |
| Add Clips | J202 (project-clip) |
| Apply Effect | J203 (effects-timeline) |
| Edit Effect | J203 (effects-timeline) |
| Apply Transition | J203 (effects-timeline) |
| Delete Flows | J203 (effect removal verified) |

J204 (export-render) is additional coverage not in the original design — it validates a seeded sample project end-to-end.

For full details on running UAT, interpreting results, and troubleshooting, see [`docs/manual/uat-testing.md`](../../manual/uat-testing.md).
