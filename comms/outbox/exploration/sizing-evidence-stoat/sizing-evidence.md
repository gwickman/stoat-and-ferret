# Backlog Item Sizing Evidence: v008–v012

## Complete Evidence Table

| Version | BL-ID | Title | Estimated Size | Actual Size | Task Type | Evidence Source | Reasoning |
|---------|-------|-------|---------------|-------------|-----------|----------------|-----------|
| v008 | BL-055 | Fix flaky E2E test (toBeHidden timeout) | L | S | Bug fix | retrospective/v008/003-backlog/README.md; retrospective/v008/007-proposals/README.md | Single-line timeout parameter change. Over-estimated because planning assumed investigation complexity, but root cause was already known from v007. |
| v008 | BL-056 | Wire structured logging at application startup | XL | L–XL | Wiring | execution/v008/01-application-startup-wiring/002-logging-startup/completion-report.md | Multi-file changes across logging, app, uvicorn config, and 15 new tests. XL was reasonable given broad surface area. Slight over-estimate. |
| v008 | BL-058 | Wire database schema creation into startup | L | M–L | Wiring | execution/v008/01-application-startup-wiring/001-database-startup/completion-report.md | New async function, lifespan integration, test helper consolidation. L was slightly generous; work was well-scoped. |
| v008 | BL-062 | Wire orphaned settings to their consumers | L | S–M | Wiring | retrospective/v008/003-backlog/README.md; retrospective/v008/007-proposals/README.md | Two simple setting-to-consumer wirings (debug flag, heartbeat interval) plus 6 tests. Significantly over-estimated at L. |
| v009 | BL-059 | Wire ObservableFFmpegExecutor into DI | M | M | Wiring | execution/v009/01-observability-pipeline/001-ffmpeg-observability/completion-report.md | Straightforward DI wiring of pre-existing component. All 5 AC passed. Correctly sized. |
| v009 | BL-060 | Wire AuditLogger into repository DI | M | M+ | Wiring | execution/v009/01-observability-pipeline/002-audit-logger/completion-report.md; LRN-047 | Unanticipated architectural decision (separate sync sqlite3 connection + WAL mode) added complexity beyond simple DI wiring. Slightly conservative estimate. |
| v009 | BL-057 | Add file-based logging with rotation | M | M | Wiring | execution/v009/01-observability-pipeline/003-file-logging/completion-report.md | Extended configure_logging() with RotatingFileHandler following idempotent pattern (LRN-040). 9 new tests. Correctly sized. |
| v009 | BL-063 | Add SPA routing fallback for GUI sub-paths | S–M | S–M | Wiring/Bug fix | execution/v009/02-gui-runtime-fixes/001-spa-routing/completion-report.md | Standard SPA catch-all pattern replacing StaticFiles mount. 9 new tests. Correctly sized. |
| v009 | BL-064 | Fix projects endpoint pagination total count | S | S+ | Wiring | execution/v009/02-gui-runtime-fixes/002-pagination-fix/completion-report.md | Backend was simple (copy count() pattern), but frontend pagination UI (state, hooks, component) was more substantial than "minimal adjustment" suggested. Slightly conservative. |
| v009 | BL-065 | Wire WebSocket broadcast calls into API operations | M–L | M–L | Wiring | execution/v009/02-gui-runtime-fixes/003-websocket-broadcasts/completion-report.md; LRN-049 | Cross-cutting changes to multiple endpoints. Guard pattern (`if ws_manager:`) simplified implementation. Correctly sized. |
| v010 | BL-072 | Fix blocking subprocess.run() in ffprobe | L | L | Bug fix / Async migration | execution/v010/01-async-pipeline-fix/001-fix-blocking-ffprobe/completion-report.md | Async conversion of ffprobe_video(), caller updates, 5 test file migrations, Python 3.10 compatibility (asyncio.TimeoutError). Correctly sized. |
| v010 | BL-073 | Add progress reporting to job queue and scan handler | L | L | Feature / Wiring | execution/v010/02-job-controls/001-progress-reporting/completion-report.md | Cross-layer changes: queue data model, scan handler, REST API schema, frontend. 11 new tests. Correctly sized. |
| v010 | BL-074 | Implement job cancellation support | M | L | Feature / Cross-layer wiring | retrospective/v010/003-backlog/README.md; retrospective/v010/007-proposals/proposals.md | Changes across 5 layers (queue model, protocol, scan handler, REST API, frontend React). Initial estimate treated cancellation as single pattern without accounting for full-stack coordination. Under-estimated. |
| v010 | BL-077 | Add CI quality gate for blocking calls in async context | L | S–M | Quality gate / Config | retrospective/v010/003-backlog/README.md; retrospective/v010/007-proposals/proposals.md | Estimated as L assuming custom grep-based CI script. Actual: 1-line ruff config change (`"ASYNC"` added to lint select) plus small health.py conversion. Significantly over-estimated. |
| v010 | BL-078 | Add event-loop responsiveness integration test | L | L | Testing / Integration | execution/v010/01-async-pipeline-fix/003-event-loop-responsiveness-test/completion-report.md | Complex timing-sensitive integration test with real AsyncioJobQueue, simulated-slow subprocess, CI variability considerations. Correctly sized. |
| v011 | BL-019 | Add Windows bash /dev/null guidance to AGENTS.md | L | L | Documentation-only | retrospective/v011/003-backlog/backlog-report.md | L sizing was for original full scope (AGENTS.md + .gitignore). The .gitignore half was already completed before v011, but sizing reflects original estimate. |
| v011 | BL-070 | Add Browse button for scan directory path selection | M | M | Full-stack (backend + frontend) | execution/v011/01-scan-and-clip-ux/001-browse-directory/completion-report.md | New backend /api/v1/filesystem/directories endpoint with validate_scan_path() security, DirectoryBrowser.tsx component. 8/8 AC. Correctly sized. |
| v011 | BL-071 | Add .env.example file for environment configuration | M | M | Documentation-only | execution/v011/02-developer-onboarding/001-env-example/completion-report.md | Template documenting all 11 Settings fields plus cross-reference updates in 3 docs. 7/7 AC. Correctly sized. |
| v011 | BL-075 | Add clip management controls (Add/Edit/Delete) to GUI | L | L | Full-stack (frontend wiring) | execution/v011/01-scan-and-clip-ux/002-clip-crud-controls/completion-report.md | Zustand store, ClipFormModal, API client functions, ProjectDetails UI. Wired to existing backend endpoints. 9/9 AC. Correctly sized. |
| v011 | BL-076 | Create IMPACT_ASSESSMENT.md with design checks | L | L | Documentation-only | execution/v011/02-developer-onboarding/003-impact-assessment/completion-report.md | 4 structured design-time checks with trigger conditions, verification steps, required actions. 6/6 AC. Correctly sized. |
| v012 | BL-079 | Fix API spec examples for progress values | L | S–M | Documentation-only | retrospective/v012/003-backlog/README.md; retrospective/v012/007-proposals/proposals.md | 5 text fixes across 2 files, no code changes, no test changes. Significantly over-estimated at L. |
| v012 | BL-061 | Wire or remove execute_command() Rust-Python bridge | L | M | Code removal (deletion) | retrospective/v012/003-backlog/README.md; retrospective/v012/007-proposals/proposals.md | Straightforward dead code deletion: 1 file removed, 13 tests removed, exports cleaned up. Decision (wire vs remove) was the complexity; execution was mechanical. Over-estimated. |
| v012 | BL-066 | Add transition support to Effect Workshop GUI | L | L | GUI feature (wiring-gap closure) | retrospective/v012/003-backlog/README.md | New Zustand store, TransitionPanel component, ClipSelector pair-mode extension. 4 files created, 5 modified. Correctly sized. |
| v012 | BL-067 | Audit and trim unused PyO3 bindings from v001 | L | L | Refactoring (API surface reduction) | execution/v012/01-rust-bindings-cleanup/002-v001-bindings-trim/completion-report.md | 5 PyO3 wrappers removed across Rust/Python/stubs, 19 parity tests removed, docs updated. Correctly sized. |
| v012 | BL-068 | Audit and trim unused PyO3 bindings from v006 | L | L | Refactoring (API surface reduction) | execution/v012/01-rust-bindings-cleanup/003-v006-bindings-trim/completion-report.md | 6 PyO3 wrappers removed (including PyExpr class), 31 parity tests removed, stub regeneration. Correctly sized. |

## Detailed Findings by Version

### v008 — Startup Integrity & CI Stability

**Pattern:** Items tended toward over-estimation. The wiring audit inflated estimates due to uncertainty about hidden complexity that turned out to be minimal.

- **BL-055 (L → S):** Most extreme mis-size. Planning assumed investigation complexity for a Playwright flake, but root cause was already known from v007 — a single `{ timeout: 10_000 }` parameter addition.
- **BL-062 (L → S–M):** Two simple setting wirings (`debug` flag, `ws_heartbeat_interval`). L assumed difficulty in tracing consumers that proved straightforward.
- **BL-056 (XL → L–XL):** Slight over-estimate. Risks identified (test interference from logging output) materialized as simple implementation choices rather than complex problems.
- **BL-058 (L → M–L):** Slight over-estimate. Design decision (create_tables vs Alembic) resolved quickly as straightforward approach.

**Source:** retrospective/v008/007-proposals/README.md — "v008 items tended toward over-estimation (BL-055 L→actual S, BL-062 L→actual S-M). Consider for future sizing."

### v009 — DI Wiring & GUI Fixes

**Pattern:** Sizing was highly accurate. All 6 items were within one half-step of their estimates.

- **BL-060 (M → M+):** Only slight miss — unanticipated WAL mode architectural decision added complexity beyond simple DI pattern.
- **BL-064 (S → S+):** Frontend pagination UI was more work than "minimal adjustment" but still absorbed by existing patterns.
- All other items (BL-059, BL-057, BL-063, BL-065) were accurately sized.

**Source:** retrospective/v009 — 31/31 acceptance criteria passed, 0 quality gate failures, 100% first-iteration success.

### v010 — Async Pipeline Fix & Job Controls

**Pattern:** Mixed calibration with one significant over-estimate and one under-estimate.

- **BL-077 (L → S–M):** Over-estimated. Assumed custom grep-based CI script; actual solution was a 1-line ruff config change adding `"ASYNC"` to the lint rule list. Discovery of ruff's built-in ASYNC rules made the solution dramatically simpler.
- **BL-074 (M → ~L):** Under-estimated. "Cooperative cancellation is well-understood" was true for the algorithm but insufficient for sizing 5-layer full-stack implementation (queue model → protocol → scan handler → REST API → frontend React).
- **BL-072, BL-073, BL-078 (all L → L):** All correctly sized given cross-layer changes and test migration work.

**Source:** retrospective/v010/003-backlog/README.md and retrospective/v010/007-proposals/proposals.md

### v011 — Scan/Clip UX & Developer Onboarding

**Pattern:** Exceptional sizing accuracy. All 5 items completed at estimated size with zero rework.

- All items matched estimates exactly: BL-019 (L→L), BL-070 (M→M), BL-071 (M→M), BL-075 (L→L), BL-076 (L→L).
- **BL-019:** L sizing was for original full scope (AGENTS.md + .gitignore). The .gitignore portion was pre-completed, but the original estimate was valid.
- 34/34 acceptance criteria passed, 0 iteration cycles required.

**Source:** retrospective/v011/003-backlog/backlog-report.md — v011 skewed toward L-sized items (60% L vs 40% M).

### v012 — Rust Bindings Cleanup & GUI Wiring

**Pattern:** Two items over-estimated (both involved documentation-only or deletion work), three correctly sized.

- **BL-079 (L → S–M):** 5 text fixes across 2 documentation files with zero code changes. L was inappropriate for documentation-only corrections.
- **BL-061 (L → M):** Dead code deletion was mechanical once the wire-vs-remove decision was made. The decision was the complexity, not the execution.
- **BL-066, BL-067, BL-068 (all L → L):** Correctly sized for multi-faceted work (GUI features, Rust PyO3 removal with stub regeneration).

**Source:** retrospective/v012/007-proposals/proposals.md — recommends S for documentation-only fixes, M for straightforward deletions.
