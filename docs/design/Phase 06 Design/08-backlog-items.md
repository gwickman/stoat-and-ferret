# Phase 6: Backlog Items

## Sizing Rules

Per exploration prompt: Documentation-only = Small; Single focused code change = Small; New feature with tests = Medium; Complex cross-cutting feature = Large.

## Phase 5 Dependencies

- BL-251 (v036): ThumbnailService/WaveformService wired to SQLite — M6.7 persistence gap already closed
- BL-252 (v035): Format-encoder validation on preview — BL-258 extends to render submission

## Phase 5 Residuals (carried into v037)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-254 | Enrich render WebSocket progress with frame count and encoder metadata | S | Backend emits frame_count, fps, encoder_name, encoder_type in render progress events | 1. Progress events include all four fields 2. Theater Mode displays encoder info 3. Fields present in WS event schema docs 4. Smoke test verifies field presence |
| BL-255 | Implement render.frame_available streaming to Theater Mode at 540p | M | Render executor intercepts FFmpeg output frames, scales to 540p, emits render.frame_available WS events throttled at 2/s | 1. Theater Mode displays latest rendered frame 2. Throttle enforced at <=2 frames/s 3. Preview quality capped at 540p 4. Smoke test for event delivery 5. No memory leak on long renders |
| BL-258 | Extend format-encoder validation to POST /render submission | S | Render submission endpoint validates format-encoder compatibility (same check as render_preview) | 1. Invalid combo returns 422 with INCOMPATIBLE_FORMAT_ENCODER 2. Smoke test for rejection 3. GUI surfaces error on StartRenderModal |

## New Backlog Items

### Theme 1: Container & Deployment (M6.1)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-301 | Multi-stage Dockerfile for production deployment | L | Dockerfile with builder stage (Rust + maturin wheel) and runtime stage (Python + wheel install). Non-root user, health check instruction. | 1. `docker build` produces working image 2. Image runs on linux/amd64 3. Non-root user in runtime stage 4. HEALTHCHECK instruction present 5. Image size < 1GB |
| BL-302 | Deployment smoke test script | S | Shell script that starts container, waits for healthy, hits /version and /health/ready, exits with pass/fail | 1. Script exits 0 on healthy container 2. Script exits 1 on failure with diagnostic output 3. Runs in CI 4. Completes < 60s |
| BL-303 | Docker Compose for local dev/test | S | docker-compose.yml with app service, volume mounts for data/, port mapping | 1. `docker compose up` starts working app 2. Data persists across restarts 3. Hot-reload not required (production-like) |
| BL-304 | Container startup health checks | M | Application verifies database connectivity, Rust core availability, and file system access on startup before accepting traffic | 1. /health/ready returns false until all checks pass 2. Startup fails fast on database error 3. Structured log event on startup completion 4. Startup < 10s on clean state |

### Theme 2: Deployment Safety (M6.2)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-305 | Database migration safety with backup | M | Migration runner creates SQLite backup before applying, records in migration_history table with rollback SQL | 1. Backup created before each migration 2. migration_history row with rollback_sql 3. Rollback restores previous state 4. Contract test for backup/restore cycle |
| BL-306 | Version endpoint with build metadata | S | GET /api/v1/version returns app_version, core_version, build_timestamp, git_sha, python_version, database_version | 1. Endpoint returns all fields 2. core_version from Rust VersionInfo 3. Smoke test validates response schema 4. Dashboard shows version card |
| BL-307 | Feature flags with environment variables | M | FeatureFlags model reads from env vars at startup. GET /api/v1/flags endpoint. Feature flag state logged at startup. | 1. Flags read from STOAT_* env vars 2. /flags endpoint returns current state 3. Startup log includes all flag values 4. feature_flag_log table populated 5. Smoke test for flags endpoint |
| BL-308 | Synthetic monitoring background task | S | When enabled, background task runs health/state/version checks every 60s with Prometheus metrics | 1. Checks run on configured interval 2. Prometheus counters/histograms emitted 3. Disabled by default 4. No impact on normal operation |

### Theme 3: AI Integration & Schema Discovery (M6.3)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-309 | Enhanced effect discovery with AI hints | M | Rust ParameterSchema struct with ai_hint field. Effects endpoint returns enriched parameter schemas with ai_summary and example_prompt. | 1. All effects have parameter schemas 2. ai_hint present on all parameters 3. ai_summary and example_prompt on each effect 4. Proptest: all effects have valid schemas 5. Smoke test for enriched response |
| BL-310 | Schema introspection endpoint | M | GET /api/v1/schema/{resource} returns JSON Schema for project, clip, timeline, render_job, effect, video | 1. Valid JSON Schema for each resource 2. 404 for unknown resource 3. Schemas match actual Pydantic models 4. Smoke test for each resource |
| BL-311 | AI integration pattern documentation | S | Document AI discovery patterns: how to use /effects with hints, /schema for learning, batch for multi-job workflows | 1. Markdown doc in docs/manual/ 2. Covers discovery, learning, execution patterns 3. Includes curl examples 4. Referenced from OpenAPI description |

### Theme 4: API Testability & Agent Infrastructure (M6.7)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-312 | WebSocket event ID and timestamp on all events | M | Every WS event includes monotonic event_id and ISO timestamp. Event IDs monotonic per job. | 1. All events have event_id and timestamp 2. IDs monotonically increasing per job 3. Heartbeat events included (but excluded from replay) 4. Smoke test validates fields |
| BL-313 | WebSocket replay buffer with reconnection support | L | Bounded ring buffer (1000 events, 5-min TTL). Clients connect with ?last_event_id to receive replay. | 1. Replay delivers missed events in order 2. Buffer enforces size limit and TTL 3. Gap warning when requested event expired 4. Contract test for buffer bounds 5. Prometheus gauge for buffer size |
| BL-314 | System state snapshot endpoint | M | GET /api/v1/system/state returns denormalised view of projects, jobs, previews, queue status | 1. Response includes all sections 2. Empty state returns valid response 3. Reflects real-time job status 4. < 500ms with 100 projects 5. Smoke test and benchmark |
| BL-315 | Test fixture seed endpoint | M | POST /api/v1/testing/seed creates fixtures, DELETE tears down. Config-guarded by STOAT_TESTING_MODE. | 1. Creates projects/videos/jobs per request 2. 404 when testing_mode=false 3. DELETE removes all seeded data 4. Smoke test for create and teardown 5. Seeded data distinguishable from real data |
| BL-316 | Long-poll wait-for-completion pattern | M | ?wait=true&timeout=N on job status endpoints. Returns immediately for terminal state, waits otherwise. | 1. Terminal jobs return immediately 2. Pending jobs wait until transition or timeout 3. Timeout returns current status (not error) 4. Works on render, batch, and generic job endpoints 5. Smoke test for all three behaviors |
| BL-317 | OpenAPI state machine documentation | S | Annotate operation transitions (e.g., render: queued→running→completed/failed) in OpenAPI descriptions | 1. All stateful endpoints document transitions 2. Terminal states clearly marked 3. WebSocket event types documented per transition 4. Reviewable in Swagger UI |

### Theme 5: Documentation & Agent Support (M6.4, M6.8)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-318 | Complete OpenAPI specification | S | Review all endpoints for complete request/response schemas, error codes, descriptions | 1. All endpoints have descriptions 2. All error codes documented 3. Example values on complex schemas 4. Validates with openapi-spec-validator |
| BL-319 | Rust core documentation (rustdoc) | S | Add doc comments to all public Rust functions and structs. Generate with `cargo doc`. | 1. `cargo doc` builds without warnings 2. All public items have doc comments 3. Examples in doc comments for key functions |
| BL-320 | API usage examples and common workflows | S | Markdown guide with curl examples for: library scan, project creation, effect apply, render, batch render | 1. Covers 5+ common workflows 2. All curl examples tested and working 3. Includes expected responses |
| BL-321 | Operational runbook and troubleshooting | S | Runbook covering startup, shutdown, backup, restore, common errors, performance tuning | 1. Covers all operational scenarios 2. Step-by-step procedures 3. Troubleshooting decision tree |
| BL-322 | Agent operator guide with canonical sequences | M | Compact AI-optimised reference. Canonical API sequences for discover→learn→execute. Expected event sequences per operation. | 1. Under 100 lines of essential content 2. Covers all major operations 3. Event sequences for render, scan, batch 4. References /schema and /effects endpoints |
| BL-323 | Prompt recipes and example scripts | S | Prompt recipes for common scenarios. Scripts: wait-for-render.py, dump-ws-events.py | 1. 5+ prompt recipes with expected outcomes 2. Scripts are executable and documented 3. wait-for-render uses long-poll pattern |
| BL-324 | WebSocket event vocabulary reference | S | Complete reference of all event types with fields, terminal states, and state transitions | 1. All 20+ event types documented 2. Terminal states marked 3. Transition diagrams for stateful events |

### Theme 6: Quality & Security Gate (M6.5)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-325 | Security review — Python API surface | M | Audit all endpoints for injection, auth boundaries, seed guard, input validation | 1. No SQL injection (parameterised queries verified) 2. Seed endpoint guard confirmed 3. No path traversal in file operations 4. Findings documented with severity |
| BL-326 | Security review — Rust core and dependencies | M | Audit unsafe blocks, panic paths, FFmpeg command sanitization. Run cargo audit + pip-audit. | 1. All unsafe blocks justified and reviewed 2. No panics reachable from Python 3. cargo audit clean 4. pip-audit clean or exceptions documented |
| BL-327 | Performance benchmark suite | M | Benchmark API latency, system state, WS replay, render throughput, container startup | 1. Benchmarks for 5+ scenarios 2. Baseline numbers recorded 3. CI-runnable benchmark suite 4. Results in Markdown table |
| BL-328 | Load testing with concurrent users | L | Load test with 50 concurrent API users, 100 WS connections, 10 batch renders | 1. P99 < 200ms for API under load 2. All WS events delivered under load 3. No OOM or crashes 4. Results documented |
| BL-329 | Quality metrics dashboard configuration | S | Prometheus/Grafana dashboard JSON for request latency, error rate, render throughput, WS health | 1. Dashboard importable into Grafana 2. Panels for all SLI metrics 3. Alert rules for SLO breaches |

### Theme 7: GUI Workspace & Final Polish (M6.6, M6.9)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| BL-330 | Dockable resizable panel layout with react-resizable-panels | L | Replace fixed Shell layout with CSS Grid + react-resizable-panels. Persist custom sizes in localStorage. | 1. Panels resizable by drag 2. Layout persists across reloads 3. Minimum panel sizes enforced 4. No regressions in existing pages 5. UAT J601 passes |
| BL-331 | Workspace layout presets (edit/review/render) | M | Three predefined panel configurations. Ctrl+1/2/3 shortcuts. PresetSelector in header. | 1. Three presets switch panel visibility and sizing 2. Keyboard shortcuts work 3. Custom overrides preserved per preset 4. UAT J601 covers preset switching |
| BL-332 | Settings panel with theme and shortcuts | M | Settings panel with theme selector, shortcut editor, preference toggles. Ctrl+, to open. | 1. Theme applies immediately 2. Shortcut rebinding persisted 3. Respects prefers-color-scheme 4. UAT J602 passes |
| BL-333 | Keyboard shortcut reference overlay | S | Modal overlay triggered by ? key listing all shortcuts grouped by context | 1. Shows all registered shortcuts 2. Grouped by context (global, page-specific) 3. Closes on Escape 4. Focus trapped in overlay |
| BL-334 | Batch panel GUI for submission and monitoring | M | BatchPanel and BatchJobList components. Tab in RenderPage alongside render queue. | 1. Submit batch from GUI 2. Progress bars per job 3. Cancel batch action 4. WebSocket live updates 5. UAT J603 passes |
| BL-335 | WCAG AA accessibility audit and fixes | L | Audit all pages. Fix focus indicators, ARIA labels, colour contrast, skip links, screen reader announcements. | 1. axe-core audit passes with 0 critical issues 2. All interactive elements have visible focus 3. Skip-to-content link present 4. Status changes announced via aria-live 5. UAT J604+J605 pass |
| BL-336 | E2E Playwright tests for critical workflows | L | Playwright tests for workspace, settings, batch, keyboard nav, accessibility, agent seed | 1. 6 new UAT journeys (J601–J606) 2. All journeys pass in CI 3. Covers happy path + key error cases |
| BL-337 | Bundle size and performance optimization | M | Analyse bundle with vite-bundle-analyzer. Code-split large pages. Virtual scrolling for long lists. | 1. Bundle < 500KB gzipped 2. Library page uses virtual scrolling 3. Lazy-loaded routes for all pages 4. Lighthouse performance score > 90 |
| BL-338 | Browser compatibility testing | S | Test on Chrome, Firefox, Safari (latest 2 versions). Document any browser-specific issues. | 1. All features work on target browsers 2. Browser support matrix documented 3. Any polyfills documented |

## Summary

| Category | Items | Small | Medium | Large |
|----------|-------|-------|--------|-------|
| Phase 5 Residuals | 3 | 2 | 1 | 0 |
| Theme 1: Container & Deployment | 4 | 2 | 1 | 1 |
| Theme 2: Deployment Safety | 4 | 2 | 2 | 0 |
| Theme 3: AI Integration | 3 | 1 | 2 | 0 |
| Theme 4: API Testability | 6 | 1 | 4 | 1 |
| Theme 5: Documentation | 7 | 5 | 2 | 0 |
| Theme 6: Quality & Security | 5 | 1 | 3 | 1 |
| Theme 7: GUI Workspace & Polish | 9 | 2 | 4 | 3 |
| **Total** | **41+3** | **16+2** | **19+1** | **6+0** |

**Grand total: 44 items (18 S, 20 M, 6 L)**

## Dependencies

- BL-312 (event IDs) must precede BL-313 (replay buffer)
- BL-307 (feature flags) must precede BL-315 (seed endpoint guard)
- BL-301 (Dockerfile) must precede BL-302 (deploy smoke test) and BL-304 (startup health)
- BL-330 (panel layout) must precede BL-331 (presets) and BL-334 (batch panel)
- BL-335 (a11y audit) should precede BL-336 (E2E tests that verify a11y)

## Upgrade Triggers (Phase 7+)

- Cross-platform Docker builds (ARM64) if deployment targets diversify
- MCP abstraction layer if agent ecosystem warrants (decision criteria in BL-322)
- Runtime feature flag toggles if gradual rollout requires dynamic switching
- Event persistence (WAL-based) if ring buffer proves insufficient for long-running agents

## Suggested Version Mapping

| Version | Theme | Items | Rationale |
|---------|-------|-------|-----------|
| v037 | Phase 5 Residuals + Container Deployment | BL-254, BL-255, BL-258, BL-301, BL-302, BL-303 | Clear residuals; establish container build early for CI use |
| v038 | Deployment Safety + Version | BL-304, BL-305, BL-306, BL-307, BL-308 | Complete deployment infrastructure before feature work |
| v039 | AI Integration + API Testability | BL-309, BL-310, BL-311, BL-312, BL-313, BL-314, BL-315, BL-316, BL-317 | Core agent infrastructure — largest version, all M6.3+M6.7 items |
| v040 | Documentation & Agent Support | BL-318, BL-319, BL-320, BL-321, BL-322, BL-323, BL-324 | All docs written after API is stable (post-v039) |
| v041 | Quality & Security Gate | BL-325, BL-326, BL-327, BL-328, BL-329 | Security review and benchmarks after all features landed |
| v042 | GUI Unified Workspace | BL-330, BL-331, BL-332, BL-333, BL-334 | Workspace infrastructure before polish |
| v043 | GUI Final Polish | BL-335, BL-336, BL-337, BL-338 | Accessibility, E2E, optimization as final pass |
