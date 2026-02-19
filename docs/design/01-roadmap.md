# stoat-and-ferret - Implementation Roadmap

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Executive Summary

This roadmap outlines the phased implementation of an AI-driven video editing system designed for programmatic control via REST API. The system uses a **hybrid Python/Rust architecture**: Python (FastAPI) for the API layer enabling rapid iteration and AI discoverability, with Rust providing high-performance compute cores for video processing operations.

**Target User:** Solo developer building a custom video library, player, and editor from scratch with native AI integration.

**Quality Philosophy:** Quality is not a phase - it's a property of every line of code. Testability, observability, operability, and security are built into the foundation, not bolted on later.

**Performance Philosophy:** Performance-critical paths are implemented in Rust, exposed via PyO3 bindings, providing native-code speed with Python's ergonomics.

---

## Hybrid Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Python Layer (FastAPI)                           │
│  • REST API with automatic OpenAPI generation                            │
│  • AI-discoverable endpoints with rich schemas                           │
│  • Request validation, middleware, health checks                         │
│  • Orchestration and workflow management                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                               PyO3 bindings
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                         Rust Core Library                                │
│  • Filter chain builder (zero-copy command generation)                   │
│  • Timeline calculations (pure functions, deterministic)                 │
│  • Render coordinator (parallel processing, resource management)         │
│  • FFmpeg command builder (validated, safe construction)                 │
│  • Input sanitization (compile-time guarantees)                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation + Rust Core

**Objective:** Establish Python API infrastructure AND Rust performance core, with quality infrastructure from day one. GUI begins as an operations dashboard for visibility into system health and library management.

### Milestone 1.1: Project Setup & Quality Foundation
- [ ] Initialize Python project with modern tooling (uv, ruff, pytest, mypy)
- [ ] Initialize Rust workspace with maturin for PyO3 integration
- [ ] Set up hybrid build system (Python + Rust compilation)
- [ ] Configure structured logging with correlation ID support
- [ ] Set up Prometheus metrics collection (/metrics endpoint)
- [ ] Create health check endpoints (/health/live, /health/ready)
- [ ] Configure externalized settings (pydantic-settings)
- [ ] Set up test infrastructure with fixtures for both Python and Rust

### Milestone 1.2: Rust Core - Timeline Math & Validation
- [ ] Implement timeline position calculations in Rust (pure functions)
- [ ] Build clip validation logic with comprehensive error messages
- [ ] Create time range arithmetic (overlap detection, gap calculation)
- [ ] Implement project duration calculations
- [ ] Write Rust unit tests with proptest for property-based testing
- [ ] Expose via PyO3 with Python type stubs (.pyi files)

### Milestone 1.3: Rust Core - FFmpeg Command Builder
- [ ] Implement FFmpeg command builder with type-safe construction
- [ ] Create filter chain builder (concat, scale, pad, format)
- [ ] Build input sanitization module (text escaping, path validation)
- [ ] Implement encoding preset builder with validation
- [ ] Write contract tests verifying generated commands work with real FFmpeg
- [ ] Expose via PyO3 with ergonomic Python API

### Milestone 1.4: Database & Storage (Python Layer)
- [ ] Set up SQLite database with schema for videos, metadata, thumbnails
- [ ] Implement repository pattern with injectable storage interfaces
- [ ] Create in-memory storage implementation for testing
- [ ] Add database migration support with rollback capability
- [ ] Implement audit logging for data modifications

### Milestone 1.5: FFmpeg Integration (Observable, Testable)
- [ ] Implement FFprobe wrapper with structured error handling (Python)
- [ ] Create FFmpeg executor protocol for dependency injection
- [ ] Build fake FFmpeg executor for unit testing
- [ ] Integrate Rust command builder with Python executor
- [ ] Add FFmpeg command logging for transparency
- [ ] Add FFmpeg process metrics (active count, duration)

### Milestone 1.6: Library Management API (Full Quality Stack)
- [ ] Implement REST API framework (FastAPI)
- [ ] Add request correlation ID middleware
- [ ] Add metrics middleware for all endpoints
- [ ] Create `/videos` endpoints with structured error responses
- [ ] Build `/scan` endpoint with progress reporting
- [ ] Implement `/search` endpoint with FTS5 full-text search
- [ ] Add graceful shutdown handling

### Milestone 1.7: Basic Clip Model & Concatenation
- [ ] Design clip data model (source, in/out points, metadata)
- [ ] Use Rust timeline math for all calculations
- [ ] Create basic concat operation using Rust command builder
- [ ] Build `/clips` API endpoints

### Milestone 1.8: Black Box Testing Infrastructure
- [ ] Create recording test double catalog (see 07-quality-architecture.md):
  - [ ] `RecordingFFmpegExecutor` - captures commands for verification
  - [ ] `InMemoryProjectStorage` - fast, isolated storage
  - [ ] `InMemoryJobQueue` - synchronous for deterministic tests
  - [ ] `NullPreviewEngine` - for CI without libmpv
- [ ] Implement application test wiring via `create_app()` dependency injection
- [ ] Build fixture factory with builder pattern for test projects
- [ ] Create contract tests verifying fakes match real implementations
- [ ] Establish black box test scenario catalog:
  - [ ] Core workflow: scan → project → clips → effects → render
  - [ ] Error handling: validation errors, FFmpeg failures
  - [ ] WebSocket: progress updates, connection lifecycle
- [ ] Configure pytest fixtures for black box test harness

### Milestone 1.9: Quality Verification
- [ ] Unit tests for all Rust pure functions (>90% coverage)
- [ ] Python integration tests for API endpoints
- [ ] **Black box integration tests for complete workflows**
- [ ] Contract tests for FFmpeg command generation
- [ ] **Contract tests verifying test doubles match real implementations**
- [ ] Security review of path handling (Rust sanitization)
- [ ] Benchmark Rust vs pure-Python implementation
- [ ] Documentation of all configuration options

### Milestone 1.10: GUI - Application Shell & Dashboard
- [ ] Set up React/Svelte project with Vite and Tailwind CSS
- [ ] Configure static file serving from FastAPI (`/gui/*`)
- [ ] Create application shell with navigation and status bar
- [ ] Build health status indicator component (green/yellow/red)
- [ ] Implement WebSocket endpoint (`/ws`) for real-time events
- [ ] Build dashboard panel with metrics cards and activity log
- [ ] Add real-time log viewer with correlation ID support

### Milestone 1.11: GUI - Library Browser
- [ ] Build video grid component with thumbnail display
- [ ] Implement search bar with debounced FTS5 query
- [ ] Add sort (date, name, duration) and filter controls
- [ ] Create scan directory modal with progress indicator
- [ ] Add video detail view with metadata display
- [ ] Implement pagination or virtual scrolling for large libraries

### Milestone 1.12: GUI - Project Manager
- [ ] Build project list component with creation date and stats
- [ ] Create "New Project" modal with output settings
- [ ] Implement project details view with clip list
- [ ] Display timeline positions calculated by Rust core
- [ ] Add project open/delete actions

### Deliverables
- Working library scanner that processes video directories
- REST API for library CRUD operations with full observability
- Basic clip concatenation capability
- SQLite database with video metadata and search
- **Rust Core:**
  - Timeline math module with PyO3 bindings
  - FFmpeg command builder with validation
  - Input sanitization module
- **Quality Infrastructure:**
  - Prometheus metrics endpoint
  - Health check endpoints (liveness + readiness)
  - Structured JSON logging with correlation IDs
  - Externalized configuration
  - Test suite with >80% coverage (Python + Rust)
  - Graceful shutdown handling
- **Black Box Testing Harness:**
  - Recording test doubles (FFmpegExecutor, Storage, JobQueue)
  - Fixture factory with builder pattern
  - Contract tests for test double compliance
  - Core workflow integration test scenarios
  - Application wiring supporting test injection
- **GUI:**
  - Operations dashboard with health status and metrics
  - Library browser with search and thumbnails
  - Project list with basic clip management
  - WebSocket real-time event streaming

---

## Phase 2: Effects Engine (Rust-Powered)

**Objective:** Implement core video effects with Rust filter chain builder, maintaining pure functions and comprehensive testing. GUI adds interactive Effect Workshop for discovery and configuration.

### Milestone 2.1: Rust Core - Filter Expression Engine
- [x] Implement FFmpeg filter expression parser/builder in Rust
- [x] Create filter graph validation (input/output pad matching)
- [x] Build filter composition system (chaining, branching)
- [x] Implement expression builder for enable/alpha/time expressions
- [x] Add comprehensive property-based tests (proptest)

### Milestone 2.2: Text Overlay System (Rust + Python)
- [x] Implement drawtext filter builder in Rust (pure function)
- [x] Add text sanitization with compile-time safety guarantees
- [x] Create alpha animation expressions for fade in/out
- [x] Build text styling options (position, color, shadow, box)
- [x] Python API for effect discovery with AI hints
- [x] Contract tests: generated filters produce valid FFmpeg commands

### Milestone 2.3: Speed Control (Rust Core)
- [x] Implement setpts filter for video speed (pure function, Rust)
- [x] Build atempo chain generator for audio speed (handle >2x speeds)
- [x] Create speed calculation functions with exhaustive unit tests
- [x] Handle audio removal option for extreme speeds
- [x] Validation with helpful error messages (Rust Error types)

### Milestone 2.4: Audio Mixing
- [ ] Implement amix filter builder (Rust)
- [ ] Add volume level controls per track
- [ ] Create audio fade in/out capability
- [ ] Build audio ducking patterns
- [ ] Test with edge cases (silence, clipping, format mismatches)

### Milestone 2.5: Transitions
- [ ] Implement fade transitions (fade in/out/crossfade) in Rust
- [ ] Add xfade filter support for transition effects
- [ ] Create transition parameter validation
- [ ] Build `/effects/transition` API endpoint (Python)

### Milestone 2.6: Effect Registry & Discovery
- [x] Design effect registry with JSON schema validation
- [x] Implement effect parameter validation as Rust functions
- [x] Create effect builder protocol for dependency injection
- [ ] Add effect metrics (effect_applications_total by type)
- [x] Build `/effects` discovery endpoint with AI hints

### Milestone 2.7: Quality Verification
- [ ] Rust unit tests for all filter builders (>95% coverage)
- [ ] Property-based tests for edge cases (proptest)
- [ ] Contract tests with real FFmpeg execution
- [ ] Performance benchmarks (Rust vs baseline)
- [ ] Security review of text input sanitization

### Milestone 2.8: GUI - Effect Discovery UI
- [ ] Build effect catalog component from `/effects` endpoint
- [ ] Create parameter form generator from JSON schema
- [ ] Display AI hints as contextual tooltips
- [ ] Implement live filter string preview (shows Rust-generated FFmpeg filter)
- [ ] Add parameter validation with inline error display

### Milestone 2.9: GUI - Effect Builder
- [ ] Create effect configuration panel with all parameters
- [ ] Build "Apply to Clip" workflow with clip selector
- [ ] Show effect stack visualization per clip
- [ ] Add effect preview thumbnail (static frame with effect applied)
- [ ] Implement effect editing and removal

### Deliverables
- Text overlay with timing and animation
- Variable speed control with audio handling
- Multi-track audio mixing
- Fade transitions between clips
- **Rust Core:**
  - Filter expression engine
  - Text sanitization module
  - Speed calculation module
  - Audio mixing filter builder
- **Quality:**
  - All filter builders as pure, testable Rust functions
  - Comprehensive test coverage including property-based tests
  - Effect usage metrics
  - Security-hardened text input handling
  - Performance benchmarks showing Rust speedup
- **GUI:**
  - Effect Workshop panel with discovery and configuration
  - Live filter preview showing generated FFmpeg commands
  - Effect stack management per clip

---

## Phase 3: Composition Engine (Rust Performance Layer)

**Objective:** Enable multi-stream layouts and complex compositions with Rust-powered computation. GUI introduces visual Timeline Canvas for multi-track editing.

### Milestone 3.1: Rust Core - Layout Calculations
- [ ] Implement layout math in Rust (positions, scales, coordinates)
- [ ] Build padding/alignment calculations
- [ ] Create resolution normalization functions
- [ ] Add aspect ratio preservation calculations

### Milestone 3.2: Picture-in-Picture
- [ ] Implement overlay filter with positioning (Rust)
- [ ] Add scale calculations for PIP sizing
- [ ] Create corner presets (top-left, bottom-right, etc.)
- [ ] Handle timing synchronization with validation
- [ ] Build `/compose/pip` API endpoint with metrics

### Milestone 3.3: Split Screen Layouts
- [ ] Implement hstack/vstack builders (Rust)
- [ ] Build overlay-based positioning for custom layouts
- [ ] Add border/padding options with validation
- [ ] Create layout presets (2x2, 3x3, side-by-side)
- [ ] Unit tests for all layout calculations

### Milestone 3.4: Layer System
- [ ] Design track-based timeline model (JSON schema)
- [ ] Implement Z-ordering for overlapping elements (Rust)
- [ ] Create timeline rendering engine with tracing spans
- [ ] Build project serialization/deserialization
- [ ] Implement project versioning for recovery

### Milestone 3.5: Project Persistence (Reliable)
- [ ] Implement atomic project save with backup
- [ ] Add project version history (last N versions)
- [ ] Create project restore from previous version
- [ ] Add project integrity validation on load
- [ ] Audit log for all project modifications

### Milestone 3.6: Quality Verification
- [ ] Integration tests for composition workflows
- [ ] Test recovery from corrupted project files
- [ ] Performance tests for complex compositions
- [ ] Benchmark multi-track rendering (Rust optimization impact)

### Milestone 3.7: GUI - Visual Timeline
- [ ] Build horizontal timeline component with time ruler
- [ ] Implement multi-track rendering (video, text, audio tracks)
- [ ] Add clip visualization with duration and thumbnails
- [ ] Create clip selection with properties panel
- [ ] Implement zoom controls and horizontal scrolling
- [ ] Add playhead position indicator

### Milestone 3.8: GUI - Composition Preview
- [ ] Add layout preview canvas for PIP positioning
- [ ] Show split-screen layout visualization
- [ ] Implement layout preset selector (2x2, side-by-side, etc.)
- [ ] Display Z-ordering (layer stacking visualization)
- [ ] Add drag handles for layout adjustment (future-ready)

### Deliverables
- PIP with flexible positioning
- Multi-video grid layouts
- Track-based timeline with layer ordering
- Project save/load capability with versioning
- **Rust Core:**
  - Layout calculation module
  - Z-ordering engine
  - Complex filter graph generator
- **Quality:**
  - Project versioning with recovery capability
  - Atomic saves preventing data corruption
  - Audit trail of project changes
  - Comprehensive composition test coverage
- **GUI:**
  - Visual timeline canvas with multi-track support
  - Composition layout preview
  - Clip selection and properties editing

---

## Phase 4: Preview & Playback (Observable, Operable)

**Objective:** Real-time preview with proxy workflow, full observability of playback performance. GUI adds integrated preview player and **AI Theater Mode** for full-screen AI-streamed viewing.

### Milestone 4.1: Proxy Generation (Background Jobs)
- [ ] Implement proxy transcoding (720p for 4K, 540p for 1080p)
- [ ] Create background proxy job queue with metrics
- [ ] Add proxy/original file association in database
- [ ] Build automatic proxy switching based on content
- [ ] Add proxy generation progress metrics and logs

### Milestone 4.2: Preview Server
- [ ] Integrate libmpv for playback
- [ ] Implement seek/scrub capability
- [ ] Create timeline position synchronization
- [ ] Add effect preview pipeline
- [ ] Add preview performance metrics (frame drops, latency)

### Milestone 4.3: Rust Core - Preview Optimization
- [ ] Implement preview filter simplification (reduce quality for speed)
- [ ] Build frame caching strategy calculations
- [ ] Create preview-specific filter variants
- [ ] Optimize filter chain for real-time playback

### Milestone 4.4: Preview API (Operable)
- [ ] Build `/preview/start` endpoint with timeline position
- [ ] Create `/preview/seek` for scrubbing
- [ ] Implement frame extraction for thumbnails
- [ ] Add waveform generation for audio
- [ ] Health check for preview server readiness

### Milestone 4.5: Quality Verification
- [ ] Performance tests for preview latency
- [ ] Test proxy generation under load
- [ ] Test graceful degradation when preview unavailable
- [ ] Benchmark preview frame rate with complex effects

### Milestone 4.6: GUI - Embedded Preview Player
- [ ] Integrate HLS.js video player component
- [ ] Build player controls (play, pause, seek, volume)
- [ ] Synchronize playback position with timeline component
- [ ] Add preview quality indicator (proxy vs original)
- [ ] Implement frame-accurate seeking with timeline scrubbing
- [ ] Show buffer status and latency metrics

### Milestone 4.7: GUI - AI Theater Mode (Full-Screen)
- [ ] Implement browser full-screen mode toggle
- [ ] Build auto-hiding HUD overlay (shows on mouse movement)
- [ ] Create AI action display component (real-time WebSocket events)
- [ ] Add progress bar with ETA and current operation
- [ ] Implement keyboard shortcuts (Space, Escape, F, M, arrows)
- [ ] Add ambient status indicators (optional sounds)
- [ ] Create Theater Mode entry button in navigation
- [ ] Support both editing preview and render viewing modes

### Deliverables
- Proxy workflow for smooth preview
- libmpv-based player integration
- Preview API for frontend integration
- Seek and scrub capability
- **Quality:**
  - Preview performance metrics (frame rate, latency)
  - Background job observability
  - Graceful degradation when proxy unavailable
  - Performance benchmarks documented
- **GUI:**
  - Integrated preview player with timeline sync
  - **AI Theater Mode** for immersive full-screen viewing
  - Real-time AI action display during playback
  - Keyboard shortcuts for hands-free control

---

## Phase 5: Export & Production (Rust Render Coordinator)

**Objective:** High-quality rendering with hardware acceleration, Rust-powered render coordination. GUI adds Render Control Center for job management and progress monitoring.

### Milestone 5.1: Rust Core - Render Coordinator
- [ ] Implement render job coordinator in Rust
- [ ] Build parallel segment rendering strategy
- [ ] Create resource management (memory, CPU limits)
- [ ] Implement progress calculation with ETA estimation
- [ ] Add render checkpoint system for recovery

### Milestone 5.2: Render Engine (Resilient)
- [ ] Build complete FFmpeg command generator from timeline (Rust)
- [ ] Implement output format options (MP4, WebM, ProRes)
- [ ] Add resolution/bitrate presets
- [ ] Create two-pass encoding option
- [ ] Implement render timeout with graceful termination
- [ ] Add render retry logic for transient failures

### Milestone 5.3: Hardware Acceleration (Fallback Chain)
- [ ] Detect available encoders (NVENC, VAAPI, VideoToolbox) - Rust
- [ ] Implement encoder selection logic with logging
- [ ] Add GPU decode support where available
- [ ] Create fallback chain: HW encoder -> SW encoder -> error
- [ ] Log hardware acceleration detection results

### Milestone 5.4: Job Queue (Observable, Recoverable)
- [ ] Implement async job processing (arq/Redis)
- [ ] Add progress tracking with percentage and ETA
- [ ] Create job status polling endpoint
- [ ] Implement webhook callbacks for completion
- [ ] Build job cancellation capability
- [ ] Add job recovery on service restart
- [ ] Metrics: queue depth, job duration, success rate

### Milestone 5.5: Export API
- [ ] Create `/render/start` endpoint with validation
- [ ] Build `/render/status/{job_id}` for polling
- [ ] Implement `/render/cancel/{job_id}`
- [ ] Add `/render/queue` for queue management
- [ ] Structured errors with recovery suggestions

### Milestone 5.6: Operational Excellence
- [ ] Disk space check before starting render (Rust)
- [ ] Resource limits (max concurrent renders)
- [ ] Rate limiting for render requests
- [ ] Cleanup of old render artifacts
- [ ] Alert thresholds for queue depth

### Milestone 5.7: Quality Verification
- [ ] Integration tests for full render workflow
- [ ] Test render recovery after crash
- [ ] Test fallback chain under various conditions
- [ ] Load test for concurrent renders
- [ ] Benchmark render speed (Rust coordinator impact)

### Milestone 5.8: GUI - Render Queue Panel
- [ ] Build job list component with status indicators
- [ ] Add progress bars with ETA and frame count
- [ ] Implement cancel and remove job actions
- [ ] Show completed jobs history with timestamps
- [ ] Add "Start Render" button with project selector
- [ ] Display FFmpeg command preview (for debugging)

### Milestone 5.9: GUI - Render Settings
- [ ] Create quality preset selector (draft/medium/high/lossless)
- [ ] Add output format options (MP4, WebM, ProRes)
- [ ] Show hardware acceleration status and selection
- [ ] Implement disk space check with warning display
- [ ] Add output path selector with validation

### Deliverables
- Full timeline to video rendering
- Hardware-accelerated encoding with fallback
- Async job queue with progress tracking
- Webhook notifications
- **Rust Core:**
  - Render coordinator with parallel processing
  - Hardware detection module
  - Resource management system
  - Progress/ETA calculation
- **Quality:**
  - Automatic retry for transient failures
  - Job recovery on restart
  - Resource protection (disk, CPU limits)
  - Full render observability (metrics, logs, traces)
  - Operational runbook documentation
- **GUI:**
  - Render Control Center with job queue management
  - Progress monitoring with ETA display
  - Quality and format settings interface

---

## Phase 6: Deployability & AI Integration

**Objective:** Production deployment readiness, container support, and AI integration refinement. GUI matures into a unified workspace with AI integration panel.

### Milestone 6.1: Container Deployment
- [ ] Create production Dockerfile with multi-stage build (Python + Rust)
- [ ] Build maturin wheel in container for distribution
- [ ] Implement startup health checks
- [ ] Create smoke test suite for deployment verification
- [ ] Document deployment procedures

### Milestone 6.2: Deployment Safety
- [ ] Implement database migration safety (backup before migrate)
- [ ] Create rollback procedures documentation
- [ ] Add version endpoint for deployment tracking (includes Rust core version)
- [ ] Implement feature flags for gradual rollout
- [ ] Synthetic monitoring configuration

### Milestone 6.3: AI Integration Refinement
- [ ] Enhance effect discovery with richer AI hints
- [ ] Add schema introspection for AI parameter learning
- [ ] Create batch operation endpoints
- [ ] Document AI integration patterns
- [ ] Example prompts for AI agents

### Milestone 6.4: Documentation & Knowledge Transfer
- [ ] Generate complete OpenAPI specification
- [ ] Document Rust core API (rustdoc)
- [ ] Create API usage examples
- [ ] Document common workflows
- [ ] Write operational runbook
- [ ] Create troubleshooting guide

### Milestone 6.5: Final Quality Gate
- [ ] Complete security review (Python + Rust)
- [ ] Performance benchmark suite
- [ ] Load testing results documented
- [ ] All SLI targets met
- [ ] Quality metrics dashboard

### Milestone 6.6: GUI - Unified Workspace
- [ ] Implement dockable/resizable panel layout
- [ ] Add workspace layout presets (edit, review, render)
- [ ] Create settings panel (theme, shortcuts, preferences)
- [ ] Build keyboard shortcut reference/help overlay
- [ ] Add panel visibility toggles

### Milestone 6.7: GUI - AI Integration Panel
- [ ] Create chat-like AI command interface
- [ ] Display AI action history with timestamps
- [ ] Implement "Undo AI Action" functionality
- [ ] Show suggested operations based on context
- [ ] Add natural language command input

### Milestone 6.8: GUI - Final Polish
- [ ] Accessibility audit and fixes (WCAG AA)
- [ ] E2E tests for critical workflows (Playwright)
- [ ] Performance optimization (bundle size, virtual scrolling)
- [ ] Browser compatibility testing
- [ ] Documentation for GUI usage

### Deliverables
- Container-ready deployment
- Complete deployment documentation
- AI-friendly API discovery
- Operational runbook
- **Quality:**
  - Smoke tests for deployment verification
  - Rollback procedures documented
  - Version tracking for deployments (including Rust core)
  - Security review completed
- **GUI:**
  - Unified workspace with dockable panels
  - AI Integration panel for natural language commands
  - Fully accessible (WCAG AA compliant)
  - Complete E2E test coverage

---

## Success Criteria

### Phase Completion Gates

| Phase | Functional Metrics | Quality Metrics | Performance Metrics | GUI Metrics |
|-------|-------------------|-----------------|---------------------|-------------|
| Phase 1 | Scan directory, search videos, concatenate clips | Metrics live, >80% coverage, **black box test harness operational**, structured logging | Rust core baseline benchmarks | Dashboard, library browser, project list functional |
| Phase 2 | Apply text, speed, audio, transitions via API | All filter builders tested, **black box tests for effect workflows**, security review | Filter generation <1ms | Effect Workshop with live filter preview |
| Phase 3 | Create PIP, split-screen, multi-track timeline | Project versioning works, **black box tests for composition**, audit logging | Complex layouts <10ms | Visual timeline with multi-track support |
| Phase 4 | Preview timeline with scrubbing | Preview metrics collected, **WebSocket tests passing**, graceful degradation | Preview >30fps at 1080p | Embedded player, **AI Theater Mode** functional |
| Phase 5 | Render complete timeline with HW acceleration | Job recovery tested, **black box render workflow tests**, fallback works | Render >1x realtime | Render queue with progress monitoring |
| Phase 6 | API is self-documenting and AI-discoverable | Smoke tests pass, **full black box coverage**, security review done | Deploy <5min | Unified workspace, AI panel, WCAG AA compliant |

### Quality Gates (Every Phase)

**Testability:**
- [ ] Rust unit test coverage >90%
- [ ] Python test coverage >80%
- [ ] Integration tests for each API endpoint
- [ ] Contract tests for FFmpeg command generation
- [ ] Property-based tests for Rust pure functions
- [ ] **Black box integration tests for complete workflows**
- [ ] **Contract tests verifying test doubles match real implementations**
- [ ] **Test harness uses real Rust core, recording fakes for external systems**

**Observability:**
- [ ] Metrics endpoint returning data
- [ ] Health checks all passing
- [ ] Structured logs with correlation IDs
- [ ] Key business metrics tracked

**Operability:**
- [ ] Configuration externalized
- [ ] Graceful shutdown working
- [ ] Health checks for dependencies

**Debuggability:**
- [ ] Structured error responses
- [ ] Error context preserved
- [ ] Audit logging for key operations

**Security:**
- [ ] Path validation tested (Rust)
- [ ] Input sanitization verified (Rust)
- [ ] No shell injection possible

### Service Level Indicators (SLIs)

| Metric | Target | Phase Introduced |
|--------|--------|------------------|
| API availability | >99.9% | Phase 1 |
| API latency (p95) | <200ms | Phase 1 |
| Render success rate | >95% | Phase 5 |
| Error rate | <1% | Phase 1 |
| Health check latency | <50ms | Phase 1 |
| Filter generation time | <5ms | Phase 2 |
| Render throughput | >1x realtime | Phase 5 |

---

## Risk Mitigation

| Risk | Mitigation | Quality Attribute |
|------|------------|-------------------|
| FFmpeg complexity | Rust command builder with validation, contract tests | Testability |
| Filter bugs in production | Pure Rust functions, property-based tests | Testability |
| PyO3 integration issues | Comprehensive integration tests, type stubs | Testability |
| Production debugging | Structured logging, correlation IDs, tracing | Observability, Debuggability |
| Configuration drift | Externalized config, environment parity | Operability |
| Service instability | Health checks, graceful shutdown | Operability, Reliability |
| Render failures | Retry logic, job recovery, fallback chain | Reliability |
| Security vulnerabilities | Rust sanitization, path validation, audit logs | Security |
| Preview performance | Proxy workflow, performance metrics | Observability |
| Deployment issues | Smoke tests, rollback capability | Deployability |
| Scope creep | Strict phase boundaries, quality gates | Maintainability |
| Rust learning curve | Incremental adoption, Python fallbacks available | Maintainability |

---

## Dependencies

### Core
- FFmpeg 5.0+ with libx264, libx265, libvpx
- Python 3.11+
- Rust 1.70+ (stable)
- SQLite 3.35+ (for FTS5)
- Redis 6.0+ (for job queue)

### Rust Build Tools
- maturin 1.0+ (PyO3 build tool)
- cargo (Rust package manager)

### Quality Infrastructure
- structlog (structured logging)
- prometheus-client (metrics)
- opentelemetry-sdk (tracing, optional)
- pytest, pytest-asyncio (Python testing)
- proptest (Rust property-based testing)
- ruff, mypy (Python code quality)
- clippy, rustfmt (Rust code quality)

### GUI / Frontend
- Node.js 18+ (build tooling)
- React 18+ or Svelte 4+ (UI framework)
- Vite 5+ (build tool)
- Tailwind CSS 3+ (styling)
- HLS.js (video streaming)
- Vitest (frontend unit testing)
- Playwright (E2E testing)

### Preview (Optional)
- libmpv (for preview)

### Hardware Acceleration (Optional)
- NVIDIA GPU (NVENC)
- Intel iGPU (VAAPI/QSV)
- AMD GPU (VAAPI)

---

## Quality Architecture Reference

See **07-quality-architecture.md** for detailed implementation patterns:
- Testability: Dependency injection, pure functions (Rust), test doubles
- **Black Box Testing**: Recording fakes, fixture factories, contract tests, integration scenarios
- Observability: Metrics, logs, traces implementation
- Operability: Configuration, resilience, graceful shutdown
- Debuggability: Structured errors, audit trails
- Maintainability: Module structure, explicit dependencies, Rust/Python boundaries
- Deployability: Containers, smoke tests, rollback
- Reliability: Retries, recovery, data integrity
- Security: Rust validation, sanitization, audit logging

---

## GUI Architecture Reference

See **08-gui-architecture.md** for detailed GUI implementation:
- Technology stack: React/Svelte, Vite, Tailwind CSS, WebSocket
- Progressive enhancement: Dashboard → Effect Workshop → Timeline → Preview → Render
- AI Theater Mode: Full-screen immersive viewing of AI-streamed content
- Component structure: Panels, hooks, stores, API clients
- Build and deployment: Vite build, static file serving from FastAPI

---

## Hybrid Architecture Benefits

| Benefit | Python Contribution | Rust Contribution |
|---------|--------------------|--------------------|
| **AI Discoverability** | FastAPI automatic OpenAPI, rich schemas | - |
| **Rapid Iteration** | Quick API changes, hot reload | - |
| **Type Safety** | Pydantic validation | Compile-time guarantees |
| **Performance** | - | Zero-cost abstractions, no GC |
| **Memory Safety** | - | Ownership system, no data races |
| **Testability** | pytest, fixtures | proptest, exhaustive checking |
| **Concurrency** | asyncio for I/O | Rayon for CPU parallelism |

---

## Next Steps

1. Review and approve roadmap
2. Review quality architecture document
3. Review GUI architecture document
4. Set up development environment (Python + Rust + Node.js toolchain)
5. Initialize Rust workspace with maturin
6. Initialize GUI project with Vite
7. Begin Phase 1, Milestone 1.1 (includes Rust core setup)
8. Begin Phase 1, Milestone 1.9 (GUI shell) in parallel
9. Establish weekly progress reviews with quality gate verification
