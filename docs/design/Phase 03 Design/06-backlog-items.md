# Phase 3: Backlog Items

## Sizing Rules

Per exploration prompt: Documentation-only = Small; Single focused code change = Small; New feature with tests = Medium; Complex cross-cutting feature = Large.

## Deferred Phase 2 Items (Resolve First)

These existing open items should be completed before new Phase 3 work:

| ID | Title | Size | Acceptance Criteria |
|----|-------|------|-------------------|
| BL-081 | Rust filter builder unit test coverage >95% | M | Rust unit test coverage reaches 95% for all filter builder modules |
| BL-082 | Property-based tests (proptest) for filter builder edge cases | M | Proptest strategies cover all filter builders; no panics on random input |
| BL-083 | Contract tests with real FFmpeg for Phase 2 builders | M | All Phase 2 filter builders validated against real FFmpeg; CI contract job passes |
| BL-084 | Performance benchmarks for Rust filter builders vs baseline | S | Benchmark suite exists; results documented; baseline established for Phase 3 |

## New Backlog Items

### Theme 1: Rust Layout & Composition Core

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 1 | Implement LayoutPosition with pixel math and validation | M | Create `layout/position.rs` with normalized position type, `to_pixels()`, and `validate()`. Add proptest for bounds. Expose via PyO3. | LayoutPosition converts normalized coords to pixels correctly; validation rejects out-of-bounds; proptest passes; PyO3 bindings work from Python |
| 2 | Implement LayoutPreset definitions | S | Create `layout/preset.rs` with 7 preset definitions (PIP corners, side-by-side, top-bottom, 2x2 grid). Each preset returns correct LayoutPositions for given input count. | All 7 presets generate correct positions; unit tests verify each preset; exposed via PyO3 |
| 3 | Implement overlay and scale filter builders for composition | M | Create `compose/overlay.rs` with `build_overlay_filter()` and `build_scale_for_layout()`. Pure functions generating FFmpeg overlay/scale filter strings. | Generated filters are valid FFmpeg syntax; proptest for various resolutions; contract test with real FFmpeg |
| 4 | Implement multi-clip composition position calculator | M | Create `compose/timeline.rs` with `calculate_composition_positions()` and `calculate_timeline_duration()` that account for transition overlaps. | Position calculations are correct with and without transitions; duration accounts for overlaps; proptest passes |
| 5 | Implement composition FilterGraph builder | L | Create `compose/graph.rs` with `build_composition_graph()` that produces a complete FilterGraph from clips, transitions, layout, and audio mix. Integrates all composition Rust modules. | FilterGraph generated for various compositions (2-clip, 4-clip, PIP, side-by-side); contract test validates with real FFmpeg; handles edge cases (single clip, no transitions) |
| 6 | Extend AudioMixSpec for multi-track coordination | M | Add `AudioMixSpec` to `ffmpeg/audio.rs` that wraps existing AmixBuilder/VolumeBuilder/AfadeBuilder for multi-track mixing. | AudioMixSpec builds correct filter chains for 2-8 tracks; validate() rejects invalid ranges; unit tests cover edge cases |
| 7 | Implement batch progress calculator | S | Create `batch.rs` with `calculate_batch_progress()` pure function for aggregating individual job progress. | Progress calculation correct for various job states; proptest passes; exposed via PyO3 |

### Theme 2: Timeline API & Persistence

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 8 | Add Track and TimelineClip data models and DB schema | M | Create Track dataclass, extend Clip model, add DB migration for tracks table and clips table alterations. Follow existing pattern in `db/schema.py`. | Track and extended Clip models defined; DB migration creates tracks table and adds columns to clips; existing tests still pass |
| 9 | Implement timeline repository with track/clip persistence | M | Create `db/timeline_repository.py` with CRUD for tracks and timeline-aware clip queries. Add InMemory test double. | Tracks persist to SQLite; clips queryable by track; InMemory double passes parity tests |
| 10 | Create timeline API endpoints | M | Create `api/routers/timeline.py` with PUT timeline, GET timeline, POST clip, PATCH clip, DELETE clip endpoints. Wire into app.py. | All CRUD endpoints work; validation errors return structured responses; black box tests pass |
| 11 | Add timeline transition endpoints with offset calculation | M | Add POST/DELETE transition endpoints to timeline router that compute timeline offsets using Rust core. | Transitions applied with correct offsets; non-adjacent clips rejected with clear error; filter_string included in response |

### Theme 3: Composition & Audio API

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 12 | Create layout preset discovery endpoint | S | Create `api/routers/compose.py` with GET /compose/presets endpoint returning all layout presets with AI hints. | Presets returned with name, description, ai_hint, min/max inputs; follows existing effect discovery pattern |
| 13 | Create layout application endpoint | M | Add POST /compose/layout endpoint accepting preset or custom positions. Returns filter preview string. | Preset layouts generate correct positions; custom positions validated; filter preview generated by Rust core |
| 14 | Create audio mix configuration endpoint | M | Create `api/routers/audio.py` with PUT /audio/mix and POST /audio/mix/preview endpoints. | Volume, fade, normalize settings accepted; filter preview generated; validation rejects out-of-range values |
| 15 | Add composition WebSocket events | S | Add event types for timeline_updated, layout_applied, audio_mix_changed, transition_applied to WebSocket broadcast. | Events broadcast on composition changes; activity log displays events; follows existing event pattern |

### Theme 4: Batch Processing & Project Versioning

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 16 | Implement batch render endpoint | M | Create `api/routers/batch.py` with POST /render/batch and GET /render/batch/{id} endpoints. Uses existing job queue with batch grouping. | Batch submission creates grouped jobs; status aggregates progress across jobs; respects parallel limit |
| 17 | Implement project version persistence | M | Create `db/version_repository.py` with version save/restore/list. Add project_versions table. Timeline JSON serialized on each save. | Versions auto-increment on timeline changes; list shows recent versions; restore creates new version from old state |
| 18 | Create project version API endpoints | S | Create `api/routers/versions.py` with GET versions and POST restore endpoints. | Version list paginated; restore creates new version; integrity validation on restore |

### Theme 5: GUI Timeline Canvas

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 19 | Build timeline canvas with time ruler and tracks | L | Create TimelineCanvas, TimeRuler, Track components. Horizontal scrolling timeline with visual tracks. | Time ruler shows accurate markers; tracks render with labels; horizontal scroll works; zoom controls functional |
| 20 | Implement clip visualization on timeline | M | Create TimelineClip component showing clips positioned on tracks with duration, thumbnails, and selection. | Clips display at correct positions; selection highlights clip; duration label shown; playhead visible |
| 21 | Build composition layout preview panel | M | Create LayoutPreview, LayoutSelector, LayerStack components for visualizing PIP and split-screen layouts. | Layout presets selectable; preview shows position rectangles; z-order displayed; custom positioning inputs work |
| 22 | Add Timeline page and navigation | S | Create TimelinePage, add /gui/timeline route, add Timeline tab to navigation. Wire stores and hooks. | Timeline page accessible via nav; stores connected to API; page loads without errors |

### Theme 6: Quality & Documentation

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 23 | Add composition smoke tests | M | Create smoke tests for timeline CRUD, layout presets, batch render, and project versions. Run with --no-cov. | Smoke tests exercise full HTTP stack; all tests pass in CI; uses real Rust core |
| 24 | Add composition contract tests with real FFmpeg | M | Create contract tests verifying overlay, composition graph, and audio mix filters work with real FFmpeg. | All composition filters validated against FFmpeg; CI contract job includes composition tests |
| 25 | Update design documents for Phase 3 | S | Update 01-roadmap.md (mark milestones), 02-architecture.md (add composition layer), 05-api-specification.md (add endpoints), 07-quality-architecture.md, 08-gui-architecture.md. | All 5 design docs updated with Phase 3 content; no stale references |
| 26 | Update IMPACT_ASSESSMENT with Phase 3 patterns | S | Add grep patterns for composition models (TrackType, LayoutPosition, AudioMixSpec, BatchProgress) to IMPACT_ASSESSMENT.md. | New patterns added; maintenance check CI job passes |

## Summary

| Category | Items | Small | Medium | Large |
|----------|-------|-------|--------|-------|
| Deferred Phase 2 | 4 | 1 | 3 | 0 |
| Rust Core | 7 | 2 | 4 | 1 |
| Timeline API | 4 | 0 | 4 | 0 |
| Composition API | 4 | 2 | 2 | 0 |
| Batch & Versioning | 3 | 1 | 2 | 0 |
| GUI Timeline | 4 | 1 | 2 | 1 |
| Quality & Docs | 4 | 2 | 2 | 0 |
| **Total** | **30** | **9** | **19** | **2** |

## Suggested Version Mapping

| Version | Theme | Items | Rationale |
|---------|-------|-------|-----------|
| v015 | Deferred Phase 2 quality + Rust layout core | BL-081–084 + items 1–4 | LRN-019: build infrastructure first; resolve tech debt before new features |
| v016 | Composition graph + timeline API | Items 5–7, 8–11 | Core composition engine + persistence; enables all other features |
| v017 | Composition & audio API + batch | Items 12–18 | API surface for all composition features |
| v018 | GUI Timeline Canvas + quality | Items 19–26 | Visual interface + comprehensive testing |
