# stoat-and-ferret - Development Plan

> Bridge between strategic roadmap and auto-dev execution.
>
> Strategic Roadmap: `docs/design/01-roadmap.md`
> Last Updated: 2026-02-25

## Current Focus

**Recently Completed:** v012 (API Surface & Bindings Cleanup)
**Upcoming:** No versions currently planned — all 12 versions delivered.

## Roadmap → Version Mapping

| Version | Roadmap Reference | Focus | Status |
|---------|-------------------|-------|--------|
| v012 | Phase 2 cleanup | API Surface & Bindings Cleanup: wire/remove FFmpeg bridge, audit PyO3 bindings, transition GUI, API spec polish | ✅ complete |
| v011 | Phase 1–2 gaps | GUI Usability & Developer Experience: browse button, clip CRUD, .env.example, IMPACT_ASSESSMENT.md | ✅ complete |
| v010 | RCA + Phase 1 gaps | Async Pipeline & Job Controls: fix blocking ffprobe, CI async gate, progress reporting, job cancellation | ✅ complete |
| v009 | Wiring audit + Phase 2 gaps | Observability & GUI Runtime: FFmpeg metrics, audit logging, file logging, SPA routing, pagination, WebSocket broadcasts | ✅ complete |
| v008 | Wiring audit | Startup Integrity & CI Stability: database startup, logging startup, orphaned settings, flaky E2E fix | ✅ complete |
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

## Completed Versions

### v012 - API Surface & Bindings Cleanup (2026-02-25)
- **Themes:** rust-bindings-audit, workshop-and-docs-polish
- **Features:** 5 completed across 2 themes
- **Backlog Resolved:** BL-061, BL-066, BL-067, BL-068, BL-079
- **Key Changes:** Removed dead `execute_command()` bridge function, trimmed 5 unused v001 PyO3 bindings (find_gaps, merge_ranges, total_coverage, validate_crf, validate_speed), trimmed 6 unused v006 PyO3 bindings (Expr/PyExpr, validated_to_string, compose_chain, compose_branch, compose_merge), wired transition effects into Effect Workshop GUI with TransitionPanel and clip-pair selection, fixed 6 misleading API spec progress examples to use normalized 0.0–1.0 floats
- **Deferred:** None

### v011 - GUI Usability & Developer Experience (2026-02-24)
- **Themes:** scan-and-clip-ux, developer-onboarding
- **Features:** 5 completed across 2 themes
- **Backlog Resolved:** BL-019, BL-070, BL-071, BL-075, BL-076
- **Key Changes:** Directory browser dialog for scan path selection with filesystem API endpoint, clip CRUD controls (Add/Edit/Delete) with ClipFormModal and clipStore, .env.example with all 11 Settings fields documented, Git Bash /dev/null guidance in AGENTS.md Windows section, IMPACT_ASSESSMENT.md with 4 design-time checks for recurring issue patterns
- **Deferred:** None

### v010 - Async Pipeline & Job Controls (2026-02-23)
- **Themes:** async-pipeline-fix, job-controls
- **Features:** 5 completed across 2 themes
- **Backlog Resolved:** BL-072, BL-073, BL-074, BL-077, BL-078
- **Key Changes:** Async ffprobe with `asyncio.create_subprocess_exec()` replacing blocking `subprocess.run()`, Ruff ASYNC rules (ASYNC210/221/230) as CI gate for blocking-in-async detection, event-loop responsiveness integration test (<2s jitter), job progress reporting with per-file progress via WebSocket, cooperative job cancellation with `cancel_event` and per-file checkpoints saving partial results
- **Deferred:** None

### v009 - Observability & GUI Runtime (2026-02-22)
- **Themes:** observability-pipeline, gui-runtime-fixes
- **Features:** 6 completed across 2 themes
- **Backlog Resolved:** BL-057, BL-059, BL-060, BL-063, BL-064, BL-065
- **Key Changes:** ObservableFFmpegExecutor wired into DI chain with Prometheus metrics, AuditLogger wired with separate sync sqlite3 connection and WAL mode, RotatingFileHandler integrated into configure_logging() with 10MB rotation, SPA routing fallback replacing StaticFiles mount, AsyncProjectRepository.count() fixing pagination totals, WebSocket broadcast wiring for project and scan events
- **Deferred:** None

### v008 - Startup Integrity & CI Stability (2026-02-22)
- **Themes:** application-startup-wiring, ci-stability
- **Features:** 4 completed across 2 themes
- **Backlog Resolved:** BL-055, BL-056, BL-058, BL-062
- **Key Changes:** Database schema creation wired into lifespan startup (`create_tables_async()`), structured logging wired with `settings.log_level` and idempotent handler guard, orphaned settings (`settings.debug`, `settings.ws_heartbeat_interval`) wired to consumers so all 9 Settings fields are now consumed by production code, flaky E2E `toBeHidden()` assertion fixed with explicit timeout
- **Deferred:** None

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

**Version-agnostic items:** BL-069 (C4 documentation update, deferred).
**Excluded from versions:** BL-069 (C4 documentation update, deferred), PR-003 (auto-dev-mcp product request, not stoat-and-ferret code).

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
| 2026-02-25 | v012 complete: API Surface & Bindings Cleanup delivered (2 themes, 5 features, 5 backlog items completed). Moved v012 from Planned to Completed. Updated Current Focus to reflect no upcoming versions. |
| 2026-02-24 | v011 complete: GUI Usability & Developer Experience delivered (2 themes, 5 features, 5 backlog items completed). Moved v011 from Planned to Completed. Updated Current Focus to v012. |
| 2026-02-24 | v010 complete: Async Pipeline & Job Controls delivered (2 themes, 5 features, 5 backlog items completed). Moved v010 from Planned to Completed. Updated Current Focus to v011. |
| 2026-02-23 | Replanned v010–v012 from 14 open backlog items. v010: Async Pipeline & Job Controls (BL-072, BL-073, BL-074, BL-077, BL-078). v011: GUI Usability & Developer Experience (BL-019, BL-070, BL-071, BL-075, BL-076). v012: API Surface & Bindings Cleanup (BL-061, BL-066, BL-067, BL-068, BL-079). Excluded BL-069 (C4 docs) and PR-003 (auto-dev product request). Updated BL-076 notes: project-specific code, not auto-dev artifact. |
| 2026-02-22 | v009 complete: Observability & GUI Runtime delivered (2 themes, 6 features, 6 backlog items completed). Moved v009 from Planned to Completed. Updated Current Focus to v010. |
| 2026-02-22 | v008 complete: Startup Integrity & CI Stability delivered (2 themes, 4 features, 4 backlog items completed). Moved v008 from Planned to Completed. Updated Current Focus to v009. |
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
