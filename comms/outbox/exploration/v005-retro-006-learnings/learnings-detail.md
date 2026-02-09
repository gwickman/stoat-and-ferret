# v005 Learning Extraction: Detailed Learnings

## LRN-020: Conditional Static Mount Pattern for Optional Frontend Serving

**Tags:** fastapi, patterns, testing, frontend, static-files
**Source:** v005/01-frontend-foundation, v005/04-e2e-testing

### Context

When a FastAPI backend optionally serves a built frontend (e.g., React/Vite), the `StaticFiles` mount raises errors if the target directory doesn't exist — such as during backend-only tests or before the first frontend build.

### Learning

Only mount `StaticFiles` when the target directory actually exists. This conditional mount pattern decouples backend testing from frontend build state. Combined with auto-loading from settings when not explicitly provided, this enables both test isolation and seamless production serving.

### Evidence

- v005 Theme 01 (frontend-scaffolding): Conditional mount ensured `pytest` passed without requiring `npm run build` first
- v005 Theme 04 (playwright-setup): Modified `create_app()` to auto-load `gui_static_path` from settings when not explicitly provided, enabling `uvicorn --factory` to serve the built frontend for E2E tests
- Backend test suite (627 tests) ran without frontend build throughout all 11 features

### Application

- Any FastAPI/Starlette project that optionally serves a built SPA frontend
- Services where a frontend build artifact may or may not be present at runtime
- Pattern: check `Path(static_path).is_dir()` before mounting, and provide DI override for tests

---

## LRN-021: Separate Vitest Config for Vite 7+ Projects

**Tags:** frontend, vite, vitest, typescript, configuration
**Source:** v005/01-frontend-foundation/001-frontend-scaffolding

### Context

When using Vite 7 with Vitest 4, the inline `test` configuration block inside `vite.config.ts` causes TypeScript errors. This is a breaking change from earlier Vite/Vitest versions where inline test config worked.

### Learning

Use a separate `vitest.config.ts` file instead of inline test configuration in `vite.config.ts` when using Vite 7+ with Vitest 4+. This provides clean separation of build and test configuration and avoids TypeScript compatibility issues.

### Evidence

- v005 Theme 01 (frontend-scaffolding): Discovered TypeScript error when attempting inline `test` config in `vite.config.ts` with Vite 7 + Vitest 4
- Separate `vitest.config.ts` file resolved the issue cleanly
- Also needed `exclude: ['e2e/**']` in vitest config to prevent picking up Playwright tests (Theme 04)

### Application

- Any React/TypeScript project using Vite 7+ with Vitest 4+
- When upgrading from older Vite/Vitest versions where inline config worked
- Remember to add E2E test directory exclusions in vitest config when adding Playwright

---

## LRN-022: Automated Accessibility Testing Catches Real Violations

**Tags:** accessibility, testing, e2e, playwright, wcag
**Source:** v005/04-e2e-testing/002-e2e-test-suite

### Context

Accessibility testing is often deferred or treated as optional. During v005 E2E test implementation, automated WCAG AA checks using axe-core were included alongside functional E2E tests.

### Learning

Include automated accessibility checks (e.g., axe-core with Playwright) as part of the E2E test suite from the start. These checks catch real WCAG violations that would otherwise ship to production. The cost of adding them is minimal compared to retrofitting accessibility later.

### Evidence

- v005 Theme 04 (e2e-test-suite): axe-core checks on dashboard, library, and projects views caught a real WCAG 4.1.2 violation — a `<select>` element missing `aria-label` in SortControls
- The violation was fixed immediately (single-line fix: added `aria-label="Sort by"`)
- Without automated checks, this violation would have persisted undetected

### Application

- Any web application with Playwright E2E tests: add `@axe-core/playwright` as a dev dependency
- Run accessibility checks on each main view/page as separate test cases
- Fix violations immediately rather than deferring — they're usually small fixes
- Consider adding to CI to prevent regression

---

## LRN-023: Client-Side Navigation for SPA E2E Tests Without Server-Side Routing

**Tags:** e2e, testing, spa, routing, playwright
**Source:** v005/04-e2e-testing/002-e2e-test-suite

### Context

When a FastAPI backend serves a React SPA via `StaticFiles`, the server doesn't handle SPA fallback routing. Direct URL navigation to sub-paths like `/gui/library` returns 404 because `StaticFiles` looks for a literal file at that path.

### Learning

E2E tests for SPAs served via static file mounts must navigate via client-side routing (clicking UI elements) starting from the root path, not via direct URL navigation to sub-paths. This accurately reflects how users interact with the application and avoids false failures from missing server-side routing.

### Evidence

- v005 Theme 04 (e2e-test-suite): All E2E tests navigate by starting at `/gui/` and clicking tab elements
- Direct URL navigation to `/gui/library` or `/gui/projects` would fail with FastAPI's `StaticFiles` mount
- Tests accurately reflect user behavior (click-based navigation)
- This limitation also means bookmarks to sub-routes won't work — identified as tech debt (SPA fallback routing)

### Application

- Any SPA served via static file hosting without server-side routing (FastAPI StaticFiles, nginx without try_files, etc.)
- Design E2E tests to navigate via UI interactions from the root path
- Consider adding a catch-all route serving `index.html` for production deployments to support deep linking

---

## LRN-024: Focused Zustand Stores Over Monolithic State Management

**Tags:** frontend, react, state-management, zustand, patterns
**Source:** v005/03-gui-components (cross-theme pattern)

### Context

React applications need state management for cross-component data sharing. Options range from heavyweight solutions (Redux) to lightweight alternatives (Zustand, Jotai, Context API).

### Learning

Use multiple focused Zustand stores scoped to feature domains rather than a single monolithic store or a heavier state management solution. Each store handles one concern with clear boundaries. Combined with FIFO eviction policies for unbounded data (like event logs), this keeps memory usage predictable and state management testable.

### Evidence

- v005 Theme 03: Three Zustand stores created — `activityStore` (50-entry FIFO eviction), `libraryStore` (filters, pagination), `projectStore` (selection, modal state)
- Each store was independently testable and easy to reason about
- 85 Vitest tests passed with clean separation of concerns
- No store-related bugs or complexity issues across four GUI features
- Theme retrospective noted Zustand kept implementation "lightweight and testable without the boilerplate of heavier alternatives"

### Application

- React applications with multiple feature domains needing shared state
- Prefer one store per feature/domain (library, projects, activity) over a single global store
- Add eviction policies (FIFO, LRU) for stores that accumulate data over time (event logs, notifications)
- Keep stores focused: if a store grows beyond ~5 state fields, consider splitting

---

## LRN-025: Feature Handoff Documents Enable Zero-Rework Sequencing

**Tags:** process, sequencing, handoff, documentation, patterns
**Source:** v005 version retrospective (cross-theme learning)

### Context

When features within a theme depend on each other, the implementing agent needs to understand integration points, API contracts, and patterns established by previous features.

### Learning

Feature-to-feature handoff documents that explicitly communicate integration points, hook APIs, layout patterns, and component conventions enable subsequent features to plug in without rework. When combined with correct theme sequencing (infrastructure before consumers), this produces zero-rework feature chains.

### Evidence

- v005 Theme 01: Infrastructure -> WebSocket -> Settings ordering meant each feature built on the previous without rework
- v005 Theme 03: Application shell handoff document communicated WebSocket hook API, layout patterns, and page component conventions to downstream features (dashboard, library, projects)
- v005 Theme 04: Playwright setup handoff document communicated test infrastructure to the E2E test suite feature
- v005 version retrospective: "All 11 features passed quality gates on first iteration" — zero rework across the entire version
- All 58/58 acceptance criteria passed with 0 failures

### Application

- Any multi-feature theme where features have dependencies
- Handoff documents should include: API contracts, integration points, component patterns, naming conventions, and test infrastructure setup
- Combine with correct feature sequencing (foundation -> consumers) for maximum effect
- This reinforces LRN-019 (Build Infrastructure First) at the feature level within themes
