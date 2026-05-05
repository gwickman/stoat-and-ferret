# Changelog

All notable changes to stoat-and-ferret will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v058] - 2026-05-05

### CI and Test Quality

Repaired malformed render_plan fixture data and removed the STOAT_RENDER_WORKER_ENABLED=false CI workaround, restoring render worker coverage in E2E and accessibility CI jobs. Fixed Python 3.10 asyncio task-cancellation stall in synthetic monitoring test.

**Themes:** 1 (ci-and-test-quality)  
**Features:** 2/2 complete (001-ci-timeout-hardening, 002-render-fixture-repair)  
**Quality:** 10/10 acceptance criteria met, 0 regressions

**Key Outcomes:**
- Added 30-minute CI job timeout and per-test 120s pytest-timeout to bound any CI hang (PR #384)
- Deleted 29 malformed render_jobs rows from data/stoat.db fixture (Windows-local paths inaccessible in CI); render worker starts clean in all CI jobs (PR #385)
- Removed STOAT_RENDER_WORKER_ENABLED=false workaround from e2e and a11y CI jobs (PR #385)
- Fixed Python 3.10 asyncio cancel stall in test_monitoring_task_continuous_execution using asyncio.wait with timeout (PR #385)

**PRs Merged:**
- #384: CI timeout hardening (job timeout, per-test timeout, asyncio.wait_for fix)
- #385: Render fixture repair (delete malformed rows, remove CI workaround, Python 3.10 stall fix)

## [v057] - 2026-05-04

### Documentation Quality Catchup

Updated C4 code-level documentation to reflect GUI store/hook/component and backend alembic/identity/WebSocket changes from v038–v057. Added FRAMEWORK_CONTEXT.md sections for accessibility testing strategy, batch progress transport, and render_worker.* event namespace.

**Themes:** 2 (c4-documentation-refresh, framework-context-additions)  
**Features:** 5/5 complete (001-gui-c4-refresh, 002-backend-c4-refresh, 001-axe-core-scanning-strategy, 002-batch-transport-docs, 003-render-worker-namespace)  
**Quality:** 52/52 acceptance criteria met, 0 regressions (2540 tests passed, 3 skipped, 0 failed)

**Key Outcomes:**
- GUI C4 code documentation updated: stores (14 → 17), hooks (13 → 20), workspace components added (PR #379)
- Backend C4 code documentation updated: alembic (7 → 9 migrations), identity module (ClientIdentityStore, InMemoryClientIdentityStore), WebSocket interface changes with client_identity_store param and client_id kwargs (PR #380)
- Accessibility testing strategy documented in FRAMEWORK_CONTEXT.md: axe-core scanning approach, decision tree for when to apply (PR #381)
- Batch progress HTTP polling transport documented in FRAMEWORK_CONTEXT.md: rationale for polling over SSE, transport selection guidance (PR #382)
- render_worker.* structured logging namespace added to FRAMEWORK_CONTEXT.md namespace taxonomy (PR #383)

**PRs Merged:**
- #379: GUI C4 code documentation refresh (stores, hooks, workspace components)
- #380: Backend C4 code documentation refresh (alembic, identity, WebSocket)
- #381: Accessibility testing strategy (axe-core scanning, decision tree)
- #382: Batch progress transport documentation
- #383: render_worker.* event namespace documentation

## [v056] - 2026-05-03

### WebSocket Client Identity

Implemented client identity management for WebSocket connections, enabling persistent token-based client tracking across reconnections.

**Theme:** websocket-client-identity  
**Features:** 3/3 complete (001-framework-documentation, 002-token-mechanism, 003-connection-integration)  
**Quality:** 49/49 acceptance criteria met, 58 new tests added, 0 regressions

**Key Outcomes:**
- Token mechanism: 32-char hex via `secrets.token_hex(16)`, validated via `is_valid_client_id()` (PR #376)
- Storage: `ClientIdentityStore` Protocol with `InMemoryClientIdentityStore` implementation, in-memory dict keyed by client token (PR #376)
- Integration: `ConnectionManager` wired with identity store; client token passed via WebSocket query parameter on connect, cleared on disconnect (PR #377)
- Backwards compatibility: Last-Event-ID replay path unchanged when no client token provided

**PRs Merged:**
- #376: Token mechanism and ClientIdentityStore implementation
- #377: ConnectionManager integration with WebSocket endpoint

## [v055] - 2026-05-03

### Render Worker Loop

Implemented a background render worker loop that dequeues render jobs and executes them via the existing `RenderService.run_job()` pipeline. The worker runs as a background task during app lifespan and is designed to be non-blocking and resilient.

**Theme:** render-worker-loop  
**Features:** 3/3 complete (001-command-builder, 002-worker-loop-core, 003-lifecycle-and-tests)  
**Quality:** 53 new tests added, 0 regressions

**Key Outcomes:**
- Command builder (`RenderCommandBuilder`) constructs validated FFmpeg command sequences from `RenderJob` (PR #373)
- Worker loop core (`RenderWorkerLoop`) dequeues jobs and dispatches to `RenderService.run_job()` with structured error handling (PR #374)
- Lifecycle integration wires `RenderWorkerLoop` into app lifespan at Phase 10 (after job queue worker), with graceful shutdown and full test coverage (PR #375)

**Recovery Context:**
v055 experienced a server restart mid-execution. Recovery involved manual PR merge (#375) and MCP state patching. Feature 003 completion report was not generated during recovery and is documented as a documentation lag.

**PRs Merged:**
- #373: Command builder for render jobs (`RenderCommandBuilder` with FFmpeg argument construction)
- #374: Render worker loop core (background dequeue loop with retry and error handling)
- #375: Lifecycle integration and tests (lifespan wiring, shutdown, 91-test coverage)

## [v054] - 2026-05-02

### GUI Performance & Compatibility Baselines

**Overview:** Established bundle size and cross-browser compatibility baselines for the web GUI. Measured Lighthouse performance and documented browser-specific testing gaps. All measurements are non-invasive; no source code was modified.

**Theme:** gui-perf-and-compat  
**Features:** 3/3 complete (001-changelog-v049, 002-bundle-analysis, 003-browser-compat-testing)  
**Quality:** 23/23 acceptance criteria met, 0 regressions

**Key Outcomes:**
- Bundle composition baseline: main 125.70 kB gzip, lazy PreviewPlayer chunk 162.20 kB gzip
- Lighthouse performance score: 79 (below 90 target due to CLS 0.44; documented in bundle-analysis.md)
- Time to Interactive (TTI): 2,130 ms (meets <3s target)
- Cross-browser test matrix: Chromium 95/96 pass, Firefox 91/96 pass, WebKit 88/96 pass
- Browser-specific issues documented with workarounds (FF-001, WK-001, WK-002)

**Backlog Items Resolved:** BL-328, BL-298, BL-299

**PRs Merged:**
- #370: Bundle size analysis baseline and optimization recommendations
- #371: Cross-browser compatibility testing and known-issue documentation

**Technical Insights:**
- Measurement-only features eliminate production risk by establishing baselines without code changes
- CI guards (`!process.env.CI`) prove effective for local-only multi-browser testing
- CLS is the primary constraint on Lighthouse score; fix is a Priority 1 recommendation for v055

## [v053] - 2026-05-02

### Comprehensive E2E Test Suite (Playwright)

Comprehensive Playwright E2E test suite for Phase 6 GUI workflows — workspace layout persistence, settings management, batch panel interaction, keyboard navigation, and accessibility validation.

**Features:**
- Workspace Layout & Settings Journeys (#366): E2E tests for workspace panel layout persistence, settings panel read/write, preset management across sessions
- Batch Panel WebSocket & Seed Endpoint (#367): E2E tests for batch job list rendering, seed endpoint integration, WebSocket progress event validation
- Keyboard Navigation & Accessibility (#368): E2E tests for keyboard-driven navigation, focus management, ARIA landmark traversal, screen reader announcements

**Quality Metrics:**
- 30/35 acceptance criteria met (5 deferred: browser-stack cross-browser, CI parallelism tuning)
- 0 regressions detected
- 58 new Playwright E2E tests added
- Full TypeScript type safety across all test files
- 3 features across 1 theme (01-gui-e2e-playwright-suite)

## [v052] - 2026-05-02

### GUI Accessibility

Achieved WCAG 2.1 Level AA conformance across all GUI components and workflows.

**Features:**
- Accessibility Core Infrastructure (#362): AccessibilityWrapper component, useAnnounce hook, dual aria-live regions
- ARIA Landmarks and Labels (#363): Semantic HTML markup, skip-to-content link, navigation landmarks
- Dynamic Status Announcements (#364): Live region integration for render progress, scan results, error states
- CI/E2E Validation Gates (#365): Automated axe-core audit, keyboard navigation testing, UAT journeys

**Quality Metrics:**
- 30/30 acceptance criteria met
- 0 regressions detected
- 2419 tests passed (3 skipped, 0 failures)
- 100% quality gate pass rate

## [v051] - 2026-05-01

Deployment Infrastructure & Developer Guardrails. Delivers three backlog items addressing deployment/DevX concerns: FFmpeg production decision with health endpoint semantics, CI Docker image build with size/quality gates, and Windows shell anti-pattern prevention via pre-commit hook. 55/55 ACs met, 0 regressions, 3 PRs (#359, #360, #361).

### Deployment Safety

- **FFmpeg Production Status Decision** — Resolved FFmpeg-in-production decision; classified FFmpeg as non-critical with graceful degradation; `/health/ready` returns HTTP 200 with `status: "degraded"` when FFmpeg unavailable rather than HTTP 503, enabling flexible deployment architectures (CPU-only containers, remote FFmpeg, staged rollouts) (BL-309, #359)

### CI Hardening

- **Docker Build CI Gate** — Added GitHub Actions CI workflow job to build production Docker image with multi-stage Dockerfile, enforcing size/quality gates to prevent bloat and configuration drift; validates production deployment readiness on every PR (BL-310, #360)

### Developer Experience

- **Windows Shell Anti-Pattern Prevention** — Implemented pre-commit hook using `grep -I -F` (fixed-string, binary-safe) to catch Windows `/dev/null` vs `nul` anti-patterns in shell scripts (.sh, .bash, .yml files); CI backup verification step in workflows prevents hook bypass; documented guidance in AGENTS.md (BL-311, #361)

## [v050] - 2026-05-01

Security Maintenance and Quality Improvements. Delivers three backlog items: a datetime deprecation fix eliminating DeprecationWarnings across the API layer, encoder cache test coverage expansion to ≥85%, and a UAT known-failure registry that distinguishes known failures from regressions. 18/18 ACs met, 0 regressions.

### Maintenance

- **Datetime Deprecation Fix** — Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)` across 7 locations in the API layer to eliminate DeprecationWarnings and ensure Python 3.10+ compatibility (BL-322, #355)

### Test Coverage

- **Encoder Cache Coverage Expansion** — Added `tests/unit/render/test_encoder_cache.py` with 18 parameterized tests covering `AsyncSQLiteEncoderCacheRepository` and `InMemoryEncoderCacheRepository`, raising coverage from 71% to ≥85% (BL-324, #356)

### UAT Infrastructure

- **UAT Known-Failure Registry** — Implemented `data/baseline-uat-failures.json` registry and updated `scripts/uat_runner.py` to emit `KNOWN_FAILURE`/`UNEXPECTED_PASS` annotations, enabling distinction between known failures and regressions (BL-325, #357)

## [v049] - 2026-04-30

Workspace Shell Polish. Delivers two themes: workspace accessibility cleanup (a11y focus order fix with E2E coverage) and workspace panel routing (per-panel URL routing with PRESETS routes field and PANEL_DEFAULTS consolidation). 18/18 ACs met, 0 regressions.

### Workspace Accessibility

- **A11y Focus Order Fix** — Removed conditional-mount guard that broke focus order on initial workspace load; added workspace a11y E2E tests covering focus-order and keyboard navigation regressions (BL-305, #350)

### Workspace Panel Routing

- **Per-Panel Routing** — PRESETS routes field wires per-panel URL routing with URL params; `003-routing-design-validation` design document captures the routing design and validation approach (BL-306, #352, #353)
- **PANEL_DEFAULTS Consolidation** — Extracted `PANEL_DEFAULTS` const to eliminate duplicate panel size definitions across workspace layout components (BL-307, #351)

## [v048] - 2026-04-30

### Added
- Explicit `python-dotenv>=1.2.2` lower-bound constraint in `pyproject.toml` to clear CVE-2026-28684 and enforce minimum version with required security fixes (#347).
- Security audit cadence formalization: `docs/security/audit-cadence.md` documents quarterly review triggers, Python/FFmpeg/PyO3 major upgrade audits, and new unsafe Rust pattern scans. Integrated into `AGENTS.md` and `docs/design/FRAMEWORK_CONTEXT.md` as authoritative process artifact (#348).

### Changed
- `docs/security/review-phase6.md` §9: Replaced inline audit cadence prose with reference pointer to new `audit-cadence.md` for single-source-of-truth maintenance.

## [v047] - 2026-04-30

- docs(v047): C4 architecture refresh and load-test baseline documentation
- PR #344: Update C4 architecture diagrams for v037–v046 changes
- PR #345: Execute and record load-test baseline

## [v045] - 2026-04-29

Phase 6: Configuration Documentation Convergence. Documents all STOAT_* environment variables with operator-facing setup references and security-focused guidance, and enforces zero-drift by reducing the security audit baseline to an empty frozenset.

### Configuration Reference

- **STOAT_* Environment Variable Coverage** — 41 STOAT_* variables documented in `docs/setup/04_configuration.md` with name, type, default, valid range, and plain-English description; Configuration Documentation Rule added to AGENTS.md enforcing documentation for all future variables (BL-316, #338)

### Operator Security Configuration

- **Operator Security Configuration Guide** — `docs/manual/configuration-reference.md` with 13 security-sensitive STOAT_* variables covering production hazards, security implications, and recommended values; `KNOWN_UNDOCUMENTED_SETTINGS_VARS` allowlist in `tests/security/test_audit.py` reduced to empty `frozenset()` to enforce zero-drift audit baseline (BL-317, #339)

## [v046] - 2026-04-29

- docs(v046): Document startup initialization sequence, Alembic migration conventions, and structured event naming
- PR #341: Startup Initialization Sequence documentation
- PR #342: Alembic Migration Conventions documentation
- PR #343: Structured Event Naming Conventions documentation

## [v044] - 2026-04-28

Phase 6: GUI Unified Workspace. Delivers two themes: a workspace layout foundation (dockable resizable panels with persistent sizing and layout presets with keyboard shortcuts) and workspace feature panels (settings panel with theme selector and shortcut editor, keyboard shortcut reference overlay, and batch panel GUI with job monitoring and cancellation).

### Workspace Layout

- **Dockable Resizable Panel Layout** — Resizable panel infrastructure with `workspaceStore` (Zustand) and `WorkspaceLayout` component; persistent panel sizing via localStorage; conditional Shell mounting for backward-compatible routed pages (BL-291, #332)
- **Workspace Layout Presets** — PRESETS constants (Edit/Review/Render); `setPreset` action with Ctrl+1/2/3 keyboard bindings; per-preset size preservation via `sizesByPreset`; `useRef` guard prevents bidirectional preset/resize loops (BL-292, #333)

### Workspace Feature Panels

- **Settings Panel** — Theme selector and shortcut editor integrated into workspace sidebar; settings persist to localStorage (BL-293, #334)
- **Keyboard Shortcut Reference Overlay** — Dynamic shortcut enumeration from registry; focus trap with Escape-to-dismiss (BL-294, #335)
- **Batch Panel GUI** — Batch job submission form, live progress polling, job cancellation, and real-time status updates; async DELETE handler fix for correct post-cancel state (BL-295, #336)

## [v043] - 2026-04-27

Phase 6 Quality & Security Gate. Delivers two themes: a security-audit theme (Python API and Rust core security audits) and a performance-observability theme (performance benchmarks with Phase 6 metrics, load testing harness with noop render mode, and Grafana SLI dashboard).

### Security

- **Python API Security Audit** — Enumerated 8 potential vulnerability classes with grep-based AST probes; zero P0/P1 findings; SQL injection defense confirmed via parameterized queries and AST-walk detection; path traversal enforced via `STOAT_ALLOWED_SCAN_ROOTS`; introduced `tests/security/` test category with 3 probe scripts (BL-286, #327)
- **Rust Core Security Audit** — Full audit of all Rust sanitization and filter-building code; zero `unsafe` blocks confirmed across entire codebase; DrawtextBuilder injection surface validated with 20 additional property-based tests; single shared security report approach adopted (BL-287, #328)

### Performance & Observability

- **Performance Benchmarks and Phase 6 Metrics** — `tests/benchmarks/` suite with pytest-benchmark against live FastAPI endpoints; 7 new Prometheus metrics registered in `metrics.py` (`stoat_seed_duration_seconds`, `stoat_system_state_duration_seconds`, `stoat_ws_buffer_size`, `stoat_ws_connected_clients`, `stoat_active_jobs_count`, `stoat_feature_flag_state`, `stoat_migration_duration_seconds`); baseline results documented in `docs/design/11-performance-benchmarks.md` (BL-288, #329)
- **Load Test Harness** — Locust-based load test harness in `tests/load/`; `STOAT_RENDER_MODE=noop` setting short-circuits FFmpeg for synthetic throughput testing; `websocket-client` (gevent-compatible) for WebSocket load simulation; hardware-variable results deferred to operator runs (BL-289, #330)
- **Grafana SLI Dashboard** — `docs/observability/grafana-sli-dashboard.json` with 7 SLI panels (request rate, error rate, latency p50/p95/p99, WebSocket clients, active jobs); test-time source parsing validates metric truth set against live registrations (BL-290, #331)

## [v042] - 2026-04-26

Agent Operator Documentation and Residual Closure. Delivers targeted documentation for AI agent operators (operator guide, prompt recipes, WebSocket event vocabulary) and closes residual v039/v041 documentation gaps (CHANGELOG verification, AGENTS.md path corrections, manual TOC completeness).

### Documentation

- **Agent Operator Guide** — `docs/manual/operator-guide.md` compact reference for AI agents orchestrating stoat-and-ferret over HTTP/WebSocket; covers API orientation, canonical sequences, state machines, testing mode, and MCP abstraction criteria; all endpoint paths live-verified (BL-283, #323)
- **Prompt Recipes and Example Scripts** — `docs/manual/prompt-recipes.md` with 6 copy-paste recipes; `scripts/wait-for-render.py` and `scripts/dump-ws-events.py` executable utilities for common agent workflows (BL-284, #324)
- **WebSocket Event Vocabulary** — `docs/manual/ws-event-vocabulary.md` documenting all 24 event types with payloads, state transitions, and live-captured evidence; 9 frames captured for validation (BL-285, #325)
- **AGENTS.md Path Fix** — Updated 8 stale `stubs/` directory references to `src/` following the v041 stub consolidation (BL-303, #321)
- **Manual TOC Update** — Added 6 missing TOC entries to `docs/manual/00_README.md` for v041 and pre-v041 manual files (BL-304, #322)
- **CHANGELOG Verification** — Confirmed v039 (BL-301) and v041 (BL-302) CHANGELOG sections are present and accurate; no edits required

## [v041] - 2026-04-24

Documentation and Operational Excellence. Validates the OpenAPI specification against Phase 6 endpoints, enriches Rust core with rustdoc examples, delivers canonical API usage workflows, and ships an operational runbook with decision-tree troubleshooting.

### Documentation

- **OpenAPI Specification Validation** — Validated OpenAPI spec against all Phase 6 endpoints; documented endpoint contracts and response schemas for the full API surface (BL-279, #316)
- **Rust Core rustdoc Examples** — Added rustdoc examples to all public Rust types and functions; consolidated stubs to `src/` for co-location with implementations (BL-280, #317)
- **API Usage Examples** — `docs/manual/api-usage-examples.md` with 5 canonical workflows demonstrating end-to-end API interactions for scan, project creation, clip management, effects, and render (BL-281, #318)
- **Operational Runbook** — `docs/manual/operational-runbook.md` with decision-tree troubleshooting guides for common failure modes, health check interpretation, and recovery procedures (BL-282, #319)

## [v040] - 2026-04-23

### Features
- Event ID and timestamp on all WebSocket events
- WebSocket replay buffer with reconnection support
- System state snapshot endpoint for external agent orientation
- Test fixture seeding endpoints for repeatable agent workflows
- Long-poll job completion endpoint with configurable timeouts
- OpenAPI state machine documentation for job lifecycle

### Improvements
- All quality gates pass (2352 tests, 100% coverage)
- Comprehensive WebSocket observability and testability improvements

## [v039] - 2026-04-23

AI Integration & Schema Discovery. Delivers a Rust ParameterSchema translator for AI-friendly effect discovery, a schema introspection REST endpoint for dynamic resource discovery by external agents, and a comprehensive AI integration patterns guide documenting how external systems can interact with the API.

### Added

- **ParameterSchema Rust Translator** — `ParameterSchema` Rust type with PyO3 bindings translating stoat-and-ferret effect parameter schemas into a normalized, AI-consumable format; enables external agents to programmatically enumerate effect capabilities and constraints (BL-270, #306)
- **Schema Introspection Endpoint** — `GET /api/v1/schema/{resource}` REST endpoint returning JSON Schema descriptions for API resources; supports AI agent discovery of available data shapes without prior knowledge of the API (BL-271, #307)
- **AI Integration Patterns Guide** — `docs/manual/ai-integration-patterns.md` documenting recommended patterns for external agents interacting with the stoat-and-ferret API, including effect discovery, parameter validation, and session management (BL-272, #308)

## [v037] - 2026-04-17

WebSocket Enrichment, Container Deployment, and Developer Quality. Enriches render WebSocket events with frame/fps/encoder metadata, implements live frame streaming to Theater Mode, ships a production-ready multi-stage Dockerfile with health checks and Docker Compose dev stack, and improves developer quality with jest-dom Vitest setup and updated test harness documentation.

### Added

- **Format-Encoder Validation on Submission** — `POST /render` enforces format-encoder compatibility at submission time, returning 422 for invalid combinations (BL-258, #293)
- **Enriched Render WebSocket Progress Events** — `render.progress` events now include `frame`, `fps`, and `encoder` metadata fields for richer client-side display (BL-254, #294)
- **Live Frame Streaming to Theater Mode** — Frame streaming endpoint delivers 540p frames to Theater Mode during active renders (BL-255, #295)
- **Production Dockerfile** — Multi-stage Dockerfile for containerized production deployment with minimal runtime image and non-root user (BL-262, #296)
- **Container Health Checks** — Startup gate and liveness/readiness health check endpoints for container orchestration (BL-265, #297)
- **Docker Compose Dev Stack** — `docker-compose.yml` orchestrating API, frontend, and dependencies for local development (BL-264, #298)
- **Deployment Smoke Script** — `scripts/deploy_smoke.sh` and `GET /api/v1/version` endpoint for smoke-testing deployed containers (BL-263, #299)
- **Jest-dom Vitest Setup** — Jest-dom matchers configured in Vitest setup for expressive DOM assertions in GUI tests (BL-259, #300)

### Changed

- **RenderJobCard C4 Diagram** — Updated C4 component diagram to reflect v035 `cancelLoading`/`retryLoading`/`deleteLoading` flags (BL-257)

### Documentation

- **Three-Tier Test Harness Guide** — Test harness documentation updated with contract test tier description and guidance (BL-256, #301)

## v034 — Documentation Catch-Up: Phase 4 and Phase 5 (2026-04-11)

### Documentation

- Verified Phase 4 design documents (01-roadmap.md, 02-architecture.md, 05-api-specification.md, 07-quality-architecture.md, 08-gui-architecture.md) — all Phase 4 content confirmed present (BL-208, #PR-001)
- Verified Phase 4 IMPACT_ASSESSMENT.md grep patterns — PreviewSession, ProxyFile, ThumbnailStrip, Waveform, TheaterMode pattern groups confirmed present (BL-209)
- Updated design documents with Phase 5 render subsystem: milestones [x] in roadmap, render state machine in architecture, 11 render endpoints in API spec, render test patterns in quality architecture, RenderPage/RenderJobCard/StartRenderModal in GUI architecture (BL-237, #279)
- Added Phase 5 grep patterns to IMPACT_ASSESSMENT.md: RenderJob/RenderStatus, OutputFormat/QualityPreset, RenderQueue/RenderExecutor, RenderService/PreflightError, EncoderCacheEntry/AsyncEncoderCacheRepository pattern groups (BL-238, #280)
- Extended sample project seed script with render step (POST /api/v1/render); added smoke test asserting status==queued; documented export workflow in sample-project.md (BL-239, #281)
- C4 architecture delta: documented encoder_cache.py in c4-code-stoat-ferret-render.md; updated useRenderEvents to Shell in c4-code-gui-hooks.md; updated BottomHUD in c4-code-gui-components-theater.md; added Start Render button to c4-code-gui-pages.md TimelinePage; added v034 delta row to C4 README (BL-241, #282)
## v035 — Frontend Reliability and Render GUI Polish (2026-04-12)

### Changed

- **useWebSocket Burst Safety** — Replaced direct `setState` in `onmessage` with a ref-queue pattern (`queueRef` + `tick` counter) to survive React 18 automatic batching; hook now exposes `messages: MessageEvent[]` array alongside `lastMessage` for burst-complete delivery (BL-248, #283)
- **WebSocket Consumers** — `useRenderEvents`, `useJobProgress`, and `ActivityLog` updated to iterate `messages[]` array with `for (const msg of messages)` pattern; `DashboardPage` passes `messages` to `ActivityLog` (BL-248, #284)

### Added

- **Format-Encoder Compatibility Validation** — `render_preview` endpoint returns HTTP 422 with `INCOMPATIBLE_FORMAT_ENCODER` for invalid format-encoder combinations (e.g., `libvpx + mp4`); `av1` codec added to `mkv` format; `StartRenderModal` surfaces 422 error message in preview area (BL-252, #286)
- **RenderJobCard Loading States** — Per-button `cancelLoading`, `retryLoading`, `deleteLoading` flags with `try/finally` reset; buttons disabled during in-flight API calls to prevent duplicate requests (BL-253, #287)

### Fixed

- **TimelinePage Test Hygiene** — Corrected stale test counts in C4 documentation (TimelinePage: 7→13, total: 318→324); confirmed all 13 TimelinePage tests pass following the cbe2fa5 fix (BL-247, #285)

## v036 — Service Quality & Persistence (2026-04-14)

### Fixed

- **UAT CI Timeout Fix** — Fixed UAT CI job hanging by implementing pre-build artifact caching and `--no-build` flag in uat_runner.py; timeout budget documented in workflow (BL-261, #288)

### Added

- **DB Persistence for Services** — Wired SQLiteThumbnailStripRepository and SQLiteWaveformRepository into ThumbnailService and WaveformService via DI; services now survive restarts (BL-251, #289)
- **ProxyService Public API** — Added `list_by_video(video_id: str)` public method to ProxyService; removed scan.py encapsulation breach (BL-249, #290)
- **Proxy Auto-Generation Optimization** — Refactored `_auto_queue_proxies()` to accept video IDs from scan result instead of re-walking directory; eliminated redundant filesystem traversal (BL-250, #291)
- **Frontend Testing Guidance** — Added async `act()` documentation to FRAMEWORK_CONTEXT.md with multi-phase hook test patterns (BL-260)

## v033 — Render Testing, UAT Journeys, and Metrics (2026-04-11)

### Added
- Render API smoke tests for cancel, retry, and encoder-refresh endpoints (BL-232, #269)
- Render contract tests for output format validation (mp4/webm/mov/mkv via ffprobe), encoder detection against real FFmpeg output, and multi-segment concat duration integrity using lavfi virtual inputs (BL-233, #270, #271, #272)
- UAT journeys J501–J504 for render export, render queue management, render settings, and render failure recovery (BL-234, #274, #275, #276, #277)
- J401–J404 headless CI hardening with graceful no-project state handling; CI UAT timeout increased from 5 to 10 minutes (BL-205, #273)
- `render_jobs_total` Prometheus counter `submitted` label on job creation for in-flight job tracking via Prometheus arithmetic (BL-245, #278)

## v032 — Render Surface Integration (2026-04-08)

### Added
- Lifted `useRenderEvents` WebSocket hook to Shell component for application-wide render event listening (BL-235)
- Render progress indicators (percentage, ETA, speed ratio) in Theater Mode BottomHUD (BL-235)
- Start Render button on TimelinePage header with StartRenderModal integration (BL-236)

### Changed
- BottomHUD reads render state from shared `useRenderStore` instead of maintaining its own WebSocket connection

## [v031] - 2026-04-07

Phase 5 GUI Render Interactive Components. Enriches render progress WebSocket events with ETA and speed data, builds reusable render job card components, and ships the StartRenderModal for configuring and launching render jobs.

### Added

- **Render Progress Enrichment** — `eta_seconds` and `speed_ratio` fields in `render.progress` WebSocket events, computed via Rust `estimate_eta()` and Python arithmetic; propagated through renderStore `setProgress` action (BL-243, #260, #261)
- **StatusBadge Component** — Reusable color-coded dot + label component for render job status display across all 5 states (BL-229, #262)
- **RenderJobCard Component** — Full job card with progress bar, ETA, speed ratio, StatusBadge, and cancel/retry/delete action buttons; integrated into RenderPage Active/Pending/Completed sections (BL-229, #263)
- **Render Preview Endpoint** — `POST /api/v1/render/preview` returning FFmpeg command strings for format/quality/encoder combinations with Rust `build_render_command` (BL-230, #264)
- **StartRenderModal** — Modal with cascading format/quality/encoder selectors, disk space bar, debounced FFmpeg command preview, inline validation, and render submission (BL-230, #265)

## [v030] - 2026-04-05

GUI Render Page Shell + Public API Hygiene. Builds the user-facing render control center with routing, state management, page layout, and UAT coverage. Fixes LayoutError public API export and migrates compose.py imports.

### Added

- **Render Page Route & Navigation** — `/render` route in App.tsx, Render tab in Navigation with endpoint health check (BL-231, #255)
- **Render Store & WebSocket Hook** — Zustand renderStore with job list, queue status, encoder/format state; useRenderEvents hook dispatching 8 WebSocket render event types with reconnection re-fetch (BL-231, #256)
- **Render Page Layout** — RenderPage with Active/Pending/Completed job sections, queue status bar, disabled Start Render button, data-testid attributes (BL-228, #257)
- **Render UAT Journey 501** — Playwright test validating render page navigation, layout elements, and data-testid selectors (BL-231, BL-228, #258)

### Fixed

- **LayoutError Public API Export** — re-exported LayoutError through stoat_ferret_core public API, migrated compose.py from internal `_core` import (BL-246, #259)

## [v028] - 2026-04-01

Phase 5 Foundation: Rust Render Core + Render Job Infrastructure. Builds compute-intensive Rust render functions (plan, encoder, progress, command) with PyO3 bindings and proptest coverage, plus Python job infrastructure (model, queue, executor, checkpoints, service) for end-to-end render job lifecycle management.

### Added

- **Render Plan Builder** — Rust `build_render_plan()` with segment decomposition at clip boundaries, frame counting, cost estimation, and `validate_render_settings()` pre-flight checks (BL-210, #234)
- **Hardware Encoder Detection** — Rust `detect_hardware_encoders()` parsing FFmpeg output, `select_encoder()` with nvenc/qsv/vaapi/amf/mf/software fallback chain, `build_encoding_args()` for draft/standard/high presets (BL-211, #235)
- **Progress Tracking** — Rust `parse_ffmpeg_progress()` for FFmpeg `-progress pipe:1` output, `calculate_progress()` bounded 0.0-1.0, `estimate_eta()`, and `aggregate_segment_progress()` with duration weighting (BL-212, #236)
- **Render Command Builder** — Rust `build_render_command()`, `build_concat_command()` for ffconcat demuxer, `check_output_conflict()`, and `estimate_output_size()` with bitrate lookup table (BL-213, #237)
- **Render Job Model** — `RenderJob` dataclass, `RenderStatus` state machine, `OutputFormat`/`QualityPreset` enums, SQLite + InMemory repository implementations with 86 parity tests (BL-214, #238)
- **Render Queue** — persistent queue with `max_concurrent`/`max_depth` limits, FIFO ordering, startup recovery, and `QueueFullError` (BL-215, #239)
- **Render Executor** — FFmpeg subprocess management with Rust PyO3 progress parsing, stdin-based graceful cancellation, timeout enforcement, and temp file cleanup (BL-216, #240)
- **Render Checkpoints** — per-segment checkpoint persistence to SQLite, recovery scanning on startup, resume-from-checkpoint, stale cleanup with CASCADE FK (BL-217, #241)
- **Render Service** — lifecycle orchestration with pre-flight checks via Rust, WebSocket event broadcasting, retry logic, and DI wiring in `create_app()` (BL-218, #242)
- **Phase 4 FFmpeg Contract Tests** — HLS segment generation, Rust-simplified filter chain, thumbnail strip JPEG, and waveform PNG validation with real FFmpeg output (BL-204, #229)

## [v027] - 2026-03-30

Theater Mode, Integration Wiring, Phase 4 Test Coverage, and Documentation Updates. Adds fullscreen Theater Mode with HUD overlay and keyboard shortcuts. Wires transition IDs, timeline-player sync, audio waveforms, and proxy status indicators. Adds Phase 4 smoke tests, contract tests, and UAT journeys. Regenerates C4 architecture documentation and updates design documents.

### Added

- **Theater Mode Fullscreen Wrapper** — fullscreen container with auto-hiding HUD, CSS transition animations, and escape-to-exit (BL-199, #221)
- **Theater HUD Overlay** — AI action indicator and render progress display overlaid on fullscreen preview (BL-200, #222)
- **Theater Mode Keyboard Shortcuts** — hotkeys for theater toggle, HUD visibility, and playback controls in fullscreen (BL-201, #223)
- **Bidirectional Timeline-Player Sync** — playhead position synchronized between timeline and preview player in both directions (BL-202, #225)
- **Audio Waveform Visualization** — waveform overlay on timeline clips using generated waveform data (BL-206, #226)
- **Proxy Status Indicators** — ProxyStatusBadge component on VideoCard showing proxy generation state via WebSocket updates (BL-207, #227)
- **Phase 4 Preview Smoke Tests** — smoke tests covering preview session endpoints (BL-203, #228)
- **Phase 4 UAT Journeys** — J401-J404 UAT journeys for theater mode, timeline sync, waveform, and proxy status (BL-205, #230)
- **C4 Architecture Regeneration** — full C4 documentation regenerated covering v011-v027 (BL-147, #231)
- **Design Document Updates** — Phase 4 content added to architecture and GUI design documents (BL-208, #232)
- **Impact Assessment Patterns** — Phase 4 grep patterns added to IMPACT_ASSESSMENT (BL-209, #233)

### Fixed

- **Transition ID Assignment** — effects-router transitions now receive IDs for DELETE compatibility (BL-148, #224)

## [v026] - 2026-03-27

Phase 4 Observability + GUI Preview Player. Instruments preview and proxy subsystems with Prometheus metrics, structured logging, health checks, and graceful degradation. Wires deferred BL-179 WebSocket progress callbacks. Builds the complete GUI preview player with HLS.js, controls, seek tooltip, quality selector, and Preview page.

### Added

- **WebSocket Progress Wiring** — throttled progress callbacks in PreviewManager broadcasting `JOB_PROGRESS` events via WebSocket for real-time generation updates (BL-179, #208)
- **Preview & Proxy Prometheus Metrics** — 14 metric definitions (counters, gauges, histograms) across preview, proxy, and cache subsystems (BL-190, #209)
- **Preview Structured Logging** — structured log events across session lifecycle, proxy, cache, thumbnail, and waveform generation with `{subsystem}_{action}` naming convention (BL-191, #210)
- **Preview & Proxy Health Checks** — preview and proxy checks on `/health/ready` with degraded semantics for optional subsystems; HealthCards GUI updates (BL-192, #211)
- **Graceful Degradation & Shutdown** — 503 `FFMPEG_UNAVAILABLE` on preview endpoints when FFmpeg missing; `cancel_all()` with process termination and temp cleanup on shutdown (BL-193, #212)
- **Smoke Test Updates** — health check assertions for preview/proxy fields; new preview session creation smoke test (BL-192, #213)
- **Smoke Test Harness Guide** — documentation of new smoke test entries in smoke-test-key-files.md (BL-192, #214)
- **Preview Page & Store** — PreviewPage shell, Zustand previewStore, navigation tab, route, and regenerated OpenAPI types for v025 preview API (BL-198, #215)
- **HLS.js Preview Player** — PreviewPlayer with HLS.js integration, Safari native fallback, fatal error recovery, buffer tracking, and `React.lazy` dynamic import (BL-194, #216)
- **Player Controls** — play/pause, progress bar click-to-seek, skip ±5s, volume slider with mute, time display (mm:ss/hh:mm:ss), and full keyboard accessibility (BL-195, #217)
- **Seek Tooltip** — sprite-sheet frame calculation, smooth mouse-following via absolute positioning, and time-only fallback when thumbnails unavailable (BL-196, #218)
- **Quality Selector & Status Display** — quality dropdown (low/medium/high) with cancel-and-restart flow, and PreviewStatus with seek latency, buffer bar, and generation progress at ~4 Hz (BL-197, #219)
- **Preview Playback UAT Journey** — J205 with 5 steps, registered in `uat_runner.py` dependency graph, and updated uat-testing.md (BL-198, #220)

## [v025] - 2026-03-26

Phase 4 Preview Engine: Sessions + Visual Aids. Core preview playback infrastructure with HLS session management, thumbnail strip generation, and waveform visualization. Backend-only — no GUI components.

### Added

- **Preview Session Data Model** — `PreviewSession` dataclass, `PreviewStatus` enum, `preview_sessions` SQLite table, `AsyncPreviewSessionRepository` protocol with SQLite + InMemory implementations and 31 parity tests (BL-178, #198)
- **HLS Segment Generator** — FFmpeg HLS VOD segment generation with Rust filter simplification, progress callbacks, and cooperative cancellation (BL-179, #199)
- **Preview Session Manager** — `PreviewManager` with start/seek/stop lifecycle, concurrency limits, per-session locks, 4 new WebSocket `EventType` variants, background expiry cleanup (BL-180, #200)
- **Preview API Endpoints** — 7 REST endpoints for session management and HLS content serving with Pydantic schemas and DI wiring (BL-181, #201)
- **Preview Cache** — LRU eviction and TTL expiry for preview segment storage with configurable size limits (1 GB default) and background cleanup task (BL-182, #202)
- **Preview Cache API** — GET/DELETE endpoints for cache status inspection and clearing with `clear_all()` bulk operation (BL-183, #203)
- **Thumbnail Strip Service** — sprite sheet generation using FFmpeg fps+scale+tile filters with NxM grid tiling, JPEG dimension limit handling, configurable interval via `STOAT_THUMBNAIL_STRIP_INTERVAL`, `extract_frame_args()` shared primitive (BL-186, #204)
- **Thumbnail Strip API** — POST 202/GET metadata/GET strip.jpg endpoints with Pydantic schemas and DI wiring (BL-187, #205)
- **Waveform Generation Service** — dual output: PNG via showwavespic filter and JSON via astats/ffprobe, mono/stereo support, Windows path escaping, configurable via `STOAT_WAVEFORM_DIR` (BL-188, #206)
- **Waveform API** — POST 202/GET metadata/GET waveform.png/GET waveform.json endpoints with dual format support (BL-189, #207)

## [v024] - 2026-03-25

Phase 4 Foundation: Deferred Quality + Proxy Infrastructure + Rust Preview Core. Close the OpenAPI enum freshness gap from v023, build proxy data and service infrastructure for Phase 4 preview playback, and implement Rust-based filter simplification and cost estimation for real-time preview.

### Added

- **OpenAPI Enum CI Freshness Check** — boot-and-compare CI step ensures committed `gui/openapi.json` stays in sync with live FastAPI spec; key-sorted JSON normalization for deterministic diffs (BL-139, #190)
- **Proxy Data Model** — `ProxyFile` dataclass, `ProxyStatus`/`ProxyQuality` enums, `proxy_files` SQLite table with UNIQUE constraint, `AsyncProxyRepository` protocol with SQLite + InMemory implementations and 51 parity tests (BL-174, #191)
- **Proxy Generation Service** — async FFmpeg proxy transcoding with progress parsing, quality auto-selection, storage quota with LRU eviction, stale detection, per-job-type timeout (1800s) in job queue (BL-175, #192)
- **Proxy Management API** — REST endpoints for proxy generate (POST), status (GET), delete (DELETE), and batch operations (POST); Pydantic response models with DI wiring (BL-176, #193)
- **Proxy Scan Integration** — optional auto-queue of proxy generation on scan discovery, stale proxy detection during scan, `STOAT_PROXY_AUTO_GENERATE` setting (BL-177, #194)
- **Proxy Smoke Tests** — 4 smoke tests covering all proxy endpoints with direct DB seeding; harness documentation updated (Impact #9, #11, #195)
- **Preview Filter Simplification (Rust)** — `preview/` module with `PreviewQuality` enum, `simplify_filter_graph`/`simplify_filter_chain`/`is_expensive_filter` functions, getter methods on FilterGraph/FilterChain/Filter, 19 Rust tests + 9 Python binding tests via PyO3 (BL-184, #196)
- **Filter Cost Estimation and Scale Injection (Rust)** — `estimate_filter_cost` with sigmoid normalization, `select_preview_quality` with threshold mapping, `inject_preview_scale` for scale filter insertion, property-based test coverage via proptest (BL-185, #197)

### Changed

- **`TransitionResponse` renamed to `EffectTransitionResponse`** — resolves non-deterministic OpenAPI schema naming from duplicate class names across modules
- **Committed `gui/openapi.json` regenerated** — spec was stale; updated to match current FastAPI output

## [v023] - 2026-03-25

Persistence, Frontend Modernisation, and CI UAT. Persistent batch state and version retention improve resilience; WebSocket push replaces HTTP polling; OpenAPI codegen pipeline eliminates hand-authored TypeScript types; effect preview thumbnails added; UAT harness wired into CI to block merges on browser-level regressions.

### Added

- **Batch SQLite Persistence** — batch render state persisted to SQLite via Protocol + SQLite + InMemory repository pattern; jobs survive server restarts (BL-143, #183)
- **Version Retention Policy** — configurable `STOAT_VERSION_RETENTION_COUNT` env var for keep-last-N pruning per project (BL-144, #184)
- **WebSocket Job Progress** — `JOB_PROGRESS` event type with async broadcast from scan handler and `useJobProgress` frontend hook; replaces HTTP polling in ScanModal (BL-141, #185)
- **OpenAPI-to-TypeScript Codegen Pipeline** — Python spec export (`scripts/export_openapi.py`), `openapi-typescript` codegen, CI drift detection for both JSON and TypeScript layers (BL-139, #186)
- **Effect Preview Thumbnails** — `POST /api/v1/effects/preview/thumbnail` endpoint with async FFmpeg processing, EffectsPage thumbnail display with 500ms debounce (BL-086, #188)
- **UAT CI Pipeline** — GitHub Actions `uat` job with Playwright install, server boot, 4 UAT journeys headless, artifact upload, `dorny/paths-filter` scoping, 5-min timeout, Playwright browser caching (BL-149, #189)

### Changed

- **Frontend Type Migration** — 9 hand-authored TypeScript types replaced with generated OpenAPI imports across 34 files; convenience re-export layer (`generated/types.ts`); deleted unused `types/timeline.ts` (BL-139, #187)
- **`ci-status` gate** updated to include UAT job

### Fixed

- **WebSocket message-loss race condition** — broadcast reordering in `scan.py` ensures critical messages arrive last; ScanModal polling fallback added as safety net (discovered during CI UAT integration)
- **Headless scroll assertion** — journey 203 zoom fix for flaky headless Playwright assertion
- **TimelinePage test failures** — 3 pre-existing test failures fixed (undefined `projects` guard, shared Response mock)

## [v22.1] - 2026-03-23

UAT Bugfix Round. Post-v022 bugfix pass resolving issues discovered during UAT journey execution. 24 fixes across application bugs, test infrastructure, and observability. All 4 UAT journeys now passing.

### Fixed

- **Application Bugs**
  - `scan.py` — `thumbnail_service.generate()` wrapped in `asyncio.to_thread()` to prevent event loop blocking (BL-150)
  - `Navigation.tsx` — HEAD requests changed to GET to eliminate 405 console errors (BL-151)
  - `ClipFormModal.tsx` — pageSize reduced 1000 to 100 to match API validation limit (BL-157)
  - `useEffectPreview.ts` — guard added to skip preview when required schema fields absent (BL-162)
  - `TimelinePage.tsx` — `fetchTimeline()` wired to projectStore for correct project context (BL-163)
  - `useEffectPreview.ts` — null-schema guard added (BL-165)
  - `EffectsPage.tsx` — onChange guard added to prevent clip-clearing on same-project re-select (BL-170)

### Changed

- **Test Infrastructure**
  - `seed_sample_project.py` — httpx timeout increased 60s to 120s, poll iterations 60 to 120 (BL-152)
  - `uat_journey_201.py` — scan-complete timeout increased 30s to 90s (BL-153)
  - `seed_sample_project.py` — `videos_already_scanned()` guard to prevent redundant scans (BL-154)
  - `uat_runner.py` — subprocess.PIPE replaced with file redirect to prevent pipe deadlock (BL-156)
  - `uat_journey_204.py` — clip selection added before effect-stack assertion (BL-158)
  - `uat_journey_203.py` + 204 — effect-stack-item- testid corrected to effect-entry- (BL-159)
  - `uat_journey_203.py` — apply button testid corrected btn-apply-effect to apply-effect-btn (BL-161)
  - `uat_journey_203.py` — clip selection added before effect interactions (BL-166)
  - `uat_journey_203.py` — input selectors corrected from name= to data-testid= (BL-167)
  - `seed_sample_project.py` + `uat_journey_203.py` — timeline track seeding added (BL-168)
  - `uat_journey_203.py` + 204 — clip-block- and preset testids corrected to match components (BL-171)
  - `uat_journey_204.py` — --force flag added to seed invocation for fresh test data (BL-172)
  - `uat_journey_203.py` — filter-preview assertion removed from post-Apply step (BL-173)

- **Observability**
  - `scan.py`, `videos.py`, `manager.py` — 12 structured log events added throughout scan flow (BL-155)
  - `TimelinePage`, `TimelineCanvas`, `timeline.py` — console.debug and structlog events added (BL-160)
  - `effects.py` — `effect_preview_validation_failed` structlog warning added (BL-164)
  - `timeline.py` — `timeline_data_requested` log level promoted DEBUG to INFO (BL-169)

## [v022] - 2026-03-18

UAT (User Acceptance Testing) Framework. Browser-based UAT that validates complete user journeys against a live application instance, closing the end-user UX validation gap between API-level smoke tests and real-world usage.

### Added

- **UAT Runner Harness**
  - `scripts/uat_runner.py` with CLI (`--headed`/`--headless`, `--journey`, `--skip-build`, `--output-dir`)
  - Full build-boot-test-teardown lifecycle with health polling and sample data seeding
  - Dependency-aware fail-fast journey execution (graph: 201->202->203, 204 independent)
  - `uat` optional dependency group in `pyproject.toml`

- **Screenshot & Report Infrastructure**
  - `take_screenshot()` helper with naming convention and `FAIL_` prefix for failures
  - `ConsoleErrorCollector` class for filtered browser console error capture
  - JSON (`uat-report.json`) and markdown (`uat-report.md`) structured report generation

- **Auto-Dev Integration**
  - `docs/auto-dev/VERSION_CLOSURE.md` with tiered UAT automation (Tier 1: headless Playwright, Tier 2: manual fallback)
  - UAT acceptance tier added to testing pyramid in `docs/design/07-quality-architecture.md`

- **UAT Journey Scripts**
  - `uat_journey_201.py` — scan, browse, and FTS5 search workflow (5 steps, 5+ screenshots)
  - `uat_journey_202.py` — project creation, clip addition with in/out points, clips table verification (~290 lines)
  - `uat_journey_203.py` — effects apply/edit/remove, timeline canvas, layout presets (3 sub-journeys, 9 steps)
  - `uat_journey_204.py` — self-seeding Running Montage validation across clips, effects, and timeline pages (~280 lines)

## [v021] - 2026-03-17

Quality & API Completeness. Verifies the BL-138 timeline persistence fix, performs a formal DrawtextBuilder security review, fills five smoke test coverage gaps, and completes the API surface with version creation, filesystem pagination, and layout preset position endpoints.

### Added

- **Version Creation Endpoint**
  - `POST /projects/{id}/versions` returning 201 with auto-incremented version number and SHA-256 checksum

- **Filesystem Pagination**
  - `limit`/`offset` pagination on `GET /filesystem/directories` with `total`, `limit`, `offset` response metadata
  - Updated `DirectoryBrowser.tsx` to use paginated API

- **Preset Positions API**
  - Augmented `GET /compose/presets` with `positions` field served from Rust single source of truth
  - Deleted duplicated `presetPositions.ts` client-side constants

- **Smoke Test Gap Fill**
  - 5 new smoke tests: transition DELETE, audio_ducking, audio_fade, video_fade, acrossfade effect types

- **DrawtextBuilder Security Review**
  - 20 new Rust tests and 10 new Python tests for `escape_drawtext()` injection and Unicode handling
  - Formal security review document confirming no vulnerabilities

- **Timeline Persistence Integration Test**
  - SQLite close/reopen integration test verifying `track_id`, `timeline_start`, `timeline_end` survive DB round-trip (BL-138)

## [v020] - 2026-03-15

Sample Project: Running Montage. Delivers the complete sample project infrastructure for the Running Montage example, including a CLI seed script, smoke test fixture with effects and transitions, regression test, developer-facing user guide, and cross-artifact sync check in IMPACT_ASSESSMENT.

### Added

- **Running Montage Seed Script**
  - `scripts/seed_sample_project.py` — synchronous CLI script creating full Running Montage project (health check, video scan, project, 4 clips, 5 effects, 1 transition)

- **Sample Project Fixture Extensions**
  - Extended `sample_project` fixture in `tests/smoke/conftest.py` with effects and transition creation
  - Added `SAMPLE_EFFECT_DEFS` and `SAMPLE_TRANSITION_DEFS` shared constants

- **Sample Project Regression Test**
  - `tests/smoke/test_sample_project.py` validating project metadata, clip frames, source video associations, and effect-to-clip mappings against canonical constants

- **Sample Project User Guide**
  - `docs/setup/guides/sample-project.md` with prerequisites, quick start, data overview, API exploration, reset instructions, and developer cross-references

- **Sample Project Artifact Sync Check**
  - 5th check in `docs/auto-dev/IMPACT_ASSESSMENT.md` covering seed script, fixture, and guide synchronization across constant categories

## [v019] - 2026-03-14

Smoke Test Coverage Expansion. Extends the Phase 2 smoke test suite to cover 6 API surfaces introduced in v015-v018 (timeline clips, transitions, compose layout, video detail, version restore, filesystem directories), adds negative-path smoke tests for Phase 3 validation rules, and updates harness documentation to reflect Phase 2 completion.

### Added

- **Timeline Clip CRUD Smoke Tests**
  - PATCH position, PATCH track, and DELETE smoke tests for timeline clips in `test_timeline.py`

- **Timeline Transition Smoke Tests**
  - POST and DELETE smoke tests for timeline transitions
  - `create_adjacent_clips_timeline()` conftest helper for multi-clip timeline setup

- **Compose Layout Smoke Tests**
  - POST smoke test for compose layout preset application in `test_compose.py`

- **Video Detail Smoke Tests**
  - GET detail, GET thumbnail, and DELETE smoke tests for videos in `test_library.py`

- **Version Restore Smoke Tests**
  - POST restore smoke test with `create_version_repo()` factory helper for direct repository access

- **Filesystem Directory Smoke Tests**
  - GET directories smoke test with `tmp_path` fixtures and `dir_tree` deterministic fixture in `test_filesystem.py`

- **Negative-Path Smoke Tests**
  - 6 negative-path smoke tests covering timeline, audio, batch, and compose error handling
  - Validates consistent `{"detail": {"code": "...", "message": "..."}}` error response format

- **Harness Documentation Update**
  - Updated 6 documentation files to reflect Phase 1 implementation and Phase 2 expansion status

### Changed

- Smoke test suite expanded from ~22 to ~43 tests across timeline, compose, library, versions, and filesystem modules
- `conftest.py` extended with reusable helpers: `create_adjacent_clips_timeline()`, `create_version_repo()`

### Fixed

- N/A

## [v018] - 2026-03-13

GUI Timeline Canvas + Quality. Builds the visual composition interface (timeline canvas, clip visualization, layout preview), validates Phase 3 with comprehensive smoke and contract tests, and closes out Phase 3 with documentation and C4 architecture updates across all four levels.

### Added

- **Phase 3 Smoke Tests**
  - 5 smoke test files (7 tests) covering timeline, compose, batch render, versions, and audio mix endpoints
  - Full HTTP stack validation with real Rust core via `smoke_client` fixture

- **Phase 3 Contract Tests**
  - 6 contract tests validating overlay filters, composition graphs, and audio mix against real FFmpeg
  - Uses lavfi virtual inputs (`testsrc2`, `sine`) for portable, fast test execution

- **Timeline Page & Navigation**
  - `/gui/timeline` route with Timeline tab in navigation
  - `timelineStore` and `composeStore` Zustand stores with `isLoading`/`error`/`data` async pattern
  - Wired to Phase 3 timeline and compose API endpoints

- **Timeline Canvas**
  - `TimeRuler`, `Track`, `ZoomControls`, `TimelineCanvas` components
  - `timeToPixel()`/`pixelToTime()` coordinate utility for position-accurate rendering
  - Horizontal scroll and zoom controls

- **Clip Visualization & Playhead**
  - `TimelineClip` component with position-accurate rendering, click-to-select, and duration labels
  - `Playhead` component with time position indicator

- **Layout Preview Panel**
  - `LayoutSelector`, `LayoutPreview`, and `LayerStack` components
  - Preset selection consuming backend preset schema
  - Custom coordinate input support
  - Percentage-based CSS positioning for resolution-independent previews

- **Design Document Updates**
  - Updated 5 design docs (roadmap, architecture, API spec, quality architecture, GUI architecture) with Phase 3 content

- **Impact Assessment Patterns**
  - Phase 3 composition model grep patterns (TrackType, LayoutPosition, LayoutPreset, AudioMixSpec, BatchProgress) added to IMPACT_ASSESSMENT

- **C4 Architecture Documentation**
  - 58 Code-level docs across 10 directories covering all modules
  - 8 Component-level docs for all logical components
  - Container-level docs (containers.md, interfaces.md)
  - Context-level system-context.md
  - Covers 6 versions of accumulated drift (v009-v017)

### Changed

- GUI navigation extended with Timeline tab
- Frontend test suite expanded to 301 tests (104 new tests across timeline theme)
- C4 documentation fully regenerated from scratch for current codebase state

### Fixed

- N/A

## [v017] - 2026-03-13

Composition & Audio API + Batch. Delivers composition layout API with preset discovery and filter preview, audio mix configuration endpoints, WebSocket broadcast events for composition mutations, batch rendering with semaphore concurrency, and project version persistence with save/restore/list operations.

### Added

- **Configurable Server Port**
  - Default port changed from 8000 to 8765 to avoid conflicts
  - Wired through pydantic-settings with `SF_PORT` environment variable override
  - Updated 6 code/config files and 17 documentation files

- **Composition Layout API**
  - `GET /api/v1/compose/presets` endpoint returning all 7 Rust LayoutPreset variants with metadata
  - `POST /api/v1/projects/{id}/compose/layout` accepting preset or custom positions
  - FFmpeg filter preview generation via Rust `build_overlay_filter()` delegation
  - 30 tests across preset discovery and layout application

- **Audio Mix Configuration**
  - `PUT /api/v1/projects/{id}/audio/mix` for persisting audio mix settings
  - `POST /api/v1/projects/{id}/audio/mix/preview` for FFmpeg filter preview
  - Per-track volume, fade-in/fade-out, master volume, and normalize controls
  - Rust `AudioMixSpec` filter generation with `VolumeBuilder` semicolon concatenation
  - `audio_mix_json` column for JSON persistence following `transitions_json` pattern

- **Composition WebSocket Events**
  - 4 new `EventType` enums: `TIMELINE_UPDATED`, `LAYOUT_APPLIED`, `AUDIO_MIX_CHANGED`, `TRANSITION_APPLIED`
  - Broadcast wired into 8 mutation routes across timeline, compose, and audio routers
  - DRY `_broadcast()` helper pattern for consistent event dispatch

- **Batch Render Endpoint**
  - `POST /api/v1/render/batch` with `asyncio.Semaphore` concurrency control
  - `GET /api/v1/render/batch/{batch_id}` for batch status polling
  - Configurable `batch_parallel_limit` and `batch_max_jobs` settings with bounded ranges

- **Version Persistence**
  - `project_versions` table with SHA-256 checksum integrity verification
  - `AsyncVersionRepository` with SQLite and in-memory implementations
  - Contract tests ensuring parity between both repository backends
  - Non-destructive restore pattern (creates new version, preserves full history)

- **Version API Endpoints**
  - `GET /api/v1/projects/{id}/versions` with pagination support
  - `POST /api/v1/projects/{id}/versions/{version}/restore` with checksum validation

### Changed

- Default API port from 8000 to 8765 across all configuration and documentation
- Project model extended with `audio_mix_json` column for audio mix persistence
- Database schema extended with `project_versions` table for version storage
- Timeline, compose, and audio routers extended with WebSocket broadcast calls

### Fixed

- Clip repository SQL for timeline fields (`track_id`, `timeline_start`, `timeline_end`) now correctly included in UPDATE statements

## [v016] - 2026-03-11

Composition Graph + Timeline API. First full Phase 3 version delivering the Rust composition graph builder, multi-track audio mixing specification, batch progress calculator, timeline data layer with persistent storage, and complete timeline REST API with transition support.

### Added

- **AudioMixSpec & TrackAudioConfig (Rust)**
  - `AudioMixSpec` for coordinated multi-track audio mixing with per-track volume, fade-in/fade-out
  - `TrackAudioConfig` for individual track audio parameters
  - PyO3 bindings with proptest coverage for parameter validation

- **Batch Progress Calculator (Rust)**
  - `BatchJobStatus` enum with wrapper pyclass pattern for enum variant data
  - `BatchProgress` struct for batch render progress aggregation
  - `calculate_batch_progress()` pure function with PyO3 bindings

- **Composition Graph Builder (Rust)**
  - `build_composition_graph()` integrating overlay, scale, transitions, and audio mix into complete `FilterGraph` output
  - Sequential and layout composition modes with universal canvas base
  - PyO3 bindings with Python parity tests

- **Track & Clip Data Models (Python)**
  - `Track` dataclass for multi-track timeline representation
  - Extended `Clip` with nullable timeline fields: `track_id`, `timeline_start`, `timeline_end`
  - Database migration for `tracks` table and ALTER TABLE for clip timeline columns

- **Timeline Repository (Python)**
  - `AsyncTimelineRepository` with async CRUD for tracks and timeline-aware clip queries
  - `AsyncSQLiteTimelineRepository` and `InMemoryTimelineRepository` implementations
  - DI wiring via `create_app()` kwargs following established patterns

- **Timeline API Endpoints (Python)**
  - `PUT /api/v1/projects/{id}/timeline` — Initialize/replace timeline
  - `GET /api/v1/projects/{id}/timeline` — Get timeline with tracks and clips
  - `POST /api/v1/projects/{id}/timeline/clips` — Add clip to timeline
  - `PATCH /api/v1/projects/{id}/timeline/clips/{id}` — Update timeline clip
  - `DELETE /api/v1/projects/{id}/timeline/clips/{id}` — Remove clip from timeline
  - 6 Pydantic request/response schemas for timeline operations

- **Timeline Transition Endpoints (Python)**
  - `POST /api/v1/projects/{id}/timeline/transitions` — Create transition between adjacent clips
  - `DELETE /api/v1/projects/{id}/timeline/transitions/{id}` — Remove transition
  - Rust core integration via `calculate_composition_positions()` for offset calculation
  - Adjacency validation guard before Rust delegation

### Changed

- Clip model extended with nullable timeline fields for track assignment and timeline positioning
- Database schema extended with `tracks` table and clip timeline columns

### Fixed

- N/A

## [v015] - 2026-03-10

Phase 2 Quality Debt + Rust Layout/Composition Core. Retires all Phase 2 quality debt (coverage enforcement, property testing, FFmpeg contract tests, performance benchmarks) and builds the foundational Rust layout and composition modules for Phase 3.

### Added

- **Unit Test Coverage Enforcement**
  - Achieved >95% line coverage for all 8 `src/ffmpeg/` modules with error path tests
  - CI enforcement step parsing `cargo llvm-cov --json` for per-module coverage checks

- **Property-Based Testing (Filter Builders)**
  - 12 proptest strategies across drawtext, speed, audio, and transitions builders
  - Coverage of both valid and invalid parameter ranges for thorough edge case detection

- **FFmpeg Contract Tests**
  - 15 contract tests validating Phase 2 filter builder outputs against real FFmpeg execution
  - `@requires_ffmpeg` marker for graceful CI skip in environments without FFmpeg

- **Performance Benchmarks**
  - 15 Criterion benchmarks across 7 groups for filter builders
  - Baseline performance measurements with HTML reports in `target/criterion/`

- **LayoutPosition (Rust)**
  - `LayoutPosition` struct with normalized coordinates (0.0–1.0), `to_pixels()` conversion, and `validate()`
  - `LayoutError` exception type for invalid coordinate values
  - PyO3 bindings with proptest coverage for pixel rounding edge cases

- **LayoutPreset (Rust)**
  - `LayoutPreset` enum with 7 variants: 4 PIP corners, SideBySide, TopBottom, Grid2x2
  - `positions(input_count)` method returning `Vec<LayoutPosition>` for preset layouts
  - PyO3 bindings with manual type stubs (pyo3-stub-gen does not support enums)

- **Overlay & Scale Filter Builders (Rust)**
  - `build_overlay_filter()` and `build_scale_for_layout()` in `compose/overlay` module
  - Converts LayoutPosition to FFmpeg filter strings with `force_divisible_by=2` for codec compatibility
  - PyO3 bindings, proptest strategies, and FFmpeg contract tests

- **Composition Position Calculator (Rust)**
  - `CompositionClip` and `TransitionSpec` structs for multi-clip timeline representation
  - `calculate_composition_positions()` and `calculate_timeline_duration()` with transition overlap clamping
  - PyO3 bindings and comprehensive tests for clamping edge cases

### Changed

- N/A

### Fixed

- N/A

## [v014] - 2026-03-09

Phase 2 Smoke Test. API-level smoke test suite exercising the full backend stack (HTTP → FastAPI → Services → PyO3/Rust → SQLite) with real video files, providing a verified Phase 2 baseline before Phase 3 begins.

### Added

- **Smoke Test Infrastructure**
  - `tests/smoke/` directory with `conftest.py` containing `EXPECTED_VIDEOS` dict, 5 fixtures (`videos_dir`, `smoke_client`, `sample_project`, etc.), and 3 async helpers
  - 6 real MP4 video files committed to git for deterministic, cross-platform test inputs
  - Lifespan-aware `smoke_client` fixture wrapping `httpx.AsyncClient` inside `async with lifespan(app)`
  - Per-test DB isolation via `tmp_path` for independent, parallelizable smoke tests
  - Default exclusion via `--ignore=tests/smoke` in pytest addopts to keep fast unit test loop unaffected

- **Core Workflow Smoke Tests**
  - 7 use cases across 4 test files covering scan, library, project, and clip workflows
  - Full-stack validation: HTTP → FastAPI → Services → PyO3/Rust → SQLite

- **Effects, Transitions & Health Smoke Tests**
  - 5 use cases across 3 test files covering effect catalog/apply, effect update/delete, fade transitions, health endpoints, and speed control + stacking
  - Full-stack exercise through Rust PyO3 filter builders validating filter-string output shape

- **CI Integration & Maintenance**
  - CI `smoke-tests` job running on 3 OS × Python 3.12 matrix
  - `pytest-timeout` dependency for smoke test time bounds
  - `IMPACT_ASSESSMENT.md` updated with 3 maintenance checks using grep-pattern approach
  - AGENTS.md quality gates updated with smoke test guidance

### Changed

- `--no-cov` flag used for smoke tests to avoid coverage threshold failures on integration-focused tests

### Fixed

- N/A

## [v013] - 2026-03-07

Scan Dialog Freeze Fix. Fixes the P0 scan dialog freeze where the progress bar reached 100% but the completion branch never fired, and adds timeout status handling so timed-out scans show an error instead of polling indefinitely.

### Added

- N/A

### Changed

- N/A

### Fixed

- **Scan Dialog Freeze (BL-080)**
  - Fixed `'completed'` vs `'complete'` string mismatch between frontend `JobStatus` type union and backend `JobStatus.COMPLETE` enum in `ScanModal.tsx`
  - Updated polling comparison and test mock atomically
  - Added integration test for scan completion flow (running -> complete -> onScanComplete fires)
- **Timeout Status Handling**
  - Added `'timeout'` to frontend `JobStatus` type union
  - Added timeout error handling branch mirroring the existing `'failed'` pattern
  - Timed-out scans now show an error message instead of polling indefinitely

## [v012] - 2026-02-25

API Surface & Bindings Cleanup. Removes 11 unused PyO3 bindings and 1 dead bridge function from the Rust-Python boundary, wires transition effects into the Effect Workshop GUI, and corrects misleading API specification examples.

### Added

- **Transition GUI in Effect Workshop**
  - Transitions tab on EffectsPage with clip-pair selection mode
  - `transitionStore` Zustand store for transition state management
  - `TransitionPanel` component with schema-driven parameter forms via `EffectParameterForm` reuse
  - `ClipSelector` extended with optional pair-mode props for two-clip selection flow
  - Non-adjacent-clip error feedback from existing `POST /api/v1/effects/transition` endpoint

### Removed

- **Dead `execute_command()` Bridge Function**
  - Removed `execute_command()` function and `CommandExecutionError` class from `stoat_ferret.ffmpeg.integration`
  - Removed exports from `stoat_ferret.ffmpeg` package `__init__.py`
  - Deleted `tests/test_integration.py` (13 tests covering only the removed function)
  - Zero production callers — `ThumbnailService` calls `executor.run()` directly
  - **Re-add trigger:** Phase 3 Composition Engine or any future render/export endpoint needing Rust command building (LRN-029)

- **Unused v001 PyO3 Bindings (BL-067)**
  - Removed `find_gaps`, `merge_ranges`, `total_coverage` PyO3 wrappers from `timeline/range.rs`
  - Removed `validate_crf`, `validate_speed` PyO3 wrappers from `sanitize/mod.rs`
  - Removed 5 functions from Python module registration, imports, stubs, and `__all__`
  - Removed `TestRangeListOperations` class (~15 tests) and `TestSanitization` crf/speed tests (~4 tests) from `tests/test_pyo3_bindings.py`
  - Deleted `benchmarks/bench_ranges.py` (3 benchmarks referencing removed bindings)
  - Rust-internal implementations preserved; zero production callers
  - **Re-add triggers:** TimeRange ops: Phase 3 Composition Engine; sanitization: Python-level standalone validation need

- **Unused v006 PyO3 Bindings (BL-068)**
  - Removed `Expr` (PyExpr) PyO3 wrapper from `ffmpeg/expression.rs`
  - Removed `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge` PyO3 wrappers from `ffmpeg/filter.rs`
  - Removed 6 bindings from Python module registration, imports, stubs, and `__all__`
  - Removed `TestExpr` class (~16 tests) and `TestFilterComposition` class (~15 tests) from `tests/test_pyo3_bindings.py`
  - Rust-internal implementations preserved; zero production callers
  - **Re-add triggers:** Expr: Python-level expression building for custom filter effects; compose: Python-level filter graph composition outside Rust builders

### Changed

- N/A

### Fixed

- **API Spec Documentation Corrections**
  - Fixed 6 job status example values in API specification and manual to use 0.0–1.0 normalized floats matching actual code behavior
  - Corrected running, complete, cancel, failed, and timeout progress examples
  - Fixed manual range documentation for progress field
  - Added `cancelled` status to documented job status values

## [v011] - 2026-02-24

GUI Usability & Developer Experience. Closes the biggest GUI interaction gaps with a directory browser for scan path selection and full clip CRUD controls, then improves developer onboarding with environment template, Windows guidance, and design-time impact assessment checks.

### Added

- **Directory Browser**
  - `GET /api/v1/filesystem/directories` endpoint with `validate_scan_path()` security enforcement
  - `DirectoryBrowser` overlay component in ScanModal for selecting scan paths
  - Non-blocking filesystem access via `run_in_executor` for `os.scandir()`

- **Clip CRUD Controls**
  - Add/Edit/Delete clip controls on ProjectDetails page
  - `ClipFormModal` with form validation for clip in/out points
  - `clipStore` Zustand store following per-entity pattern (like `effectStackStore`)
  - Wired to existing backend POST/PATCH/DELETE clip endpoints

- **Environment Template**
  - `.env.example` covering all 11 Settings fields with inline documentation
  - Cross-references added to AGENTS.md, quickstart guide, and contributing docs

- **Windows Developer Guidance**
  - Git Bash `/dev/null` pitfall documentation added to AGENTS.md Windows section

- **Impact Assessment**
  - `IMPACT_ASSESSMENT.md` with 4 design-time checks: async safety, settings documentation, cross-version wiring, GUI input mechanisms (BL-076)
  - Captures recurring issue patterns for early detection during version design

### Changed

- ScanModal now includes embedded DirectoryBrowser overlay for path selection instead of manual text entry only

### Fixed

- N/A

## [v010] - 2026-02-23

Async Pipeline Fix & Job Controls. Fixes the P0 blocking subprocess.run() in ffprobe that froze the asyncio event loop during scans, adds CI guardrails and runtime regression tests to prevent recurrence, then builds user-facing job progress reporting and cooperative cancellation on the working pipeline.

### Added

- **Async FFprobe**
  - `ffprobe_video()` converted from blocking `subprocess.run()` to `asyncio.create_subprocess_exec()` with timeout and process cleanup
  - 30-second configurable timeout with proper process termination on timeout/cancellation

- **Async Blocking CI Gate**
  - Ruff ASYNC rules (ASYNC210, ASYNC221, ASYNC230) enabled to detect blocking calls in async functions at CI time
  - `_check_ffmpeg()` in health.py wrapped with `asyncio.to_thread()` to comply with new rules

- **Event-Loop Responsiveness Test**
  - Integration test verifying asyncio event loop stays responsive (< 2s jitter) during directory scans
  - Uses production `AsyncioJobQueue` to exercise real async concurrency

- **Job Progress Reporting**
  - `progress` field added to job entries (percentage, current file index, total files)
  - Scan handler reports per-file progress via `progress_callback`
  - Progress exposed via `GET /api/v1/jobs/{id}` endpoint

- **Cooperative Job Cancellation**
  - `cancel_event` (`asyncio.Event`) for cooperative cancellation signaling
  - `POST /api/v1/jobs/{id}/cancel` endpoint with 200/404/409 status codes
  - Scan handler checks cancellation at per-file checkpoints, saves partial results
  - Frontend abort button with Vitest test coverage

### Changed

- `scan_directory()` pre-collects video files for accurate progress total instead of lazy glob iteration
- `AsyncJobQueue` Protocol extended with `set_progress()` and `cancel()` methods
- `InMemoryJobQueue` updated with no-op stubs for new protocol methods

### Fixed

- P0: `ffprobe_video()` no longer freezes the asyncio event loop during directory scans (BL-072)

## [v009] - 2026-02-22

Observability Pipeline & GUI Runtime Fixes. Wires pre-existing observability components (FFmpeg metrics, audit logging, file-based logs) into the application's DI chain and startup sequence, and fixes three GUI runtime gaps (SPA routing fallback, projects pagination, WebSocket broadcasts).

### Added

- **FFmpeg Observability Wiring**
  - `ObservableFFmpegExecutor` wired into DI chain via lifespan; FFmpeg operations now emit Prometheus metrics and structured logs in production
  - Test-injection bypass preserves clean test doubles without observable wrapper noise

- **Audit Logging Wiring**
  - `AuditLogger` wired into repository DI with separate sync `sqlite3.Connection` alongside `aiosqlite`
  - WAL mode enables concurrent sync/async access without deadlocks
  - Database mutations now produce audit entries automatically

- **File-Based Logging**
  - `RotatingFileHandler` integrated into `configure_logging()` with 10MB rotation and 5 backup files
  - `logs/` directory auto-created on startup
  - Idempotent handler registration prevents duplicate file handlers

- **SPA Routing Fallback**
  - Replaced `StaticFiles` mount with catch-all FastAPI routes (`/gui` and `/gui/{path:path}`)
  - Static files served directly; unmatched paths fall back to `index.html` for client-side routing

- **Projects Pagination Fix**
  - `count()` added to `AsyncProjectRepository` protocol (SQLite `SELECT COUNT(*)`, InMemory `len()`)
  - API endpoint returns true total count instead of page result length
  - Frontend pagination UI added to projects page matching library browser pattern

- **WebSocket Broadcasts**
  - `ConnectionManager.broadcast()` wired into project creation (`PROJECT_CREATED`) and scan handler (`SCAN_STARTED`, `SCAN_COMPLETED`)
  - Guard pattern (`if ws_manager:`) allows broadcasts to be optional without affecting tests or minimal deployments

### Changed

- Lifespan startup sequence extended with FFmpeg observability wrapping, audit logger initialization, and file handler registration
- SPA routing uses catch-all routes instead of `StaticFiles` mount for GUI paths
- Projects list endpoint returns accurate pagination total via repository `count()`

### Fixed

- Direct navigation to GUI sub-paths (e.g., `/gui/library`) no longer returns 404
- Projects pagination total now reflects actual dataset size instead of current page length

## [v008] - 2026-02-22

Application Startup Wiring & CI Stability. Wires disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence, and fixes a flaky E2E test that intermittently blocked CI merges.

### Added

- **Database Startup Wiring**
  - `create_tables_async()` called in lifespan so database schema is created automatically on fresh startup
  - 3 duplicate test helpers consolidated into shared import

- **Logging Startup Wiring**
  - `configure_logging()` wired into lifespan with `settings.log_level` controlling verbosity
  - Idempotent handler guard prevents duplicate log handlers
  - Uvicorn log level made configurable from settings

- **Orphaned Settings Wiring**
  - `settings.debug` wired to `FastAPI(debug=...)` for error detail control
  - `settings.ws_heartbeat_interval` replaces hardcoded constant in WebSocket manager
  - All 9 `Settings` fields now consumed by production code

### Changed

- Lifespan startup sequence extended with database schema creation and logging configuration
- WebSocket heartbeat interval now driven by settings instead of hardcoded value

### Fixed

- Flaky E2E `toBeHidden()` assertion in `project-creation.spec.ts` — added explicit 10-second timeout matching established pattern in other specs (BL-055)

## [v007] - 2026-02-19

Effect Workshop GUI. Implements Rust filter builders for audio mixing and video transitions, refactors the effect registry to builder-protocol dispatch with JSON schema validation, builds the complete GUI effect workshop (catalog, parameter forms, live preview, builder workflow), and validates with E2E tests and accessibility compliance. Covers milestones M2.4–M2.6, M2.8–M2.9.

### Added

- **Audio Mixing Builders (Rust)**
  - `AmixBuilder` for multi-input audio mixing with weighted inputs and dropout handling
  - `VolumeBuilder` for audio level adjustment with expression support
  - `AfadeBuilder` for audio fade-in/fade-out with configurable curves (FadeCurve enum)
  - `DuckingPattern` for multi-filter audio ducking using FilterGraph composition API
  - 54 Rust unit tests + 42 Python parity tests

- **Transition Filter Builders (Rust)**
  - `FadeBuilder` for video fade-in/fade-out with alpha channel support
  - `XfadeBuilder` with `TransitionType` enum covering all 59 FFmpeg xfade variants
  - `AcrossfadeBuilder` for combined audio crossfade + video xfade transitions
  - Reused `FadeCurve` enum from audio module for cross-domain consistency
  - 35 Rust unit tests + 46 Python parity tests

- **Effect Registry Refactor**
  - Builder-protocol dispatch via `build_fn` field on `EffectDefinition`, replacing if/elif monolith
  - JSON schema validation using `jsonschema.Draft7Validator` with structured error messages
  - 9 effects registered with self-contained build functions and parameter schemas
  - Prometheus counter for effect build operations

- **Transition API**
  - `POST /api/v1/effects/transition` endpoint with clip adjacency validation
  - Specific error codes: `SAME_CLIP`, `EMPTY_TIMELINE`, `NOT_ADJACENT`
  - Persistent transition storage via `transitions_json` column on Project model

- **Effect Catalog UI**
  - Grid/list view of available effects with search (300ms debounce) and category filter
  - AI hint tooltips from effect registry metadata
  - Effect selection dispatched to parameter form

- **Dynamic Parameter Forms**
  - Schema-driven `SchemaField` dispatcher rendering typed sub-components
  - Input widgets: number/range slider, string, enum dropdown, boolean toggle, color picker
  - Validation from JSON schema constraints with dirty-state tracking

- **Live Filter Preview**
  - `POST /api/v1/effects/preview` endpoint returning built filter strings
  - Debounced preview panel with regex-based FFmpeg syntax highlighting
  - Copy-to-clipboard functionality

- **Effect Builder Workflow**
  - Clip selector component for choosing target clips
  - Effect stack visualization with ordering
  - `PATCH /api/v1/projects/{id}/clips/{id}/effects/{index}` for editing effects
  - `DELETE /api/v1/projects/{id}/clips/{id}/effects/{index}` for removing effects
  - Full CRUD lifecycle: browse catalog → configure parameters → preview → apply → edit/remove

- **E2E Testing & Accessibility**
  - 8 Playwright E2E tests covering catalog browse, parameter config, apply/edit/remove workflow
  - Keyboard navigation test (Tab, Enter, Space through full workflow)
  - axe-core WCAG AA accessibility scans on effect workshop pages
  - Serial test mode for stateful CRUD test group

- **Documentation Updates**
  - API specification updated with 3 new endpoints (preview, PATCH, DELETE)
  - Roadmap milestones M2.4, M2.5, M2.6, M2.8, M2.9 marked complete
  - GUI architecture document updated with Effect Workshop components
  - C4 architecture documentation regenerated at all levels

### Changed

- Effect registry dispatch refactored from monolithic if/elif to per-definition `build_fn` callables
- Project model extended with `transitions_json` column for persistent transition storage
- Effects router simplified — dispatch delegated to registry lookup

### Fixed

- Parameter validation errors now return structured messages from JSON schema validation instead of opaque PyO3 type coercion failures

## [v006] - 2026-02-19

Effects Engine Foundation. Builds a greenfield Rust filter expression engine with graph validation, composition system, text overlay and speed control builders, effect discovery API, and clip effect application endpoint. Completes Phase 2 core milestones (M2.1-M2.3).

### Added

- **Filter Expression Engine (Rust)**
  - `Expr` enum with type-safe builder API for FFmpeg filter expressions
  - Operator overloading and precedence-aware serialization (minimizes parentheses)
  - FFmpeg variable support (`t`, `n`, `w`, `h`, etc.) and function calls (`if`, `lt`, `between`, etc.)
  - Proptest validation for expression correctness (balanced parens, no NaN/Inf)
  - Full PyO3 bindings with Python type stubs

- **Filter Graph Validation (Rust)**
  - Opt-in `validate()` and `validated_to_string()` methods on `FilterGraph`
  - Unconnected pad detection, duplicate label detection
  - Cycle detection using Kahn's algorithm (O(V+E)) with involved-label error messages
  - Backward-compatible: existing `to_string()` behavior unchanged

- **Filter Composition API (Rust)**
  - `compose_chain`, `compose_branch`, `compose_merge` programmatic composition functions
  - `LabelGenerator` with thread-safe `AtomicU64` counter for automatic pad label management
  - Auto-generated `_auto_{prefix}_{seq}` labels for debugging clarity

- **DrawtextBuilder (Rust)**
  - Type-safe drawtext filter builder with fluent API
  - Position presets enum (Center, BottomCenter, TopLeft, etc.) with margin parameters
  - Font styling (family, size, color), shadow and box background effects
  - Alpha fade animation via expression engine integration
  - Extended text escaping (`%` -> `%%` for drawtext expansion mode)

- **SpeedControl (Rust)**
  - `setpts` video speed builder with expression-based PTS manipulation
  - `atempo` audio speed builder with automatic chaining for speeds outside [0.5, 2.0]
  - Decomposition algorithm for extreme speeds (e.g., 4x -> atempo=2.0,atempo=2.0)
  - Drop-audio option for video-only speed changes
  - Proptest validation for atempo chain product correctness and bound compliance

- **Effect Discovery API (Python)**
  - `EffectRegistry` with parameter schemas and AI hints for each registered effect
  - `GET /api/v1/effects` endpoint returning available effects with metadata
  - Preview function integration (previewed filters match applied filters)

- **Clip Effect Application API (Python)**
  - `POST /api/v1/projects/{id}/clips/{id}/effects` endpoint
  - Effect storage as JSON list column in clip model (`effects_json TEXT`)
  - DrawtextBuilder and SpeedControl dispatch from API parameters
  - DI via `create_app()` kwarg -> `app.state.effect_registry` pattern

- **Architecture Documentation**
  - Updated `02-architecture.md` with Rust filter modules, Effects Service, and clip model extension
  - API specification reconciled with actual implementation
  - C4 architecture documentation regenerated at all levels

### Changed

- Clip model extended with `effects_json` column for persistent effect storage
- Effects router serves both global (`/api/v1/effects`) and per-clip (`/api/v1/projects/{id}/clips/{id}/effects`) routes

### Fixed

- N/A (greenfield implementation)

## [v005] - 2026-02-09

GUI Shell, Library Browser & Project Manager. Builds the frontend from scratch: React/TypeScript/Vite project, WebSocket real-time events, backend thumbnail pipeline, four main GUI panels, and Playwright E2E testing. Completes Phase 1 (M1.10-M1.12).

### Added

- **Frontend Foundation**
  - React/TypeScript/Vite project scaffolded in `gui/` with Tailwind CSS v4
  - FastAPI StaticFiles mount at `/gui` with conditional directory check
  - CI `frontend` job for build/lint/test in parallel with Python matrix
  - WebSocket endpoint (`/ws`) with `ConnectionManager`, heartbeat, correlation IDs
  - Lazy dead connection cleanup during broadcast with `asyncio.Lock`
  - Settings fields: `thumbnail_dir`, `gui_static_path`, `ws_heartbeat_interval`

- **Backend Services**
  - `ThumbnailService` with FFmpeg executor pattern for video thumbnail extraction
  - `GET /api/v1/videos/{id}/thumbnail` endpoint with placeholder fallback
  - Scan-time automatic thumbnail generation
  - `AsyncVideoRepository.count()` protocol method (SQLite and InMemory)
  - Paginated list endpoint now returns true total count (not page length)

- **GUI Components**
  - Application shell with header/content/footer layout and tab navigation via React Router
  - Health indicator polling `/health/ready` every 30s (green/yellow/red)
  - WebSocket hook with auto-reconnect and exponential backoff (1s to 30s)
  - Dashboard panel with health cards (Python API, Rust Core, FFmpeg) and real-time activity log
  - Prometheus metrics cards parsing text format for request count/duration
  - Library browser with responsive video grid, thumbnails, search (300ms debounce), sort controls, scan modal with progress, and pagination
  - Project manager with list view, creation modal (resolution/fps/format validation), project details with timeline positions, and delete confirmation
  - Three Zustand stores: activity, library, project

- **E2E Testing**
  - Playwright configuration with `webServer` auto-starting FastAPI
  - CI `e2e` job on ubuntu-latest with Chromium browser caching
  - Navigation, scan trigger, project creation, and WCAG AA accessibility E2E tests
  - axe-core accessibility checks on all three main views

### Changed

- `create_app()` auto-loads `gui_static_path` from settings when not explicitly provided
- Architecture, API, and AGENTS documentation updated for frontend and WebSocket

### Fixed

- SortControls WCAG 4.1.2 violation: added missing `aria-label` attribute
- Pagination `total` field now returns true dataset count instead of page result count

## [v004] - 2026-02-09

Testing Infrastructure & Quality Verification. Establishes test doubles, dependency injection, fixture factories, black box and contract tests, async scan infrastructure, security audit, performance benchmarks, and developer experience tooling.

### Added

- **Test Foundation**
  - InMemory test doubles for all repositories with deepcopy isolation and seed helpers
  - Constructor-based dependency injection via `create_app()` kwargs on `app.state`
  - Builder-pattern fixture factory with `build()` (unit) and `create_via_api()` (integration) outputs
  - `InMemoryJobQueue` for deterministic synchronous job execution in tests

- **Black Box & Contract Testing**
  - 30 REST API black box workflow tests (project CRUD, clips, error handling, edge cases)
  - 21 parametrized FFmpeg contract tests verifying Real, Recording, and Fake executor parity
  - `strict` mode for FFmpeg executor args verification
  - Per-token `startswith` search in InMemory repositories matching FTS5 prefix semantics
  - 7 search parity tests ensuring InMemory/SQLite consistency

- **Async Scan Infrastructure**
  - `AsyncioJobQueue` using `asyncio.Queue` producer-consumer pattern with background worker
  - `POST /videos/scan` now returns `202 Accepted` with `job_id` for async processing
  - `GET /api/v1/jobs/{job_id}` endpoint for job status polling
  - Handler registration pattern with `make_scan_handler()` factory for DI
  - Configurable per-job timeout (default 5 minutes)

- **Security & Performance**
  - Security audit of all 8 Rust sanitization/validation functions against OWASP vectors
  - `ALLOWED_SCAN_ROOTS` configuration with `validate_scan_path()` enforcement
  - 35 security tests across 5 attack categories (path traversal, null bytes, shell injection, whitelist bypass, FFmpeg filter injection)
  - Performance benchmark suite comparing Rust vs Python across 7 operations in 4 categories
  - Security audit document (`docs/design/09-security-audit.md`)
  - Performance benchmark document (`docs/design/10-performance-benchmarks.md`)

- **Developer Experience & Coverage**
  - Property-based testing guidance with Hypothesis dependency and design template integration
  - Rust code coverage via `cargo-llvm-cov` with 75% CI threshold
  - Docker-based testing environment with multi-stage build (`Dockerfile`, `docker-compose.yml`)
  - `@pytest.mark.requires_ffmpeg` marker for conditional CI execution

### Changed

- `POST /videos/scan` refactored from synchronous blocking to async job queue pattern
- Design documents updated to reflect async scan behavior (`02-architecture.md`, `03-prototype-design.md`, `04-technical-stack.md`, `05-api-specification.md`)
- Requirements and implementation-plan templates updated with property test (PT-xxx) sections

### Fixed

- Coverage exclusion audit: removed unjustified `pragma: no cover` on ImportError fallback in `__init__.py`, added fallback tests

## [v003] - 2026-01-28

API Layer + Clip Model (Roadmap M1.6-1.7). Establishes FastAPI REST API, async repository layer, video library endpoints, clip/project data models with Rust validation, and CI improvements.

### Added

- **Process Improvements**
  - `AsyncVideoRepository` protocol with async SQLite and in-memory implementations
  - CI migration verification step (upgrade → downgrade → upgrade)
  - CI path filters using `dorny/paths-filter` to skip heavy tests for docs-only changes
  - Three-job CI structure (changes → test → ci-status) for branch protection

- **API Foundation**
  - FastAPI application factory with lifespan context manager for database lifecycle
  - Externalized configuration using pydantic-settings with environment variable support
  - Health endpoints: `/health/live` (liveness) and `/health/ready` (readiness with dependency checks)
  - Middleware stack with correlation ID (`X-Correlation-ID` header) and Prometheus metrics

- **Library API**
  - `GET /api/v1/videos` - List videos with pagination (offset/limit)
  - `GET /api/v1/videos/{video_id}` - Get video details by ID
  - `GET /api/v1/videos/search` - Full-text search with FTS5 integration
  - `POST /api/v1/videos/scan` - Directory scanning with FFprobe metadata extraction
  - `DELETE /api/v1/videos/{video_id}` - Delete video with optional file removal (`delete_file` flag)

- **Clip Model**
  - `Project` model for organizing clips with output settings (resolution, fps)
  - `Clip` model with in/out points delegating validation to Rust core
  - `AsyncProjectRepository` and `AsyncClipRepository` with SQLite and in-memory implementations
  - `GET/POST /api/v1/projects` - List and create projects
  - `GET/PUT/DELETE /api/v1/projects/{project_id}` - Project CRUD operations
  - `GET/POST /api/v1/projects/{project_id}/clips` - List and create clips
  - `GET/PUT/DELETE /api/v1/clips/{clip_id}` - Clip CRUD operations

### Changed

- Repository pattern now supports both sync (CLI) and async (API) access
- CI workflow now conditionally runs tests based on changed paths
- pytest-asyncio configured with `asyncio_mode = "auto"` for cleaner async tests

### Fixed

- CI migration reversibility now verified automatically on every push

## [v002] - 2026-01-27

Database & FFmpeg Integration with Python Bindings Completion. Addresses roadmap M1.4-1.5.

### Added

- **Python Bindings Completion**
  - `Clip` and `ClipValidationError` types exposed to Python with full property access
  - `find_gaps`, `merge_ranges`, and `total_coverage` functions for TimeRange operations
  - Automatic stub generation verification script (`scripts/verify_stubs.py`)
  - CI drift detection for stub files

- **Database Foundation**
  - SQLite schema with 14-column `videos` table for video metadata storage
  - FTS5 full-text search with automatic index synchronization via triggers
  - `VideoRepository` protocol with SQLite and InMemory implementations
  - Alembic migration support with rollback capability
  - Audit logging for tracking all data modifications (`audit_log` table)

- **FFmpeg Integration**
  - FFprobe wrapper for extracting structured video metadata (`VideoMetadata` dataclass)
  - `FFmpegExecutor` protocol with Real, Recording, and Fake implementations
  - Integration layer bridging Rust `FFmpegCommand` to Python executor
  - Recording/replay pattern for deterministic subprocess testing
  - `ObservableFFmpegExecutor` wrapper with structured logging (structlog)
  - Prometheus metrics for FFmpeg command execution (duration, success/failure counts)

- **Process Documentation**
  - PyO3 bindings section in AGENTS.md with incremental binding rule
  - Stub regeneration workflow documentation
  - Naming convention guidance (`py_` prefix with `#[pyo3(name)]` attribute)

### Changed

- API naming cleanup: removed `py_` prefixes from 16 Python-visible method names
- Updated 37 test assertions for new API naming
- Renamed Rust `ValidationError` to `ClipValidationError` in Python for clarity

### Fixed

- Stub drift between generated and manual stubs now caught by CI verification

## [v001] - 2026-01-26

Foundation version establishing hybrid Python/Rust architecture with timeline math and FFmpeg command building.

### Added

- **Project Foundation**
  - Python project structure with uv, ruff, mypy, and pytest
  - Rust workspace with PyO3 bindings (abi3-py310)
  - GitHub Actions CI pipeline (Ubuntu, Windows, macOS × Python 3.10, 3.11, 3.12)
  - Type stubs for IDE support and mypy integration

- **Timeline Math (Rust)**
  - `FrameRate` type with rational numerator/denominator representation
  - `Position` type for frame-accurate timeline positions
  - `Duration` type for frame-accurate time spans
  - `Clip` type with validation (start, end, media_start, media_duration)
  - `ValidationError` with field, message, actual, and expected values
  - `TimeRange` with half-open interval semantics
  - Range operations: overlap, intersection, union, subtraction, contains
  - List operations: find_gaps, merge_ranges (O(n log n))
  - Property-based tests for invariants (proptest)

- **FFmpeg Command Builder (Rust)**
  - `FFmpegCommand` fluent builder with input/output management
  - Position-sensitive option handling (seek, codecs, filters)
  - `Filter`, `FilterChain`, and `FilterGraph` types
  - Common filter constructors: scale, pad, fps, setpts, concat, atrim
  - Input sanitization: text escaping, path validation, bounds checking
  - Codec and preset whitelist validation
  - Complete PyO3 bindings with method chaining support

- **Python API**
  - `stoat_ferret_core` module with all Rust types exposed
  - ImportError fallback for development without Rust builds
  - Full type stubs in `stubs/stoat_ferret_core/`

### Changed

- N/A (initial release)

### Fixed

- N/A (initial release)
