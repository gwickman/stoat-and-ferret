# Phase 4: Backlog Items

## Sizing Rules

Per exploration prompt: Documentation-only = Small; Single focused code change = Small; New feature with tests = Medium; Complex cross-cutting feature = Large.

## Deferred Items (Resolve First)

These existing open items should be completed before or alongside Phase 4 work:

| ID | Title | Size | Acceptance Criteria |
|----|-------|------|-------------------|
| BL-086 | Effect preview thumbnail with static frame and applied effect | L | Frame extraction endpoint works; thumbnail updates on parameter change; debounced API calls; integrated with effect builder |
| BL-141 | Replace polling-based job progress with WebSocket push events | M | JOB_PROGRESS WebSocket event type defined; job progress pushed on update; frontend polling removed; existing job status tests updated |

## New Backlog Items

### Theme 1: Proxy Infrastructure

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 1 | Add proxy data model and database schema | M | Create ProxyFile dataclass, ProxyStatus/ProxyQuality enums, proxy_files DB table, and AsyncProxyRepository with InMemory test double. | ProxyFile persists to SQLite; unique constraint on (video_id, quality); InMemory double passes parity tests |
| 2 | Implement proxy generation service | M | Create proxy_service.py that orchestrates FFmpeg proxy transcoding as background jobs. Auto-select quality based on source resolution. Integrate with job queue. | Proxy generated at correct quality; job queue integration works; structured logging for start/complete/fail; progress reported via WebSocket |
| 3 | Create proxy management API endpoints | M | Create `api/routers/proxy.py` with POST generate, GET status, DELETE, and POST batch endpoints. Wire into app.py. | All CRUD endpoints work; duplicate proxy returns 409; batch skips existing; structured errors per pattern |
| 4 | Wire proxy auto-generation into scan workflow | S | When `proxy_auto_generate` setting is enabled, automatically queue proxy generation for new videos discovered during scan. | Proxies auto-queued after scan; setting respected; existing scan tests unaffected; log events for auto-proxy |

### Theme 2: Preview Session Infrastructure

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 5 | Add preview session data model and persistence | M | Create PreviewSession dataclass, PreviewStatus enum, preview_sessions DB table, and AsyncPreviewRepository. Add session TTL tracking. | PreviewSession persists; status transitions enforced; expired sessions detectable; InMemory double works |
| 6 | Implement HLS segment generator | L | Create hls_generator.py that uses FFmpeg to produce HLS segments from a project timeline. Apply Rust filter simplification. Generate manifest.m3u8 and segment_NNN.ts files. | HLS segments generated in output directory; manifest is valid HLS; simplified filters used; progress events emitted |
| 7 | Implement preview session manager | L | Create PreviewManager handling session lifecycle: create, generate, seek, stop, expire. Coordinate HLS generator, cache, and WebSocket events. | Session state machine works; concurrent session limit enforced; seek regenerates segments; graceful stop with cleanup |
| 8 | Create preview API endpoints | M | Create `api/routers/preview.py` with POST start, GET status, POST seek, DELETE stop, GET manifest, GET segment endpoints. Wire into app.py. | All endpoints work; manifest served with correct Content-Type; segments streamed; structured errors; empty timeline rejected |
| 9 | Implement preview cache with LRU eviction | M | Create preview cache.py with configurable size limit, TTL-based expiry, and LRU eviction. Background task for periodic cleanup. | Cache enforces size limit; LRU eviction works; TTL expiry works; cache status queryable; structured logging on eviction |
| 10 | Create preview cache API endpoints | S | Add GET /preview/cache status and DELETE /preview/cache clear endpoints. | Cache status returns usage metrics; clear removes all sessions and frees disk; structured errors |

### Theme 3: Rust Preview Filter Simplification

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 11 | Implement preview filter simplification in Rust | L | Create `preview/simplify.rs` with `simplify_filter_graph()`, `simplify_filter_chain()`, and `is_expensive_filter()`. Three quality levels (Draft/Medium/High). Property-based tests. | Simplification reduces filter count at Draft/Medium; High preserves all; proptest passes; PyO3 bindings work from Python |
| 12 | Implement filter cost estimation and preview scale injection | M | Add `estimate_filter_cost()` and `inject_preview_scale()` to Rust preview module. Cost score enables auto-quality selection. | Cost bounded 0.0-1.0; scale filter correctly appended; proptest passes; exposed via PyO3 |

### Theme 4: Visual Aids (Thumbnails & Waveforms)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 13 | Implement thumbnail strip generation service | M | Create thumbnail_service.py using FFmpeg fps+scale+tile filters to generate sprite sheet images. Background job with progress. | Sprite sheet generated with correct frame count/size; interval configurable; job integration; structured logging |
| 14 | Create thumbnail strip API endpoints | M | Create `api/routers/thumbnails.py` with POST generate, GET metadata, and GET image endpoints. Serve strip image with correct Content-Type. | Generate queues job; metadata returns frame dimensions; image served as JPEG; 404 if not generated |
| 15 | Implement waveform generation service | M | Create waveform_service.py using FFmpeg showwavespic filter (PNG) or astats (JSON). Background job with progress. | Waveform generated in requested format; PNG and JSON both work; job integration; structured logging |
| 16 | Create waveform API endpoints | M | Create `api/routers/waveform.py` with POST generate, GET metadata, and GET image/data endpoints. | Generate queues job; metadata returns format/channels; PNG served correctly; JSON returns samples array |

### Theme 5: Observability & Operations

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 17 | Add preview and proxy Prometheus metrics | M | Add all metrics defined in 04-observability-and-operations.md: session counters, generation histograms, cache gauges, proxy gauges. | Metrics appear on /metrics endpoint; histogram buckets appropriate; labels match spec |
| 18 | Add structured logging for preview subsystem | S | Add all structured log events defined in 04-observability-and-operations.md for preview sessions, proxies, cache, and thumbnails/waveforms. | All lifecycle events logged; correlation IDs present; FFmpeg commands logged for debugging |
| 19 | Extend health checks for preview subsystem | S | Add preview and proxy health checks to /health/ready. Preview unavailable doesn't make app unhealthy. Cache warning at >90%. | Health check includes preview/proxy status; degraded when FFmpeg missing; cache usage reported |
| 20 | Implement graceful degradation and shutdown | S | Preview is optional - FFmpeg unavailable returns 503 for preview but app continues. Graceful shutdown cancels active FFmpeg processes and cleans temp files. | App healthy without FFmpeg; preview endpoints return 503; shutdown cancels processes; temp files cleaned |

### Theme 6: GUI Preview Player

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 21 | Build HLS.js preview player component | L | Create PreviewPlayer.tsx with HLS.js integration, video element, error handling, and buffer tracking. Safari native HLS fallback. | HLS playback works; buffer tracked; errors reported; Safari fallback; data-testid attributes |
| 22 | Build player controls and progress bar | M | Create PlayerControls.tsx, ProgressBar.tsx, VolumeSlider.tsx with play/pause/seek/skip/volume. Click-to-seek on progress bar. | All transport controls work; progress bar seekable; volume adjustable; mute toggle; keyboard-accessible |
| 23 | Build seek tooltip with thumbnail strip | M | Create SeekTooltip.tsx that shows thumbnail from sprite sheet on progress bar hover. Calculate correct frame from hover position. | Tooltip appears on hover; correct frame displayed; smooth tracking; disappears on mouse leave |
| 24 | Build quality selector and status display | S | Create QualitySelector.tsx dropdown and PreviewStatus.tsx showing latency/buffer/status. | Quality options match available proxies; status shows real-time latency; buffer amount displayed |
| 25 | Add Preview page and navigation | S | Create PreviewPage.tsx, add /gui/preview route, add Preview tab to navigation. Wire preview store. | Preview page accessible via nav; store connected; page loads without errors |

### Theme 7: GUI AI Theater Mode

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 26 | Build Theater Mode full-screen wrapper | L | Create TheaterMode.tsx with fullscreen API, auto-hiding HUD (TheaterHUD.tsx), and fullscreen exit detection. | Full-screen activates; HUD auto-hides after 3s; mouse movement shows HUD; fullscreen exit returns to normal |
| 27 | Build AI action indicator and theater HUD | M | Create TopHUD.tsx with project title and AIActionIndicator.tsx consuming WebSocket ai_action events. Create BottomHUD.tsx with controls. | AI action text updates in real-time; project title shown; controls functional; render progress displayed |
| 28 | Implement keyboard shortcuts for Theater Mode | S | Create useTheaterShortcuts.ts hook with Space, Escape, F, M, arrows, Home, End. | All shortcuts work; Space toggles play; Escape exits; arrows seek +-5s; volume adjustable |

### Theme 8: Integration & Quality

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|-------------------|
| 29 | Implement timeline-player synchronization | M | Create useTimelineSync.ts hook. Player time updates timeline playhead. Timeline click seeks player. Bidirectional sync with debounce. | Playhead moves during playback; timeline click seeks video; no infinite sync loops; debounced updates |
| 30 | Add preview smoke tests | M | Create smoke tests for preview start, proxy generate, cache status, thumbnail strip, and waveform endpoints. Run with --no-cov. | Smoke tests exercise full HTTP stack; all pass in CI; uses real Rust core |
| 31 | Add preview contract tests with real FFmpeg | M | Create contract tests verifying HLS generation, thumbnail strips, waveforms, and simplified filter chains work with real FFmpeg. | All FFmpeg commands validated; HLS segments playable; thumbnails valid images; waveforms valid |
| 32 | Add UAT journeys for preview and playback | M | Create 4 UAT journey scripts: J401 (preview playback), J402 (proxy management), J403 (theater mode), J404 (timeline-player sync). | All 4 journeys pass; screenshots captured; report generated; follows existing UAT pattern |
| 33 | Add audio waveform visualization to timeline | S | Create AudioWaveform.tsx component rendering waveform PNG as background in audio track clips. Fetch from waveform API. | Waveform visible in audio clips; loads asynchronously; placeholder when missing |
| 34 | Add proxy status indicators to library browser | S | Add proxy status dot/badge to VideoCard.tsx. Green = ready, yellow = generating, gray = none. | Status indicator visible; updates on proxy.ready WebSocket event; correct colors |
| 35 | Update design documents for Phase 4 | S | Update 01-roadmap.md (mark milestones), 02-architecture.md (preview subsystem), 05-api-specification.md (endpoints), 07-quality-architecture.md, 08-gui-architecture.md. | All 5 design docs updated with Phase 4 content; no stale references |
| 36 | Update IMPACT_ASSESSMENT with Phase 4 patterns | S | Add grep patterns for preview models (PreviewSession, ProxyFile, PreviewQuality, ThumbnailStrip, Waveform, TheaterMode). | New patterns added; maintenance check CI job passes |

## Summary

| Category | Items | Small | Medium | Large |
|----------|-------|-------|--------|-------|
| Deferred | 2 | 0 | 1 | 1 |
| Proxy Infrastructure | 4 | 1 | 3 | 0 |
| Preview Sessions | 6 | 1 | 3 | 2 |
| Rust Core | 2 | 0 | 1 | 1 |
| Visual Aids | 4 | 0 | 4 | 0 |
| Observability | 4 | 3 | 1 | 0 |
| GUI Preview Player | 5 | 2 | 2 | 1 |
| GUI Theater Mode | 3 | 1 | 1 | 1 |
| Integration & Quality | 8 | 3 | 4 | 0 (+ 1 deferred L) |
| **Total** | **38** | **11** | **20** | **6** |

(Note: 2 deferred + 36 new = 38 total items)

## Suggested Version Mapping

| Version | Theme | Items | Rationale |
|---------|-------|-------|-----------|
| v024 | Deferred items + Proxy infrastructure + Rust core | BL-086, BL-141, items 1-4, 11-12 | LRN-019: build infrastructure first; resolve tech debt; Rust core ready for preview |
| v025 | Preview sessions + Visual aids | Items 5-10, 13-16 | Core preview engine + thumbnails/waveforms; enables all playback features |
| v026 | Observability + GUI Preview Player | Items 17-25 | Metrics, health, graceful degradation + frontend player with controls |
| v027 | GUI Theater Mode + Integration + Quality | Items 26-36 | Theater mode, timeline sync, tests, UAT journeys, design doc updates |
