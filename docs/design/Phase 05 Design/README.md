# Phase 5: Export & Production Design

Phase 5 extends stoat-and-ferret with a full render pipeline: Rust-powered render coordination, hardware-accelerated encoding with fallback chains, an async job queue with crash recovery, and a GUI Render Control Center. The design builds on the established hybrid Python/Rust architecture: Rust handles render plan generation, FFmpeg command construction, encoder detection, and progress calculation; Python manages job orchestration, queue persistence, and API serving. The design produces 30 new backlog items (11 Small, 12 Medium, 6 Large) mapped across 4 versions (v028-v031).

**Design status:** Initial design. All open questions resolved.

## Key Design Decisions

1. **Larger Rust scope than Phase 4**: Phase 5 adds four Rust submodules (plan, encoder, progress, command) versus Phase 4's single module. This is justified because render coordination involves compute-intensive pure functions: building FFmpeg filter graphs from timelines, calculating progress/ETA across segments, and detecting hardware encoders. Per LRN-012, Rust is still only used where it provides genuine value.

2. **Sequential rendering with parallel-ready data model**: Phase 5 renders segments sequentially for simplicity, but the `RenderPlan` and segment-based progress tracking support future parallel rendering without data model changes. Parallel rendering will activate for timelines >= 5 minutes (`render_parallel_min_duration_seconds = 300`); below this threshold, segment overhead outweighs speedup.

3. **SQLite persistence over Redis**: Per LRN-010 (prefer stdlib asyncio.Queue over external dependencies), render jobs are persisted to SQLite (extending the BL-143 batch state pattern) rather than introducing Redis. The queue uses asyncio for orchestration with SQLite as the persistence layer.

4. **Non-destructive output**: Per LRN-091, render output goes to a separate directory and never modifies source files. The DELETE endpoint removes job metadata but preserves output files.

5. **Hardware acceleration is optional and auto-detected**: Encoder detection runs at startup, results are cached in SQLite. The fallback chain ensures rendering always works (via software encoder) even without GPU hardware.

6. **Render replaces basic export**: The existing Phase 1 render endpoint is replaced by the full job queue system. The batch render endpoint (Phase 3) internally creates individual render jobs.

## Document Inventory

Read in this order:

| # | File | Description |
|---|------|-------------|
| 1 | `01-export-data-models.md` | Pydantic and Rust struct definitions for render jobs, render plans, hardware encoders, quality presets, checkpoints, and render queue. Includes database schema additions and configuration extensions. |
| 2 | `02-rust-core-design.md` | Four new Rust submodules: render plan generation, hardware encoder detection/selection, progress tracking with FFmpeg output parsing, and render command construction. PyO3 bindings and property-based tests. |
| 3 | `03-api-endpoints.md` | FastAPI endpoints for render start/status/cancel/retry/delete, encoder detection/refresh, output format discovery, and render queue status. WebSocket event contracts for render lifecycle. |
| 4 | `04-observability-and-operations.md` | Structured logging events, Prometheus metrics, health checks, graceful degradation (FFmpeg unavailable, disk full, HW encoder failure), and resource management for the render subsystem. |
| 5 | `05-gui-integration.md` | React components for Render Control Center (job list, progress bars, queue status), Start Render modal (format/quality/encoder settings, disk space check, command preview), and Theater Mode render integration. |
| 6 | `06-test-strategy.md` | Test harness updates: recording fakes for render executor and hardware detector, black box scenarios, contract tests with real FFmpeg, smoke tests, and 4 UAT journeys (export, queue, settings, recovery). |
| 7 | `07-artifact-update-plan.md` | Complete inventory of all files needing creation or modification: 57 new files and 33 modified files across Rust core, Python backend, tests, GUI, design docs, and CI. |
| 8 | `08-backlog-items.md` | 30 backlog items with sizing, acceptance criteria, theme grouping, and suggested version mapping (v028-v031). |

## Resolved Decisions

1. **ProRes support priority**: ProRes is INCLUDED in the Phase 5 initial release. All data models, encoder fallback chains, and test coverage include ProRes from the start.

2. **Two-pass encoding scope**: Two-pass encoding is the DEFAULT for the "high" quality preset (`render_two_pass_default = true`). No explicit opt-in required. Users can disable via settings or per-job override.

3. **Render-during-preview**: IMPLEMENTED in Phase 5. The `render.frame_available` WebSocket event streams the latest rendered frame (540p JPEG via proxy quality infrastructure) to Theater Mode during active renders. Throttled to max 2/sec.

4. **Output path defaults**: Default output directory is `data/renders/` (server-oriented path, relative to project root). This is consistent with the existing `data/` directory convention used by other subsystems.

5. **Parallel segment rendering trigger**: Timeline duration >= 5 minutes (`render_parallel_min_duration_seconds = 300`) with 30-second segments. Below this threshold, segment overhead (keyframe alignment, temp file management, concatenation) outweighs speedup. See `02-rust-core-design.md` for full rationale based on research into FFmpeg parallelism strategies, overhead costs, and industry tool defaults.

## Risks

| Risk | Mitigation |
|------|------------|
| Hardware encoder detection flaky across platforms | Extensive contract tests; always-available software fallback; detection cached in SQLite |
| Long-running FFmpeg processes cause resource exhaustion | Configurable timeout (default 2h); max_concurrent limit; disk space pre-flight check |
| Render crash loses progress | Checkpoint system persists progress to SQLite; recovery on restart |
| Phase 4 not complete when Phase 5 starts | WebSocket push pattern can fall back to polling; Rust module structure is independently implementable |
| Large Rust scope increases implementation risk | Four independent submodules (plan, encoder, progress, command) can be implemented and tested separately |

## Deviations from Phase 4 Design Pattern

1. **Larger Rust scope**: Phase 4 had one Rust module; Phase 5 has four submodules. Justified by the computational nature of render coordination.

2. **Replaces existing endpoint**: Phase 5 replaces the basic Phase 1 render endpoint rather than adding alongside it (as Phase 4 added new endpoints). This is because the job queue system is a strict superset of the original functionality.

3. **No new visual aids**: Phase 4 introduced thumbnails and waveforms. Phase 5 has no equivalent — the GUI focus is on job management and settings, not new media types.

4. **Crash recovery**: Phase 5 introduces a checkpoint/recovery pattern not present in Phase 4. This is because render jobs are long-running (minutes to hours) versus preview sessions (seconds to minutes).
