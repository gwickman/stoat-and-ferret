# Phase 5: Artifact Update Plan

## Overview

Phase 5 render and export features touch multiple existing artifacts and require significant new file creation. This document catalogs every file or artifact that needs updating, organized by area.

## Design Documents

| File | Update Needed |
|------|--------------|
| `docs/design/01-roadmap.md` | Mark Phase 5 milestones 5.1-5.9 as in-progress/complete |
| `docs/design/02-architecture.md` | Add render subsystem to architecture diagram, document render coordinator layer |
| `docs/design/05-api-specification.md` | Add render, encoder, and format endpoint specs |
| `docs/design/07-quality-architecture.md` | Add render test patterns, recording fakes, update test pyramid |
| `docs/design/08-gui-architecture.md` | Add Render Control Center and Render Settings component specs |

## API Specification Updates

### OpenAPI / Auto-Generated

FastAPI auto-generates OpenAPI from route definitions. New routers automatically appear. Manual updates needed:

| Artifact | Change |
|----------|--------|
| `05-api-specification.md` | Add 3 new endpoint groups (render CRUD, encoders, formats) |
| API error codes section | Add render-specific error codes (see `03-api-endpoints.md`) |
| WebSocket events section | Add render event types (queued, started, progress, completed, failed, cancelled, frame_available) |

## Rust Core Artifacts

| File | Change |
|------|--------|
| `rust/stoat_ferret_core/src/lib.rs` | Register render module and PyO3 bindings |
| `src/stoat_ferret_core/_core.pyi` | Add type stubs for RenderPlan, RenderSettings, HardwareEncoder, etc. |
| `src/stoat_ferret_core/__init__.py` | Export new classes/functions |

### New Rust Files to Create

```
rust/stoat_ferret_core/src/render/mod.rs
rust/stoat_ferret_core/src/render/plan.rs
rust/stoat_ferret_core/src/render/encoder.rs
rust/stoat_ferret_core/src/render/progress.rs
rust/stoat_ferret_core/src/render/command.rs
```

### Existing Rust Files (No Changes)

All existing modules (layout, compose, ffmpeg, timeline, clip, sanitize, batch, preview) remain unchanged.

## Python Backend Artifacts

### New Files to Create

```
src/stoat_ferret/render/__init__.py             # render subsystem package
src/stoat_ferret/render/service.py              # RenderService - job orchestration
src/stoat_ferret/render/executor.py             # FFmpeg process management for render
src/stoat_ferret/render/queue.py                # RenderQueue - async job queue with persistence
src/stoat_ferret/render/checkpoint.py           # Checkpoint management for crash recovery
src/stoat_ferret/render/hw_detect.py            # Hardware encoder detection (wraps Rust)
src/stoat_ferret/render/disk_check.py           # Disk space verification
src/stoat_ferret/api/routers/render_encoders.py # encoder status and refresh endpoints
src/stoat_ferret/api/routers/render_formats.py  # output format discovery endpoints
src/stoat_ferret/api/schemas/render.py          # RenderJob, RenderSettings, RenderQueue schemas
src/stoat_ferret/api/schemas/encoder.py         # HardwareEncoder, EncoderType schemas
src/stoat_ferret/api/schemas/format.py          # OutputFormat, QualityPreset schemas
src/stoat_ferret/db/render_repository.py        # render job persistence
src/stoat_ferret/db/checkpoint_repository.py    # checkpoint persistence
src/stoat_ferret/db/encoder_repository.py       # hardware encoder cache persistence
```

### Existing Files to Modify

| File | Change |
|------|--------|
| `src/stoat_ferret/api/app.py` | Register new routers (render_encoders, render_formats) |
| `src/stoat_ferret/api/routers/render.py` | Replace basic render with full job CRUD, queue status |
| `src/stoat_ferret/db/models.py` | Add RenderJob, RenderCheckpoint, HardwareEncoder dataclasses |
| `src/stoat_ferret/db/schema.py` | Add render_jobs, render_checkpoints, hardware_encoders tables |
| `src/stoat_ferret/config.py` | Add render queue, output, and hardware settings |
| `src/stoat_ferret/api/routers/health.py` | Add render subsystem health check |
| `src/stoat_ferret/api/websocket/events.py` | Add render event types (queued, started, progress, completed, failed, cancelled, frame_available) |
| `src/stoat_ferret/jobs/queue.py` | Add RENDER, RENDER_SEGMENT job types |
| `src/stoat_ferret/jobs/handlers.py` | Add render job handler |
| `.env.example` | Add all new SF_RENDER_* settings |

## Test Artifacts

### New Test Files

```
tests/test_doubles/render.py                             # RecordingRenderExecutor, RecordingHardwareDetector, InMemoryRenderQueue
tests/test_api/test_render_jobs.py                        # render job endpoint tests
tests/test_api/test_render_encoders.py                    # encoder endpoint tests
tests/test_api/test_render_formats.py                     # format endpoint tests
tests/test_api/test_render_queue.py                       # queue management tests
tests/test_blackbox/test_render_workflow.py                # end-to-end render workflow
tests/test_blackbox/test_render_recovery.py               # crash recovery workflow
tests/test_contract/test_render_contract.py               # FFmpeg render command validation
tests/test_contract/test_encoder_contract.py              # encoder detection validation
tests/test_contract/test_concat_contract.py               # segment concatenation validation
tests/smoke/test_render.py                                # render smoke tests
tests/smoke/test_render_encoders.py                       # encoder smoke tests
tests/uat/journeys/test_j501_export_video.py              # UAT: export video journey
tests/uat/journeys/test_j502_render_queue.py              # UAT: render queue management
tests/uat/journeys/test_j503_render_settings.py           # UAT: render settings and formats
tests/uat/journeys/test_j504_failed_render.py             # UAT: failed render recovery
```

### Existing Test Files to Modify

| File | Change |
|------|--------|
| `tests/conftest.py` | Add render_recorder, hw_detector, render_queue, project_with_clips fixtures |
| `tests/test_doubles/__init__.py` | Export new test doubles |
| `tests/smoke/conftest.py` | Add smoke_project_with_clips fixture (may already exist from Phase 4) |
| `IMPACT_ASSESSMENT.md` | Add grep patterns for render/encoder/queue models |

## GUI Artifacts

### New GUI Files

```
gui/src/pages/RenderPage.tsx                               # render page
gui/src/components/render/RenderControlCenter.tsx           # main layout
gui/src/components/render/RenderJobCard.tsx                 # job display
gui/src/components/render/RenderProgressBar.tsx             # progress bar with ETA
gui/src/components/render/RenderQueueStatus.tsx             # queue overview bar
gui/src/components/render/ActiveRenderList.tsx              # active jobs section
gui/src/components/render/PendingRenderList.tsx             # pending queue section
gui/src/components/render/RenderHistory.tsx                 # completed/failed history
gui/src/components/render/StartRenderModal.tsx              # render start dialog
gui/src/components/render/RenderSettingsForm.tsx            # settings form
gui/src/components/render/EncoderSelector.tsx               # HW/SW encoder selector
gui/src/components/render/QualityPresetSelector.tsx         # quality preset radio group
gui/src/components/render/OutputPathSelector.tsx            # output path with browse
gui/src/components/render/DiskSpaceIndicator.tsx            # disk space display
gui/src/components/render/CommandPreview.tsx                # FFmpeg command preview
gui/src/components/render/StatusBadge.tsx                   # status color badge
gui/src/stores/renderStore.ts                              # render state management
gui/src/hooks/useRenderEstimate.ts                         # disk space + size estimation
gui/src/hooks/useCommandPreview.ts                         # command preview hook
gui/src/api/render.ts                                      # render REST API client
gui/src/types/render.ts                                    # TypeScript type definitions
```

### Existing GUI Files to Modify

| File | Change |
|------|--------|
| `gui/src/App.tsx` | Add `/gui/render` route |
| `gui/src/components/Navigation.tsx` | Add Render tab |
| `gui/src/components/StatusBar.tsx` | Show active render count and progress |
| `gui/src/hooks/useWebSocket.ts` | Handle render.* event types |
| `gui/src/types/api.ts` | Add render, encoder, format types |
| `gui/src/components/theater/BottomHUD.tsx` | Add render progress display (Phase 4 integration) |
| `gui/src/components/timeline/TimelinePage.tsx` | Add "Start Render" quick action button |

## CI/CD Artifacts

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Add render smoke test job, render contract test job, Rust render test command |
| `IMPACT_ASSESSMENT.md` | Add Phase 5 grep patterns |

## Database Migrations

New migration needed for:
1. Create `render_jobs` table
2. Create `render_checkpoints` table
3. Create `hardware_encoders` table
4. Add indexes for render status and project queries

Migration should follow existing pattern in `db/schema.py` with backward-compatible defaults.

## Sample Project Updates

The Running Montage sample project should be extended with a render example:
- Add render command to `scripts/seed_sample_project.py`
- Update sample project user guide with export workflow
- Add render smoke test to sample project regression suite

## Summary Count

| Category | New Files | Modified Files |
|----------|----------|----------------|
| Rust core | 5 | 2 |
| Python backend | 15 | 10 |
| Tests | 16 | 4 |
| GUI | 21 | 7 |
| Design docs | 0 | 5 |
| CI/CD | 0 | 2 |
| Sample project | 0 | 3 |
| **Total** | **57** | **33** |
