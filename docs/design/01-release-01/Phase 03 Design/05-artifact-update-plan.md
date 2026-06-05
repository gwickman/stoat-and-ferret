# Phase 3: Artifact Update Plan

## Overview

Phase 3 composition features touch multiple existing artifacts. This document catalogs every file or artifact that needs updating, organized by area.

## Design Documents

| File | Update Needed |
|------|--------------|
| `docs/design/01-roadmap.md` | Mark Phase 3 milestones 3.1-3.8 as in-progress/complete |
| `docs/design/02-architecture.md` | Add composition layer to architecture diagram, document layout/compose modules |
| `docs/design/05-api-specification.md` | Add timeline, compose, audio, batch, and version endpoint specs |
| `docs/design/07-quality-architecture.md` | Add composition test patterns, update test pyramid description |
| `docs/design/08-gui-architecture.md` | Add Timeline Canvas component specs, update progressive enhancement section |

## API Specification Updates

### OpenAPI / Auto-Generated

FastAPI auto-generates OpenAPI from route definitions. New routers automatically appear. Manual updates needed:

| Artifact | Change |
|----------|--------|
| `05-api-specification.md` | Add 5 new endpoint groups (timeline, compose, audio, batch, versions) |
| API error codes section | Add composition-specific error codes (see `03-api-endpoints.md`) |
| Effect discovery section | Add layout presets to discovery pattern |

## Rust Core Artifacts

| File | Change |
|------|--------|
| `rust/stoat_ferret_core/Cargo.toml` | Add `rayon = "1.8"` dependency |
| `rust/stoat_ferret_core/src/lib.rs` | Register new modules (layout, compose, batch) and PyO3 bindings |
| `src/stoat_ferret_core/_core.pyi` | Add type stubs for all new Rust types and functions |
| `src/stoat_ferret_core/__init__.py` | Export new classes/functions |

### New Rust Files to Create

```
rust/stoat_ferret_core/src/layout/mod.rs
rust/stoat_ferret_core/src/layout/position.rs
rust/stoat_ferret_core/src/layout/preset.rs
rust/stoat_ferret_core/src/compose/mod.rs
rust/stoat_ferret_core/src/compose/timeline.rs
rust/stoat_ferret_core/src/compose/overlay.rs
rust/stoat_ferret_core/src/compose/graph.rs
rust/stoat_ferret_core/src/batch.rs
```

### Existing Rust Files to Extend

```
rust/stoat_ferret_core/src/ffmpeg/audio.rs  → add AudioMixSpec
rust/stoat_ferret_core/src/ffmpeg/mod.rs    → re-export AudioMixSpec
```

## Python Backend Artifacts

### New Files to Create

```
src/stoat_ferret/api/routers/timeline.py    → timeline CRUD endpoints
src/stoat_ferret/api/routers/compose.py     → layout/composition endpoints
src/stoat_ferret/api/routers/audio.py       → audio mix endpoints
src/stoat_ferret/api/routers/batch.py       → batch render endpoints
src/stoat_ferret/api/routers/versions.py    → project version endpoints
src/stoat_ferret/api/schemas/timeline.py    → Timeline, Track, TimelineClip schemas
src/stoat_ferret/api/schemas/compose.py     → LayoutPosition, LayoutPreset schemas
src/stoat_ferret/api/schemas/audio.py       → AudioTrackConfig, AudioMixConfig schemas
src/stoat_ferret/api/schemas/batch.py       → BatchRequest, BatchStatus schemas
src/stoat_ferret/api/schemas/version.py     → ProjectVersion schema
src/stoat_ferret/db/timeline_repository.py  → timeline/track persistence
src/stoat_ferret/db/version_repository.py   → project version storage
```

### Existing Files to Modify

| File | Change |
|------|--------|
| `src/stoat_ferret/api/app.py` | Register new routers (timeline, compose, audio, batch, versions) |
| `src/stoat_ferret/db/models.py` | Add Track dataclass, extend Clip with track_id/timeline fields, add ProjectVersion |
| `src/stoat_ferret/db/schema.py` | Add tracks table, project_versions table, alter clips table |
| `src/stoat_ferret/db/clip_repository.py` | Support track_id filtering, timeline position queries |
| `src/stoat_ferret/db/project_repository.py` | Support version creation and restore |
| `src/stoat_ferret/api/schemas/clip.py` | Add track_id, timeline_start, timeline_end fields |
| `src/stoat_ferret/api/schemas/project.py` | Add tracks, timeline_duration, version fields |
| `src/stoat_ferret/effects/registry.py` | Register layout presets as discoverable items |
| `src/stoat_ferret/api/websocket/events.py` | Add composition event types (timeline_updated, layout_applied, etc.) |
| `src/stoat_ferret/jobs/queue.py` | Support batch job grouping |

## Test Artifacts

### New Test Files

```
tests/test_api/test_timeline.py          → timeline endpoint tests
tests/test_api/test_compose.py           → composition endpoint tests
tests/test_api/test_audio.py             → audio mix endpoint tests
tests/test_api/test_batch.py             → batch render endpoint tests
tests/test_api/test_versions.py          → project version endpoint tests
tests/test_blackbox/test_composition_workflow.py → end-to-end composition
tests/test_contract/test_composition_contract.py → FFmpeg filter validation
tests/smoke/test_composition.py          → composition smoke tests
tests/smoke/test_batch.py               → batch processing smoke tests
```

### Existing Test Files to Modify

| File | Change |
|------|--------|
| `tests/conftest.py` | Add timeline_factory, test_video_pair fixtures |
| `tests/test_doubles/` | Add InMemoryTimelineRepository, InMemoryVersionRepository |
| `tests/smoke/conftest.py` | Add composition fixtures |
| `IMPACT_ASSESSMENT.md` | Add grep patterns for composition models |

## GUI Artifacts

### New GUI Files (Phase 3 Timeline Canvas)

```
gui/src/pages/TimelinePage.tsx              → timeline editing page
gui/src/components/timeline/TimelineCanvas.tsx  → main timeline component
gui/src/components/timeline/Track.tsx       → individual track renderer
gui/src/components/timeline/TimelineClip.tsx → clip on timeline
gui/src/components/timeline/Playhead.tsx    → playhead indicator
gui/src/components/timeline/TimeRuler.tsx   → time ruler/scale
gui/src/components/timeline/ZoomControls.tsx → zoom in/out controls
gui/src/components/compose/LayoutPreview.tsx → layout visualization
gui/src/components/compose/LayoutSelector.tsx → preset picker
gui/src/components/compose/LayerStack.tsx   → z-order visualization
gui/src/stores/timelineStore.ts             → timeline state management
gui/src/stores/composeStore.ts              → composition state
gui/src/hooks/useTimeline.ts                → timeline API integration
gui/src/hooks/useCompose.ts                 → composition API integration
gui/src/api/timeline.ts                     → timeline API client
gui/src/api/compose.ts                      → composition API client
```

### Existing GUI Files to Modify

| File | Change |
|------|--------|
| `gui/src/App.tsx` | Add `/gui/timeline` route |
| `gui/src/components/Navigation.tsx` | Add Timeline tab |
| `gui/src/components/StatusBar.tsx` | Show timeline duration |
| `gui/src/stores/projectStore.ts` | Add timeline version info |
| `gui/src/hooks/useWebSocket.ts` | Handle composition events |
| `gui/src/types/api.ts` | Add timeline, layout, audio types |

## CI/CD Artifacts

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Add composition smoke test job, update Rust test commands |
| `IMPACT_ASSESSMENT.md` | Add Phase 3 grep patterns |

## Database Migrations

New migration needed for:
1. Create `tracks` table
2. Add `track_id`, `timeline_start`, `timeline_end` to `clips` table
3. Create `project_versions` table

Migration should follow existing pattern in `db/schema.py` with backward-compatible defaults (LRN-017: empty allowlist = unrestricted).

## Summary Count

| Category | New Files | Modified Files |
|----------|----------|----------------|
| Rust core | 8 | 3 |
| Python backend | 11 | 10 |
| Tests | 9 | 4 |
| GUI | 16 | 6 |
| Design docs | 0 | 5 |
| CI/CD | 0 | 2 |
| **Total** | **44** | **30** |
