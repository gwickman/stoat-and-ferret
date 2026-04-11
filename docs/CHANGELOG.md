# Changelog

All notable changes to stoat-and-ferret will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
