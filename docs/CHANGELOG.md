# Changelog

All notable changes to stoat-and-ferret will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v012] - 2026-02-25

Rust Bindings Cleanup. Removes dead code from the FFmpeg integration module to reduce maintenance surface before Phase 3 work begins.

### Removed

- **Dead `execute_command()` Bridge Function**
  - Removed `execute_command()` function and `CommandExecutionError` class from `stoat_ferret.ffmpeg.integration`
  - Removed exports from `stoat_ferret.ffmpeg` package `__init__.py`
  - Deleted `tests/test_integration.py` (13 tests covering only the removed function)
  - Zero production callers — `ThumbnailService` calls `executor.run()` directly
  - **Re-add trigger:** Phase 3 Composition Engine or any future render/export endpoint needing Rust command building (LRN-029)

### Changed

- N/A

### Fixed

- N/A

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
