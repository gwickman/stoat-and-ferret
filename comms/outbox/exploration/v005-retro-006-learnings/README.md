# v005 Retrospective Task 006: Learning Extraction

Extracted 6 new learnings from v005 completion reports (11 features), theme retrospectives (4 themes), and the version retrospective. 3 existing learnings were reinforced by new evidence from v005.

## New Learnings

| ID | Title | Tags | Source |
|----|-------|------|--------|
| LRN-020 | Conditional Static Mount Pattern for Optional Frontend Serving | fastapi, patterns, testing, frontend, static-files | v005/01-frontend-foundation, v005/04-e2e-testing |
| LRN-021 | Separate Vitest Config for Vite 7+ Projects | frontend, vite, vitest, typescript, configuration | v005/01-frontend-foundation/001-frontend-scaffolding |
| LRN-022 | Automated Accessibility Testing Catches Real Violations | accessibility, testing, e2e, playwright, wcag | v005/04-e2e-testing/002-e2e-test-suite |
| LRN-023 | Client-Side Navigation for SPA E2E Tests Without Server-Side Routing | e2e, testing, spa, routing, playwright | v005/04-e2e-testing/002-e2e-test-suite |
| LRN-024 | Focused Zustand Stores Over Monolithic State Management | frontend, react, state-management, zustand, patterns | v005/03-gui-components (cross-theme pattern) |
| LRN-025 | Feature Handoff Documents Enable Zero-Rework Sequencing | process, sequencing, handoff, documentation, patterns | v005 version retrospective (cross-theme learning) |

## Reinforced Learnings

| ID | Title | New Evidence from v005 |
|----|-------|----------------------|
| LRN-005 | Constructor DI over dependency_overrides for FastAPI Testing | `create_app()` kwargs pattern scaled to 4 new components (ws_manager, gui_static_path, thumbnail_service, gui auto-load) across all 11 features without breaking existing tests |
| LRN-008 | Record-Replay with Strict Mode for External Dependency Testing | Thumbnail pipeline (Theme 02) reused the FFmpeg executor record-replay pattern for testing thumbnail generation without real process execution |
| LRN-019 | Build Infrastructure First in Sequential Version Planning | v005 theme ordering (infrastructure -> backend -> GUI -> E2E) validated by zero-rework feature chains; all 58/58 acceptance criteria passed first-pass |

## Filtered Out

**14 items filtered** across these categories:

| Category | Count | Reason |
|----------|-------|--------|
| Version-specific tech debt | 6 | SPA fallback routing, dual WebSocket, client-side sorting, search total semantics, C4 docs, heartbeat wiring — all project-specific debt, not transferable patterns |
| Implementation details | 4 | Placeholder image path choice, synchronous FFmpeg in thumbnails, scan polling interval, Rust health inference — decisions specific to this codebase |
| Restatements of existing learnings | 2 | DI pattern consistency and feature sequencing observations already captured in LRN-005 and LRN-019 |
| Tool-specific configuration | 2 | Tailwind CSS v4 config, Vite dev proxy maintenance — too narrow to be general learnings |
