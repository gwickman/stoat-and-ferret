# Phase 4: Artifact Update Plan

## Overview

Phase 4 preview and playback features touch multiple existing artifacts and require significant new file creation. This document catalogs every file or artifact that needs updating, organized by area.

## Design Documents

| File | Update Needed |
|------|--------------|
| `docs/design/01-roadmap.md` | Mark Phase 4 milestones 4.1-4.7 as in-progress/complete |
| `docs/design/02-architecture.md` | Add preview subsystem to architecture diagram, document HLS serving layer |
| `docs/design/05-api-specification.md` | Add preview, proxy, thumbnail, waveform, and cache endpoint specs |
| `docs/design/07-quality-architecture.md` | Add preview test patterns, recording fakes, update test pyramid |
| `docs/design/08-gui-architecture.md` | Add Preview Player and AI Theater Mode component specs |

## API Specification Updates

### OpenAPI / Auto-Generated

FastAPI auto-generates OpenAPI from route definitions. New routers automatically appear. Manual updates needed:

| Artifact | Change |
|----------|--------|
| `05-api-specification.md` | Add 4 new endpoint groups (preview, proxy, thumbnails, waveform) |
| API error codes section | Add preview-specific error codes (see `03-api-endpoints.md`) |
| WebSocket events section | Add preview and proxy event types |

## Rust Core Artifacts

| File | Change |
|------|--------|
| `rust/stoat_ferret_core/src/lib.rs` | Register preview module and PyO3 bindings |
| `src/stoat_ferret_core/_core.pyi` | Add type stubs for PreviewQuality, simplify functions |
| `src/stoat_ferret_core/__init__.py` | Export new classes/functions |

### New Rust Files to Create

```
rust/stoat_ferret_core/src/preview/mod.rs
rust/stoat_ferret_core/src/preview/simplify.rs
```

### Existing Rust Files (No Changes)

All existing modules (layout, compose, ffmpeg, timeline, clip, sanitize, batch) remain unchanged.

## Python Backend Artifacts

### New Files to Create

```
src/stoat_ferret/api/routers/preview.py       # preview session management + HLS serving
src/stoat_ferret/api/routers/proxy.py          # proxy file management
src/stoat_ferret/api/routers/thumbnails.py     # thumbnail strip generation/serving
src/stoat_ferret/api/routers/waveform.py       # waveform generation/serving
src/stoat_ferret/api/schemas/preview.py        # PreviewSession, PlaybackState schemas
src/stoat_ferret/api/schemas/proxy.py          # ProxyFile, ProxyStatus schemas
src/stoat_ferret/api/schemas/thumbnail.py      # ThumbnailStrip schema
src/stoat_ferret/api/schemas/waveform.py       # Waveform schema
src/stoat_ferret/preview/__init__.py           # preview subsystem package
src/stoat_ferret/preview/manager.py            # PreviewManager - session lifecycle
src/stoat_ferret/preview/hls_generator.py      # FFmpeg HLS segment generation
src/stoat_ferret/preview/cache.py              # PreviewCache - LRU eviction
src/stoat_ferret/preview/proxy_service.py      # proxy generation orchestration
src/stoat_ferret/preview/thumbnail_service.py  # thumbnail strip generation
src/stoat_ferret/preview/waveform_service.py   # waveform generation
src/stoat_ferret/db/proxy_repository.py        # proxy file persistence
src/stoat_ferret/db/preview_repository.py      # preview session persistence
src/stoat_ferret/db/thumbnail_repository.py    # thumbnail strip persistence
src/stoat_ferret/db/waveform_repository.py     # waveform persistence
```

### Existing Files to Modify

| File | Change |
|------|--------|
| `src/stoat_ferret/api/app.py` | Register new routers (preview, proxy, thumbnails, waveform) |
| `src/stoat_ferret/db/models.py` | Add ProxyFile, PreviewSession, ThumbnailStrip, Waveform dataclasses |
| `src/stoat_ferret/db/schema.py` | Add proxy_files, preview_sessions, thumbnail_strips, waveforms tables |
| `src/stoat_ferret/db/video_repository.py` | Add proxy_status field queries |
| `src/stoat_ferret/config.py` | Add preview, proxy, thumbnail, waveform settings |
| `src/stoat_ferret/api/routers/videos.py` | Include proxy status in video responses |
| `src/stoat_ferret/api/routers/health.py` | Add preview and proxy health checks |
| `src/stoat_ferret/api/websocket/events.py` | Add preview, proxy, ai_action, render_progress event types |
| `src/stoat_ferret/jobs/queue.py` | Add PROXY_GENERATE, PREVIEW_GENERATE, THUMBNAIL_STRIP, WAVEFORM job types |
| `src/stoat_ferret/jobs/handlers.py` | Add job handlers for proxy, preview, thumbnail, waveform generation |
| `.env.example` | Add all new SF_PREVIEW_*, SF_PROXY_*, SF_THUMBNAIL_*, SF_WAVEFORM_* settings |

## Test Artifacts

### New Test Files

```
tests/test_doubles/preview.py                         # RecordingPreviewGenerator, RecordingProxyGenerator, InMemoryPreviewCache
tests/test_api/test_preview.py                         # preview endpoint tests
tests/test_api/test_proxy.py                           # proxy endpoint tests
tests/test_api/test_thumbnails.py                      # thumbnail endpoint tests
tests/test_api/test_waveform.py                        # waveform endpoint tests
tests/test_blackbox/test_preview_workflow.py            # end-to-end preview workflow
tests/test_blackbox/test_proxy_workflow.py              # end-to-end proxy workflow
tests/test_contract/test_preview_contract.py            # FFmpeg preview/HLS validation
tests/test_contract/test_thumbnail_contract.py          # FFmpeg thumbnail strip validation
tests/test_contract/test_waveform_contract.py           # FFmpeg waveform validation
tests/smoke/test_preview.py                            # preview smoke tests
tests/smoke/test_proxy.py                              # proxy smoke tests
tests/uat/journeys/test_j401_preview_playback.py       # UAT: preview playback journey
tests/uat/journeys/test_j402_proxy_management.py       # UAT: proxy management journey
tests/uat/journeys/test_j403_theater_mode.py           # UAT: AI Theater Mode journey
tests/uat/journeys/test_j404_timeline_player_sync.py   # UAT: timeline-player sync journey
```

### Existing Test Files to Modify

| File | Change |
|------|--------|
| `tests/conftest.py` | Add preview_recorder, proxy_recorder, preview_cache, project_with_clips fixtures |
| `tests/test_doubles/__init__.py` | Export new test doubles |
| `tests/smoke/conftest.py` | Add smoke_project_with_clips, smoke_video_id fixtures |
| `IMPACT_ASSESSMENT.md` | Add grep patterns for preview/proxy/theater models |

## GUI Artifacts

### New GUI Files

```
gui/src/pages/PreviewPage.tsx                          # preview page
gui/src/components/preview/PreviewPlayer.tsx            # HLS.js video wrapper
gui/src/components/preview/PlayerControls.tsx           # transport controls
gui/src/components/preview/ProgressBar.tsx              # seekable progress bar
gui/src/components/preview/SeekTooltip.tsx              # thumbnail preview on hover
gui/src/components/preview/VolumeSlider.tsx             # volume control
gui/src/components/preview/QualitySelector.tsx          # quality dropdown
gui/src/components/preview/PreviewStatus.tsx            # status/latency display
gui/src/components/theater/TheaterMode.tsx              # full-screen wrapper
gui/src/components/theater/TheaterHUD.tsx               # auto-hiding overlay
gui/src/components/theater/TopHUD.tsx                   # project title + AI action
gui/src/components/theater/BottomHUD.tsx                # controls + progress
gui/src/components/theater/AIActionIndicator.tsx        # AI status display
gui/src/components/theater/TheaterProgressBar.tsx       # full-width progress
gui/src/components/timeline/AudioWaveform.tsx           # waveform in timeline
gui/src/stores/previewStore.ts                         # preview + theater state
gui/src/hooks/useTimelineSync.ts                       # player <-> timeline sync
gui/src/hooks/useTheaterShortcuts.ts                   # keyboard shortcuts
gui/src/hooks/usePreviewSession.ts                     # preview API integration
gui/src/api/preview.ts                                 # preview/proxy API client
gui/src/types/preview.ts                               # TypeScript type definitions
```

### Existing GUI Files to Modify

| File | Change |
|------|--------|
| `gui/src/App.tsx` | Add `/gui/preview` route |
| `gui/src/components/Navigation.tsx` | Add Preview tab |
| `gui/src/components/StatusBar.tsx` | Show preview session status |
| `gui/src/hooks/useWebSocket.ts` | Handle preview, proxy, ai_action events |
| `gui/src/types/api.ts` | Add preview, proxy, thumbnail, waveform types |
| `gui/src/components/library/VideoCard.tsx` | Add proxy status indicator |
| `gui/src/stores/videoStore.ts` | Add proxy status tracking |
| `gui/src/components/timeline/TimelineClip.tsx` | Add thumbnail strip integration |

## CI/CD Artifacts

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Add preview smoke test job, preview contract test job, Rust preview test command |
| `IMPACT_ASSESSMENT.md` | Add Phase 4 grep patterns |

## Database Migrations

New migration needed for:
1. Create `proxy_files` table
2. Create `preview_sessions` table
3. Create `thumbnail_strips` table
4. Create `waveforms` table

Migration should follow existing pattern in `db/schema.py` with backward-compatible defaults.

## Summary Count

| Category | New Files | Modified Files |
|----------|----------|----------------|
| Rust core | 2 | 2 |
| Python backend | 20 | 11 |
| Tests | 16 | 4 |
| GUI | 22 | 8 |
| Design docs | 0 | 5 |
| CI/CD | 0 | 2 |
| **Total** | **60** | **32** |
