# stoat-and-ferret - Development Plan

> Bridge between strategic roadmap and auto-dev execution.
>
> Strategic Roadmap: `docs/design/01-roadmap.md`
> Last Updated: 2026-02-19

## Current Focus

**Recently Completed:** v007 (effect workshop GUI: audio mixing, transitions, effect registry, catalog UI, parameter forms, live preview)
**Upcoming:** v008 (Startup Integrity & CI Stability — wiring audit fixes)

## Roadmap → Version Mapping

| Version | Roadmap Reference | Focus | Status |
|---------|-------------------|-------|--------|
| v007 | Phase 2, M2.4–2.6, M2.8–2.9 | Effect Workshop GUI: audio mixing, transitions, effect registry, catalog UI, parameter forms, live preview | ✅ complete |
| v006 | Phase 2, M2.1–2.3 | Effects engine foundation: filter expression engine, graph validation, text overlay, speed control | ✅ complete |
| v005 | Phase 1, M1.10–1.12 | GUI shell + library browser + project manager | ✅ complete |
| v004 | Phase 1, M1.8–1.9 | Testing infrastructure + quality verification | ✅ complete |
| v003 | Phase 1, M1.6–1.7 | API layer + Clip model | ✅ complete |
| v002 | Phase 1, M1.4–1.5 | Database + FFmpeg integration | ✅ complete |
| v001 | Phase 1, M1.1–1.3 | Foundation + Rust core basics | ✅ complete |

## Investigation Dependencies

Track explorations that must complete before version design.

| ID | Question | Informs | Status |
|----|----------|---------|--------|
| EXP-001 | PyO3/maturin hybrid build workflow — dev experience, CI setup, stub generation | v001 | complete |
| EXP-002 | Recording fake pattern — concrete implementation for RecordingFFmpegExecutor | v001, v004 | complete |
| EXP-003 | FastAPI static file serving — GUI deployment from API server | v005 | complete |
| BL-028 | Frontend framework selection (extends EXP-003) | v005 | complete |
| BL-043 | Clip effect model design (how effects attach to clips) | v006 | complete |
| BL-047 | Effect registry schema and builder protocol design | v007 | complete |
| BL-051 | Preview thumbnail pipeline (frame extraction + effect application) | v007 | complete |

## Planned Versions

### v008 — Startup Integrity & CI Stability

**Goal:** Fix P0 blockers and critical startup wiring gaps discovered by the wiring audit. After v008, a fresh install starts cleanly with working logging, database, and settings.

**Theme 1: application-startup-wiring**
- 001-database-startup: Wire `create_tables()` into lifespan startup [BL-058, P0]
- 002-logging-startup: Call `configure_logging()` at startup, wire `settings.log_level` [BL-056, P1]
- 003-orphaned-settings: Wire `settings.debug` to FastAPI and `settings.ws_heartbeat_interval` to ws.py [BL-062, P2]

**Theme 2: ci-stability**
- 001-flaky-e2e-fix: Fix `project-creation.spec.ts:31` toBeHidden timeout flake [BL-055, P0]

**Backlog items:** BL-055, BL-056, BL-058, BL-062 (4 items)
**Dependencies:** None. All items are independent startup/CI fixes.
**Risk:** BL-055 (flaky E2E) may require Playwright timing investigation.

---

### v009 — Observability & GUI Runtime

**Goal:** Complete the observability pipeline (FFmpeg metrics, audit logging, file-based logs) and fix GUI runtime gaps (SPA routing, pagination, WebSocket broadcasts).

**Theme 1: observability-pipeline**
- 001-ffmpeg-observability: Wire `ObservableFFmpegExecutor` into DI chain [BL-059, P1]
- 002-audit-logging: Wire `AuditLogger` into repository DI [BL-060, P2]
- 003-file-logging: Add `RotatingFileHandler` to `configure_logging()` [BL-057, P2]

**Theme 2: gui-runtime-fixes**
- 001-spa-routing: Add SPA fallback to serve index.html for GUI sub-paths [BL-063, P1]
- 002-pagination-fix: Add `count()` to `AsyncProjectRepository`, fix total in GET /projects [BL-064, P2]
- 003-websocket-broadcasts: Wire `ConnectionManager.broadcast()` calls into API operations [BL-065, P2]

**Backlog items:** BL-057, BL-059, BL-060, BL-063, BL-064, BL-065 (6 items)
**Dependencies:** BL-057 depends on BL-056 (v008). All others independent.
**Risk:** BL-065 (WebSocket broadcasts) touches multiple API endpoints.

---

### v010 — API Surface Cleanup & Remaining

**Goal:** Audit and trim dead PyO3 bindings, resolve the Rust-Python FFmpeg bridge, add transition GUI support, and close remaining housekeeping.

**Theme 1: rust-python-api-cleanup**
- 001-ffmpeg-bridge: Wire or remove `execute_command()` Rust-Python bridge [BL-061, P2]
- 002-v001-bindings-audit: Audit and trim unused v001 PyO3 bindings (TimeRange ops, sanitization) [BL-067, P3]
- 003-v006-bindings-audit: Audit and trim unused v006 PyO3 bindings (Expr, graph validation, composition) [BL-068, P3]

**Theme 2: gui-and-housekeeping**
- 001-transition-gui: Add transition support to Effect Workshop GUI [BL-066, P3]
- 002-agents-md-guidance: Add Windows bash /dev/null redirect guidance to AGENTS.md [BL-019, P3]

**Backlog items:** BL-019, BL-061, BL-066, BL-067, BL-068 (5 items)
**Dependencies:** BL-066 depends on transition API from v007. All others independent.
**Risk:** BL-061 requires a design decision (wire vs remove). BL-067/BL-068 are audit-then-act.

## Completed Versions

### v007 - Effect Workshop GUI (2026-02-19)
- **Themes:** rust-filter-builders, effect-registry-api, effect-workshop-gui, quality-validation
- **Features:** 11 completed across 4 themes
- **Backlog Resolved:** BL-044, BL-045, BL-046, BL-047, BL-048, BL-049, BL-050, BL-051, BL-052
- **Key Changes:** Rust audio mixing builders (AmixBuilder, VolumeBuilder, AfadeBuilder, DuckingPattern) and transition builders (FadeBuilder, XfadeBuilder, AcrossfadeBuilder), effect registry refactor to builder-protocol dispatch with JSON schema validation, transition API endpoint with clip adjacency validation, complete GUI effect workshop (catalog with search/filter, schema-driven parameter forms, live filter preview with syntax highlighting, effect builder workflow with CRUD lifecycle), Playwright E2E tests with WCAG AA accessibility compliance
- **Deferred:** None

### v006 - Effects Engine Foundation (2026-02-19)
- **Themes:** filter-engine, filter-builders, effects-api
- **Features:** 8 completed across 3 themes
- **Backlog Resolved:** BL-037, BL-038, BL-039, BL-040, BL-041, BL-042, BL-043
- **Key Changes:** Greenfield Rust filter expression engine with type-safe Expr builder API, filter graph validation with cycle detection (Kahn's algorithm), filter composition system with LabelGenerator, DrawtextBuilder with position presets and alpha fade, SpeedControl with setpts/atempo and automatic chaining for extreme speeds, EffectRegistry with effect discovery API, clip effect application endpoint with effects_json storage
- **Deferred:** None

### v005 - GUI Shell, Library Browser & Project Manager (2026-02-09)
- **Themes:** frontend-foundation, backend-services, gui-components, e2e-testing
- **Features:** 11 completed across 4 themes
- **Backlog Resolved:** BL-003, BL-028, BL-029, BL-030, BL-031, BL-032, BL-033, BL-034, BL-035, BL-036
- **Key Changes:** React/TypeScript/Vite frontend in gui/, WebSocket endpoint with ConnectionManager, ThumbnailService with FFmpeg, application shell with tab navigation, dashboard with health cards, library browser with search/sort/scan, project manager with CRUD, Zustand stores, Playwright E2E tests with WCAG AA accessibility, pagination total count fix
- **Deferred:** SPA fallback routing for deep links, WebSocket connection consolidation

### v004 - Testing Infrastructure & Quality Verification (2026-02-09)
- **Themes:** test-foundation, blackbox-contract, async-scan, security-performance, devex-coverage
- **Features:** 15 completed across 5 themes
- **Backlog Resolved:** BL-020, BL-021, BL-022, BL-023, BL-024, BL-025, BL-026, BL-027, BL-009, BL-010, BL-012, BL-014, BL-016
- **Key Changes:** InMemory test doubles with DI via create_app(), fixture factory with builder pattern, 30 black box REST API tests, 21 FFmpeg contract tests, async scan via asyncio.Queue job queue, security audit of Rust sanitization, Rust vs Python performance benchmarks, property test guidance, Rust code coverage with cargo-llvm-cov, Docker testing environment
- **Deferred:** Rust coverage threshold at 75% (target 90%), scan endpoint blackbox tests (requires real FFmpeg)

### v003 - API Layer + Clip Model (2026-01-28)
- **Themes:** process-improvements, api-foundation, library-api, clip-model
- **Features:** 15 completed across 4 themes
- **Backlog Resolved:** BL-013, BL-015, BL-017
- **Key Changes:** FastAPI REST API with request correlation and metrics middleware, async repository layer, video library endpoints (CRUD + search + scan), clip and project data models with Rust validation, CI improvements
- **Deferred:** WebSocket support (→ v005), async scan job queue (→ v004)

### v002 - Database & FFmpeg Integration (2026-01-27)
- **Themes:** 4 themes, 13 features
- **Key Changes:** Python bindings completion, SQLite with repository pattern and FTS5 search, FFmpeg executor with dependency injection and observability, recording fake pattern for FFmpeg
- **Deferred:** Unify InMemory vs FTS5 search behavior (→ v004)

### v001 - Foundation (2026-01-26)
- **Themes:** 3 themes, 10 features
- **Key Changes:** Python/Rust hybrid tooling (maturin, PyO3), timeline math module (pure functions), FFmpeg command builder with filter chain/graph, input sanitization, type stubs
- **Deferred:** Contract tests with real FFmpeg (→ v004), drop-frame timecode (→ TBD)

## Deferred Items

| Item | From | To | Rationale |
|------|------|----|-----------|
| Contract tests with real FFmpeg | M1.3 | v004 | Part of testing infrastructure version |
| Drop-frame timecode support | M1.2 | TBD | Complex; start with non-drop-frame only |
| Phase 3: Composition Engine | v008 (original) | post-v010 | Wiring audit fixes take priority over new features |

## Backlog Integration

Work categories:

| Tag | Purpose |
|-----|---------|
| `investigation` | Needs exploration before implementation |
| `deferred` | Known work explicitly pushed to later |
| `discovered` | Found during execution, not originally planned |
| `blocked` | Waiting on external dependency |

**Version-agnostic items:** None — all open items assigned to v008-v010.

Query: `list_backlog_items(project="stoat-and-ferret", status="open")`

## Cancelled Items

| ID | Title | Rationale |
|----|-------|-----------|
| BL-011 | Consolidate Python/Rust build backends | Obsoleted by 7 versions of successful dual-backend usage |
| BL-053 | Add PR vs BL routing guidance to AGENTS.md | Routing guidance embedded in core auto-dev scripts instead |
| BL-054 | Add WebFetch safety rules to AGENTS.md | Superseded by auto-dev-mcp BL-536 at the global level |

## Change Log

| Date | Change |
|------|--------|
| 2026-02-21 | Planned v008-v010 covering all 15 open backlog items from wiring audit. Cancelled BL-011, BL-053, BL-054. Closed PR-001, PR-002 after investigation. Deferred Phase 3: Composition Engine to post-v010. |
| 2026-02-19 | v007 complete: Effect Workshop GUI delivered (4 themes, 11 features, 9 backlog items completed). Moved v007 from Planned to Completed. Updated Current Focus to v008. Marked BL-047 and BL-051 investigations as complete. |
| 2026-02-19 | v006 complete: Effects Engine Foundation delivered (3 themes, 8 features, 7 backlog items completed). Moved v006 from Planned to Completed. Updated Current Focus to v007. Marked BL-043 investigation as complete. |
| 2026-02-09 | v005 complete: GUI Shell, Library Browser & Project Manager delivered (4 themes, 11 features, 10 backlog items completed). Moved v005 from Planned to Completed. Updated Current Focus to v006. Marked EXP-003 and BL-028 investigations as complete. |
| 2026-02-09 | v004 complete: Testing Infrastructure & Quality Verification delivered (5 themes, 15 features, 13 backlog items completed). Moved v004 from Planned to Completed. Updated Current Focus to v005. |
| 2026-02-08 | Rewrote plan.md to match auto-dev-mcp format. Added Planned Versions sections for v004–v007 with full backlog item listings and dependency chains. |
| 2026-02-08 | Gap analysis completed (backlog-gap-analysis exploration). Created 33 new backlog items (BL-020–052) for v004–v007. Retagged 5 existing items to v004. Updated plan with backlog coverage and scoping decisions for v006/v007. |
| 2026-01-28 | v003 complete: API layer + Clip model delivered (4 themes, 15 features, BL-013/015/017 completed) |
| 2026-01-27 | v002 complete: Database & FFmpeg integration delivered (4 themes, 13 features) |
| 2026-01-26 | v001 complete: Foundation version delivered |
| 2025-01-25 | v001 design complete: 3 themes, 10 features designed |
| 2025-01-25 | EXP-001, EXP-002 complete: Investigations for v001 prerequisites |
| 2025-01-25 | Initial plan created: Project bootstrap, mapping Phase 1-2 milestones to versions |
