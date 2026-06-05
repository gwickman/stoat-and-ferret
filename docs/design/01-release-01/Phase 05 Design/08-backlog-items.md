# Phase 5: Backlog Items

## Sizing Rules

Per exploration prompt: Documentation-only = Small; Single focused code change = Small; New feature with tests = Medium; Complex cross-cutting feature = Large.

## Phase 4 Dependencies

Phase 5 depends on the following Phase 4 outputs:
- **BL-141 (WebSocket push)**: Render progress events use the same push pattern
- **Preview filter simplification (Rust)**: Render uses the full production filter graph (not simplified), but the Rust module structure patterns from Phase 4 guide render module design
- **Batch render state persistence (BL-143, v023)**: The SQLite persistence pattern for batch state directly informs render job persistence

If Phase 4 items are not yet complete, Phase 5 can proceed with polling-based progress (falling back to `GET /render/{job_id}` polling) and upgrade to WebSocket push when BL-141 lands.

## New Backlog Items

### Theme 1: Rust Render Core

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 1 | Implement render plan builder in Rust with PyO3 bindings | L | Create `render/plan.rs` with `build_render_plan()` and `validate_render_settings()`. Converts CompositionGraph to RenderPlan with segments, frame counts, and cost estimation. Property-based tests. | RenderPlan produced from CompositionGraph; segments cover full timeline; validation catches invalid settings; proptest passes; PyO3 bindings work from Python |
| 2 | Implement hardware encoder detection and selection in Rust | M | Create `render/encoder.rs` with `detect_hardware_encoders()`, `select_encoder()`, and `build_encoding_args()`. Parses FFmpeg encoder list and implements fallback chain. | Detection parses real FFmpeg output; fallback chain selects SW when HW unavailable; encoding args correct per preset/encoder; proptest passes; PyO3 bindings work |
| 3 | Implement render progress tracking and FFmpeg output parsing in Rust | M | Create `render/progress.rs` with `calculate_progress()`, `parse_ffmpeg_progress()`, and `aggregate_segment_progress()`. Parses FFmpeg stderr for frame/time progress. | Progress bounded 0.0-1.0; ETA calculated correctly; FFmpeg output parsed; multi-segment aggregation works; proptest passes; PyO3 bindings work |
| 4 | Implement render command builder in Rust | M | Create `render/command.rs` with `build_render_command()`, `build_concat_command()`, `check_output_conflict()`, and `estimate_output_size()`. Generates complete FFmpeg CLI commands. | Commands include all required FFmpeg args; concat uses demuxer format; size estimate proportional to duration; proptest passes; PyO3 bindings work |

### Theme 2: Render Job Infrastructure

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 5 | Add render job data model and database schema | M | Create RenderJob, RenderStatus, OutputFormat, QualityPreset models. Add render_jobs table to SQLite. Create AsyncRenderRepository with InMemory test double. | RenderJob persists to SQLite; status transitions enforced; indexes on status and project_id; InMemory double passes parity tests |
| 6 | Implement render queue with persistence and concurrency control | L | Create RenderQueue class managing job ordering, concurrency limits (max_concurrent), queue depth limits, and SQLite-backed persistence for crash recovery. | Queue enforces max_concurrent; rejects when max_depth reached; persists to SQLite; surviving jobs resume on restart; structured logging for enqueue/dequeue |
| 7 | Implement render executor with FFmpeg process management | L | Create RenderExecutor orchestrating FFmpeg subprocess lifecycle: start, progress monitoring (via Rust parser), cancellation (SIGTERM/SIGKILL), timeout, and temp file cleanup. | FFmpeg process started and monitored; progress parsed and broadcast; cancellation sends SIGTERM then SIGKILL; timeout enforced; temp files cleaned on completion/failure |
| 8 | Implement render checkpoint system for crash recovery | M | Create checkpoint management: write checkpoint after each segment, query unfinished jobs on startup, resume from last checkpoint. SQLite persistence. | Checkpoints written to SQLite; recovery finds interrupted jobs; resume skips completed segments; stale checkpoints cleaned; structured logging |
| 9 | Implement render service orchestrating job lifecycle | L | Create RenderService coordinating: pre-flight checks (disk space, validation, queue capacity), job creation, queue management, progress broadcasting, completion/failure handling, and retry logic. | Pre-flight checks run before queuing; service coordinates executor and queue; progress broadcast via WebSocket; retry on transient failure; cleanup on completion |

### Theme 3: Render API

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 10 | Create render job CRUD endpoints | M | Extend `api/routers/render.py` with POST start, GET status, GET list, POST cancel, POST retry, DELETE endpoints. Wire into app.py. | All CRUD endpoints work; pre-flight checks enforce validation; cancel terminates FFmpeg process; retry requeues failed job; structured errors per pattern |
| 11 | Create hardware encoder endpoints | S | Create `api/routers/render_encoders.py` with GET encoder list and POST refresh endpoints. Cache detection results in SQLite. | Encoder list returns detected encoders; refresh re-runs detection; results cached; structured errors |
| 12 | Create output format discovery endpoint | S | Create `api/routers/render_formats.py` with GET formats endpoint. Returns format capabilities, supported codecs, and quality presets. | Format list includes all 4 formats; capabilities accurate; preset mappings correct; AI-discoverable with rich schema |
| 13 | Add render queue status endpoint | S | Add GET /render/queue endpoint returning active count, pending count, capacity, disk space, and throughput metrics. | Queue status accurate; disk space checked; today's completed/failed counts correct |
| 14 | Add render WebSocket events | M | Add render.queued, render.started, render.progress, render.completed, render.failed, render.cancelled, render.frame_available, render.queue_status event types. Broadcast on job state transitions. render.frame_available streams latest rendered frame URL for Theater Mode display. | All event types broadcast correctly; progress events throttled (max 2/sec); frame_available events throttled (max 2/sec); events include required fields per spec |

### Theme 4: Observability & Operations

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 15 | Add render Prometheus metrics | M | Add all metrics defined in `04-observability-and-operations.md`: job counters, duration histograms, speed ratio, queue depth, HW encoder gauges, disk usage. | Metrics appear on /metrics; histogram buckets appropriate; labels match spec; gauges update correctly |
| 16 | Add structured logging for render subsystem | S | Add all structured log events defined in `04-observability-and-operations.md` for render jobs, hardware detection, resource management, and queue operations. | All lifecycle events logged; correlation IDs present; FFmpeg commands logged for debugging; stderr captured on failure |
| 17 | Extend health checks for render subsystem | S | Add render health check to /health/ready. Report active jobs, queue depth, disk space, and HW encoder availability. Render unavailable doesn't make app unhealthy. | Health check includes render status; degraded when disk low or queue near capacity; unavailable when FFmpeg missing |
| 18 | Implement render graceful degradation and shutdown | S | Render continues operating when FFmpeg unavailable (refuses new jobs). Graceful shutdown cancels active renders and cleans temp files. Timeout with SIGTERM/SIGKILL. | App healthy without FFmpeg; render endpoints return 503; shutdown cancels active processes; temp files cleaned; timeout enforced |

### Theme 5: GUI Render Control Center

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 19 | Build Render Control Center page with job list | L | Create RenderPage with RenderControlCenter layout showing active, pending, and completed jobs. Include queue status bar and "Start Render" button. Real-time updates via WebSocket. | Page shows all job states; WebSocket updates reflected immediately; queue status accurate; data-testid attributes |
| 20 | Build render job card with progress display | M | Create RenderJobCard showing job details, progress bar with ETA, render speed, and action buttons (cancel, retry, delete). StatusBadge for visual state. | Progress bar updates smoothly; ETA displayed; render speed shown; cancel/retry/delete work; correct status colors |
| 21 | Build Start Render modal with settings form | L | Create StartRenderModal with format selector, quality presets, resolution/fps, encoder selector, output path, disk space check, and FFmpeg command preview. | All settings configurable; encoder auto-selects best; disk space checked; command preview updates; validation errors shown inline |
| 22 | Add Render page navigation and renderStore | S | Add /gui/render route, Render tab to navigation. Create renderStore with job list, queue status, and encoder/format state. Wire WebSocket events. | Page accessible via nav; store connected; WebSocket events update store; page loads without errors |

### Theme 6: Integration & Quality

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 23 | Add render smoke tests for all Phase 5 endpoints | M | Create smoke tests for render start, queue status, encoder list, format list, and job list endpoints. Run with --no-cov. | Smoke tests exercise full HTTP stack; all pass in CI; uses real Rust core |
| 24 | Add render contract tests with real FFmpeg | M | Create contract tests verifying render commands, encoder detection, concat, and output format generation work with real FFmpeg. Use lavfi inputs (LRN-100). | All FFmpeg commands validated; output files valid; encoder detection works; concat joins correctly |
| 25 | Add UAT journeys for render workflow | M | Create 4 UAT journey scripts: J501 (export video), J502 (render queue), J503 (render settings), J504 (failed render recovery). | All 4 journeys pass; screenshots captured; report generated; follows existing UAT pattern |
| 26 | Integrate render progress and frame streaming with Theater Mode | M | Update BottomHUD to show active render progress (frame count, fps, ETA, encoder). Wire `render.frame_available` WebSocket event to display rendered frames in Theater Mode at 540p via proxy quality infrastructure. | Render progress visible in Theater Mode; latest rendered frame displayed in real-time; updates throttled to max 2/sec; encoder info displayed |
| 27 | Add "Start Render" quick action to Timeline page | S | Add "Start Render" button to TimelinePage header. Opens StartRenderModal pre-filled with current project. | Button visible on Timeline page; modal opens with correct project; render starts successfully |
| 28 | Update design documents for Phase 5 | S | Update 01-roadmap.md (mark milestones), 02-architecture.md (render subsystem), 05-api-specification.md (endpoints), 07-quality-architecture.md, 08-gui-architecture.md. | All 5 design docs updated with Phase 5 content; no stale references |
| 29 | Update IMPACT_ASSESSMENT with Phase 5 patterns | S | Add grep patterns for render models (RenderJob, RenderPlan, HardwareEncoder, RenderProgress, RenderQueue, OutputFormat, QualityPreset). | New patterns added; maintenance check CI job passes |
| 30 | Extend sample project with render example | S | Add render command to seed script. Update user guide with export workflow. Add render smoke test to regression suite. | Seed script renders sample project; user guide documents export; regression test verifies render |

## Summary

| Category | Items | Small | Medium | Large |
|----------|-------|-------|--------|-------|
| Rust Core | 4 | 0 | 3 | 1 |
| Render Infrastructure | 5 | 0 | 2 | 3 |
| Render API | 5 | 3 | 2 | 0 |
| Observability | 4 | 3 | 1 | 0 |
| GUI | 4 | 1 | 1 | 2 |
| Integration & Quality | 8 | 3 | 4 | 0 |
| **Total** | **30** | **10** | **13** | **6** |

(Note: Render-during-preview streaming, originally reserved from Phase 4, is now included in Phase 5 as part of item 26.)

## Dependencies

- **Phase 4 WebSocket push (BL-141)**: Render progress events build on this pattern. If not yet implemented, render falls back to polling.
- **Phase 3 CompositionGraph**: `build_render_plan()` takes a CompositionGraph as input. This Rust type must be stable.
- **BL-143 (batch state persistence)**: The SQLite persistence pattern for batch state informs render job persistence.
- **Phase 4 preview filter simplification**: Not used directly by render (render uses full-quality filters), but the Rust module structure is the template.

## Upgrade Triggers (Phase 6+)

- **Parallel segment rendering**: Phase 5 renders sequentially but the RenderPlan/segment model supports future parallel rendering. The configured trigger threshold is timeline duration >= 5 minutes (`render_parallel_min_duration_seconds = 300`). Below this threshold, segment overhead (keyframe alignment, temp files, concatenation) outweighs speedup. When implementing, activate parallel rendering for timelines exceeding this threshold using 30-second segments. See `02-rust-core-design.md` for full rationale.
- **Render profiles/templates**: User-saved render settings (format + quality + encoder + resolution combinations) for one-click rendering. Defer until user requests indicate this is a pain point.
- **Distributed rendering**: Multiple machines rendering different segments. Far future — requires network transport and coordination beyond single-machine scope.

## Suggested Version Mapping

| Version | Theme | Items | Rationale |
|---------|-------|-------|-----------|
| v028 | Rust render core + Render infrastructure | Items 1-9 | LRN-019: build infrastructure first. Rust core and job infrastructure must exist before API/GUI can use them. |
| v029 | Render API + Observability | Items 10-18 | API layer and observability instrument the infrastructure from v028. |
| v030 | GUI Render Control Center | Items 19-22 | Frontend requires stable backend API from v029. |
| v031 | Integration + Quality | Items 23-30 | Smoke tests, contract tests, UAT journeys, doc updates. Quality verification as dedicated theme (LRN-082). |

**Note on Phase 4 overlap:** Phase 5 versions (v028-v031) follow Phase 4 versions (v024-v027). If Phase 4 completes early or Phase 5 starts in parallel for non-dependent items (e.g., Rust render core), versions can overlap.
