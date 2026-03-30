# Web GUI

## Purpose

The Web GUI component is a React single-page application (SPA) that provides the complete browser-based user interface for the stoat-and-ferret video editor. It manages the full user workflow across six domain pages: system health dashboard, video library, project and clip management, effects and transitions workshop, interactive timeline with layout composition, and HLS video preview with theater mode. It communicates with the API Gateway exclusively over HTTP/JSON and WebSocket.

## Responsibilities

- Render and route between six feature pages via React Router within a persistent Shell layout
- Maintain domain-specific UI state in Zustand stores with clear separation between loading, error, and data states
- Fetch and cache data from the API Gateway with debounce, stale-request prevention, and automatic refetch after mutations
- Establish and maintain a persistent WebSocket connection to the API Gateway with exponential-backoff reconnection
- Display real-time WebSocket events in an activity log and surface system health status and Prometheus metrics
- Provide schema-driven form generation for effect parameter configuration driven by JSON schemas from the API
- Visualize the project timeline with a canvas-style component showing tracks, positioned clips, a zoom-responsive time ruler, and a playhead indicator
- Support multi-input layout composition with API-fetched preset selection, 16:9 visual preview, and manual coordinate editing
- Play HLS video previews with quality selection, seek support, and theater mode with auto-hiding HUD
- Display proxy generation status on video cards in the library browser with WebSocket-driven updates
- Render audio waveforms as PNG background images fetched from the API
- Submit directory scan jobs as background operations and poll job status with a progress bar until completion
- Serve as a static asset bundle from the `/gui` path via API Gateway's SPA catch-all route

## Interfaces

### Provided Interfaces

The Web GUI presents a browser-based UI accessible at `/gui`. It has no programmatic API surface; all interfaces are user-facing.

### Required Interfaces

All communication with the API Gateway via HTTP/JSON and WebSocket:

| Domain | Endpoints Used |
|--------|---------------|
| Health | `GET /health/ready` (30s polling) |
| Metrics | `GET /metrics` (Prometheus text format, 30s polling) |
| Videos | `GET /api/v1/videos`, `GET /api/v1/videos/search`, `GET /api/v1/videos/{id}/thumbnail`, `POST /api/v1/videos/scan`, `GET /api/v1/jobs/{id}` |
| Filesystem | `GET /api/v1/filesystem/directories` (with `limit`, `offset`, `path` params) |
| Projects | `GET /api/v1/projects`, `POST /api/v1/projects`, `DELETE /api/v1/projects/{id}`, `GET /api/v1/projects/{id}/clips`, `POST /api/v1/projects/{id}/clips`, `PATCH /api/v1/projects/{id}/clips/{id}`, `DELETE /api/v1/projects/{id}/clips/{id}` |
| Effects | `GET /api/v1/effects`, `POST /api/v1/effects/preview`, `POST /api/v1/effects/preview/thumbnail`, `POST /api/v1/projects/{id}/clips/{id}/effects`, `PATCH /api/v1/projects/{id}/clips/{id}/effects/{index}`, `DELETE /api/v1/projects/{id}/clips/{id}/effects/{index}`, `POST /api/v1/projects/{id}/effects/transition` |
| Compose | `GET /api/v1/compose/presets`, `POST /api/v1/projects/{id}/compose/layout` |
| Timeline | `GET /api/v1/projects/{id}/timeline` |
| Preview | `POST /api/v1/projects/{id}/preview/start`, `GET /api/v1/preview/{session_id}`, `POST /api/v1/preview/{session_id}/seek`, `DELETE /api/v1/preview/{session_id}`, `GET /api/v1/preview/{session_id}/manifest.m3u8`, `GET /api/v1/preview/{session_id}/segment_{index}.ts`, `GET /api/v1/preview/cache` |
| Proxy | `GET /api/v1/videos/{id}/proxy` |
| Waveform | `GET /api/v1/videos/{id}/waveform.png` |
| Jobs | `GET /api/v1/jobs/{id}`, `POST /api/v1/jobs/{id}/cancel` |
| WebSocket | `WS /ws` — receives `HEARTBEAT`, `PROJECT_CREATED`, `SCAN_STARTED`, `SCAN_COMPLETED`, `TIMELINE_UPDATED`, `LAYOUT_APPLIED`, `AUDIO_MIX_CHANGED`, `TRANSITION_APPLIED`, `JOB_PROGRESS`, `PREVIEW_GENERATING`, `PREVIEW_READY`, `PREVIEW_SEEKING`, `PREVIEW_ERROR`, `AI_ACTION`, `RENDER_PROGRESS`, `PROXY_READY` |

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| App Shell | `gui/src/App.tsx`, `gui/src/main.tsx`, `gui/src/components/Shell.tsx`, `gui/src/components/Navigation.tsx` | React Router entry point, shell layout (header/main/footer), capability-checking navigation tab discovery |
| Pages | `gui/src/pages/` | Six route destinations: DashboardPage, LibraryPage, ProjectsPage, EffectsPage, TimelinePage, PreviewPage |
| Preview/Player Components | `gui/src/components/PreviewPlayer.tsx`, `gui/src/components/PlayerControls.tsx`, `gui/src/components/ProgressBar.tsx`, `gui/src/components/VolumeSlider.tsx`, `gui/src/components/SeekTooltip.tsx`, `gui/src/components/QualitySelector.tsx`, `gui/src/components/PreviewStatus.tsx` | HLS video player with HLS.js/Safari fallback, transport controls, quality switching, seek, volume |
| Theater Mode Components | `gui/src/components/theater/TheaterMode.tsx`, `TopHUD.tsx`, `BottomHUD.tsx`, `AIActionIndicator.tsx` | Fullscreen theater mode wrapper with auto-hiding HUD (3s timeout), AI action display, render progress |
| Timeline Components | `gui/src/components/Timeline*.tsx`, `gui/src/components/Playhead.tsx`, `gui/src/components/ZoomControls.tsx` | `TimelineCanvas`, `Track`, `TimelineClip`, `TimeRuler`, `Playhead`, `ZoomControls` — full interactive timeline visualization |
| Layout/Compose Components | `gui/src/components/Layout*.tsx`, `gui/src/components/LayerStack.tsx` | `LayoutSelector`, `LayoutPreview` (16:9 canvas), `LayerStack` with coordinate editing; presets fetched from API |
| Effect Components | `gui/src/components/Effect*.tsx`, `gui/src/components/FilterPreview.tsx`, `gui/src/components/TransitionPanel.tsx` | `EffectCatalog`, `EffectParameterForm` (schema-driven), `EffectStack`, `FilterPreview` with FFmpeg syntax highlighting, `TransitionPanel` |
| Library/Media Components | `gui/src/components/Video*.tsx`, `gui/src/components/Directory*.tsx`, `gui/src/components/ScanModal.tsx`, `gui/src/components/ClipSelector.tsx`, `gui/src/components/ClipFormModal.tsx`, `gui/src/components/AudioWaveform.tsx`, `gui/src/components/library/ProxyStatusBadge.tsx` | `VideoCard` with proxy status badge, `VideoGrid`, `DirectoryBrowser`, `ScanModal` with job polling, `ClipSelector`, `ClipFormModal`, `AudioWaveform` (PNG background), `ProxyStatusBadge` (WebSocket-driven) |
| Project Components | `gui/src/components/Project*.tsx` | `ProjectCard`, `ProjectList`, `ProjectDetails`, `CreateProjectModal` |
| Shared Components | `gui/src/components/Status*.tsx`, `gui/src/components/Health*.tsx`, `gui/src/components/Activity*.tsx`, etc. | `StatusBar`, `HealthIndicator`, `HealthCards`, `MetricsCards`, `ActivityLog`, `SearchBar`, `SortControls`, `DeleteConfirmation` |
| Custom Hooks | `gui/src/hooks/` | `useWebSocket` (auto-reconnect), `useHealth`, `useMetrics`, `useVideos`, `useProjects`, `useEffects`, `useEffectPreview`, `useDebounce`, `useFullscreen`, `useTheaterShortcuts`, `useTimelineSync`, `useJobProgress` |
| Zustand Stores | `gui/src/stores/` | `activityStore`, `clipStore`, `composeStore`, `effectCatalogStore`, `effectFormStore`, `effectPreviewStore`, `effectStackStore`, `libraryStore`, `projectStore`, `previewStore`, `theaterStore`, `timelineStore`, `transitionStore` |
| Types and Utilities | `gui/src/types/generated/types.ts`, `gui/src/types/generated/api-types.ts`, `gui/src/utils/timeline.ts` | `TimelineClip`, `Track`, `TimelineResponse`, `LayoutPosition`, `LayoutPreset` types; `timeToPixel()`, `pixelToTime()`, `getMarkerInterval()`, `formatRulerTime()` utilities |

## Key Behaviors

**Navigation Discovery:** The `Navigation` component probes all tab endpoints with HEAD requests on mount and renders only tabs whose endpoints respond (200 or 405). This provides graceful degradation if API features are partially available.

**WebSocket Auto-Reconnect:** `useWebSocket` uses exponential backoff (1s, 2s, 4s, ... up to 30s) to reconnect after disconnection. The connection is initialized at the Shell level so it persists across route changes and is shared by all pages.

**Schema-Driven Effect Forms:** `EffectParameterForm` walks `schema.properties` and renders the appropriate field type (number slider, string input, enum dropdown, boolean checkbox, color picker) purely from the JSON Schema. No field type is hardcoded.

**Stale Request Prevention:** All data-fetching hooks use a local `active` boolean flag. If a component unmounts before a fetch completes, `active` is set to false and the result is discarded, preventing state updates on unmounted components.

**Timeline Coordinate Math:** Clip and playhead positions are computed with `timeToPixel(time, zoom, scrollOffset)` using integer pixel arithmetic. The time ruler selects its marker interval dynamically from a candidate list to maintain 80–150px gaps between markers regardless of zoom level.

**Debounced Preview:** `useEffectPreview` debounces parameter changes by 300ms before calling `POST /api/v1/effects/preview`. This prevents excessive API calls as the user adjusts sliders.

**API-Fetched Presets:** Layout preset positions are fetched from `GET /api/v1/compose/presets` and cached in `composeStore`. The compose router supports both preset names and custom `positions` arrays with normalized coordinates (0.0–1.0).

**Job Polling Pattern:** `ScanModal` polls `GET /api/v1/jobs/{job_id}` every 1 second using `setInterval`. The interval is cleared and the callback is called once a terminal state (complete, cancelled, failed, or timeout) is reached. This triggers a video list refetch in the parent `LibraryPage`.

**HLS Preview Playback:** `PreviewPlayer` uses HLS.js for Chrome/Firefox and native `<video>` for Safari. Quality switching destroys the current session and creates a new one. Preview progress is tracked via WebSocket events (`PREVIEW_GENERATING`, `PREVIEW_READY`).

**Theater Mode:** `TheaterMode` wraps the preview player in a fullscreen container with an auto-hiding HUD. The HUD fades after 3 seconds of mouse inactivity. Keyboard shortcuts (Escape, Space, F, M, arrows, Home, End) are scoped to the theater container via `useTheaterShortcuts` to avoid input field conflicts.

**Proxy Status Indicators:** `ProxyStatusBadge` in the library browser shows a color-coded dot (green=ready, yellow=generating, gray=none) for each video. Status updates arrive via the `PROXY_READY` WebSocket event.

**Timeline-Preview Sync:** `useTimelineSync` provides debounced bidirectional synchronization between the timeline playhead position and the preview player position.

## Inter-Component Relationships

```
Browser (user)
    |
    | HTTP/JSON, WS
    v
Web GUI (React SPA at /gui)
    |-- REST API calls --> API Gateway
    |-- WebSocket events <-- API Gateway
    |
    |-- pages render via --> React Router (Shell / Outlet)
    |-- state managed by --> Zustand stores
    |-- data fetched by --> custom hooks (useVideos, useProjects, etc.)
    |-- real-time events --> useWebSocket --> ActivityLog, StatusBar
```

## Version History

| Version | Changes |
|---------|---------|
| v011-v012 | Initial SPA: app shell, pages (Dashboard, Library, Projects, Effects), shared hooks and stores |
| v013 | Added TimelinePage with `TimelineCanvas`, `Track`, `TimelineClip`, `TimeRuler`, `ZoomControls` (BL-110, BL-111) |
| v014 | Added `Playhead` component to timeline canvas; added layout preset panel with `LayoutSelector`, `LayoutPreview`, `LayerStack` (BL-111, BL-112) |
| v015 | Added `composeStore` fetching presets from `/api/v1/compose/presets`; `PRESET_POSITIONS` client data; `timelineStore` fetching from `/api/v1/projects/{id}/timeline` |
| v016-v017 | WebSocket event handling for `TIMELINE_UPDATED`, `LAYOUT_APPLIED`, `AUDIO_MIX_CHANGED`, `TRANSITION_APPLIED` reflected in activity log |
| v027 | Added PreviewPage with HLS playback and theater mode; added `previewStore` and `theaterStore`; added preview, theater, proxy status, and waveform components; added `useFullscreen`, `useTheaterShortcuts`, `useTimelineSync`, `useJobProgress` hooks; layout presets now fetched from API (removed hardcoded `presetPositions.ts`) |
