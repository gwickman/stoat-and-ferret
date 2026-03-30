# C4 Code Level: Custom React Hooks

**Source:** `gui/src/hooks/`

**Component:** Web GUI

## Purpose

Custom hooks encapsulate data fetching, polling, WebSocket management, and other reusable logic. All hooks follow React conventions (cleanup, dependencies, state management).

## Code Elements

### useDebounce

**Location:** `gui/src/hooks/useDebounce.ts` (line 3)

```typescript
useDebounce<T>(value: T, delayMs = 300): T
```

- **Purpose:** Debounce value changes
- **Implementation:** setTimeout + cleanup in useEffect
- **Usage:** `const debouncedQuery = useDebounce(searchQuery, 300)`
- **Returns:** Debounced value (updated after delay with no new changes)
- **Used by:** LibraryPage (search), useEffectPreview

### useEffectPreview

**Location:** `gui/src/hooks/useEffectPreview.ts` (line 14)

```typescript
useEffectPreview(): void
```

- **Purpose:** Watch selected effect + form parameters, debounce 300ms, fetch preview
- **Dependencies:** selectedEffect, debouncedParams (from useDebounce)
- **Flow:**
  1. Watch `useEffectCatalogStore.selectedEffect`
  2. Watch `useEffectFormStore.parameters` (debounced via useDebounce)
  3. POST `/api/v1/effects/preview` with effect_type + parameters
  4. Update `useEffectPreviewStore.filterString` with response
- **Error handling:** Sets error message, clears on success
- **Cleanup:** Aborts stale requests via `active` flag
- **Used by:** EffectsPage (called unconditionally)

### useEffects

**Location:** `gui/src/hooks/useEffects.ts` (line 45)

```typescript
useEffects(): UseEffectsResult
// Returns: { effects: Effect[], loading, error, refetch }
```

- **Purpose:** Fetch effects catalog from API once on mount
- **Endpoint:** GET `/api/v1/effects`
- **Dependencies:** fetchKey (refetch trigger)
- **Exports:**
  - `deriveCategory(effectType)` - Helper to classify effects:
    - `audio_*` or `volume` or `acrossfade` → 'audio'
    - `xfade` → 'transition'
    - else → 'video'
- **Used by:** EffectsPage, EffectCatalog, TransitionPanel

**Effect interface:**
```typescript
interface Effect {
  effect_type: string
  name: string
  description: string
  parameter_schema: Record<string, unknown>  // JSON Schema
  ai_hints: Record<string, string>
  filter_preview: string                     // Example FFmpeg filter
}
```

### useHealth

**Location:** `gui/src/hooks/useHealth.ts` (line 26)

```typescript
useHealth(intervalMs = 30_000): HealthState
// Returns: { status: 'healthy' | 'degraded' | 'unhealthy', checks }
```

- **Purpose:** Poll health endpoint at regular interval
- **Endpoint:** GET `/health/ready`
- **Polling:** Default 30s, can customize via param
- **Status mapping:**
  - response.status === 'ok' → 'healthy'
  - response.status === 'degraded' → 'degraded'
  - else → 'unhealthy'
- **Used by:** DashboardPage, HealthIndicator

**HealthState:**
```typescript
interface HealthState {
  status: HealthStatus
  checks: Record<string, HealthCheck>  // Per-service status
}
```

### useMetrics

**Location:** `gui/src/hooks/useMetrics.ts` (line 40)

```typescript
useMetrics(intervalMs = 30_000): Metrics
// Returns: { requestCount, avgDurationMs }
```

- **Purpose:** Poll Prometheus metrics endpoint
- **Endpoint:** GET `/metrics` (Prometheus text format)
- **Parsing:** `parsePrometheus()` extracts:
  - `http_requests_total` → requestCount
  - `http_request_duration_seconds_sum / _count` → avgDurationMs (converted to ms)
- **Polling:** Default 30s
- **Used by:** DashboardPage, MetricsCards

### useProjects

**Location:** `gui/src/hooks/useProjects.ts` (line 47)

```typescript
useProjects(options: UseProjectsOptions): UseProjectsResult
// Returns: { projects, total, loading, error, refetch }
```

- **Purpose:** Fetch paginated projects list
- **Endpoint:** GET `/api/v1/projects?limit={pageSize}&offset={page*pageSize}`
- **Options:** `{ page?: number, pageSize?: number }`
- **Dependencies:** page, pageSize, fetchKey

**Exported helpers:**

- `createProject(data)` - POST `/api/v1/projects`
- `deleteProject(id)` - DELETE `/api/v1/projects/{id}`
- `fetchClips(projectId)` - GET `/api/v1/projects/{id}/clips` → `{ clips, total }`
- `createClip(projectId, data)` - POST `/api/v1/projects/{id}/clips`
- `updateClip(projectId, clipId, data)` - PATCH `/api/v1/projects/{id}/clips/{id}`
- `deleteClip(projectId, clipId)` - DELETE `/api/v1/projects/{id}/clips/{id}`

**Project interface:**
```typescript
interface Project {
  id: string
  name: string
  output_width, output_height, output_fps: number
  created_at, updated_at: string
}
```

**Clip interface:**
```typescript
interface Clip {
  id, project_id, source_video_id: string
  in_point, out_point, timeline_position: number
  created_at, updated_at: string
}
```

- **Used by:** ProjectsPage, EffectsPage, ClipFormModal

### useVideos

**Location:** `gui/src/hooks/useVideos.ts` (line 80)

```typescript
useVideos(options: UseVideosOptions): UseVideosResult
// Returns: { videos, total, loading, error, refetch }
```

- **Purpose:** Fetch videos with search/sort/pagination
- **Options:**
  - `searchQuery, sortField, sortOrder, page, pageSize`
- **Endpoints:**
  - If searchQuery: GET `/api/v1/videos/search?q={query}&limit={pageSize}`
  - Else: GET `/api/v1/videos?limit={pageSize}&offset={page*pageSize}`
- **Client-side sorting:** `sortVideos()` sorts after fetch by name/date/duration
- **Dependencies:** searchQuery, sortField, sortOrder, page, pageSize, fetchKey

**Video interface:**
```typescript
interface Video {
  id, path, filename: string
  duration_frames: number
  frame_rate_numerator, frame_rate_denominator: number
  width, height: number
  video_codec, audio_codec: string | null
  file_size: number
  thumbnail_path: string | null
  created_at, updated_at: string
}
```

- **Used by:** LibraryPage, ClipFormModal

### useWebSocket

**Location:** `gui/src/hooks/useWebSocket.ts` (line 14)

```typescript
useWebSocket(url: string): WebSocketHook
// Returns: { state, send, lastMessage }
```

- **Purpose:** Establish and maintain WebSocket connection with auto-reconnect
- **Connection state:**
  - `connected` - Connection open
  - `disconnecting` - Closed but may retry
  - `reconnecting` - Waiting for reconnect
- **Auto-reconnect logic:**
  - Base delay: 1s
  - Exponential backoff: `Math.min(BASE_DELAY * 2^retryCount, 30s)`
  - Resets retry count on successful connect
- **Cleanup:** Properly closes connection and clears timers on unmount
- **API:**
  - `state: ConnectionState` - Current connection status
  - `lastMessage: MessageEvent | null` - Most recent message received
  - `send(data)` - Send string to server (no-op if not connected)
- **Used by:** Shell (initializes), DashboardPage (listens for activity), TheaterMode (AI actions, render progress), ProxyStatusBadge (proxy updates)

**Connection flow:**
1. New connection via `new WebSocket(url)`
2. On open: reset retry count, set state to 'connected'
3. On message: update lastMessage (subscribers listen to this)
4. On close: set state to 'reconnecting', schedule reconnect with backoff
5. On error: just trigger close (reconnect logic in onclose)

### useFullscreen

**Location:** `gui/src/hooks/useFullscreen.ts` (line 8)

```typescript
useFullscreen(containerRef: React.RefObject<HTMLElement | null>): {
  enter: () => Promise<void>
  exit: () => Promise<void>
}
```

- **Purpose:** Wrapper around Fullscreen API with state synchronization
- **Features:**
  - Derives fullscreen state from browser fullscreenchange events (not button state)
  - Syncs state with theaterStore via enterTheater/exitTheater actions
  - Handles API errors gracefully (e.g., permission denied)
- **Implementation:**
  - On mount: add fullscreenchange listener
  - When fullscreen enters: call `enterTheater()`
  - When fullscreen exits: call `exitTheater()`
  - `enter()`: Call `requestFullscreen()` on container element
  - `exit()`: Call `document.exitFullscreen()`
- **Used by:** PreviewPage (via TheaterMode)

**Event-Driven State:** State derived from browser fullscreenchange event, ensuring accuracy even with ESC key, F11, other fullscreen triggers (NFR-002).

### useTheaterShortcuts

**Location:** `gui/src/hooks/useTheaterShortcuts.ts` (line 26)

```typescript
useTheaterShortcuts(options: UseTheaterShortcutsOptions): void
```

**Options:**
```typescript
interface UseTheaterShortcutsOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>
  onExit: () => void
  onToggleFullscreen: () => void
  enabled: boolean
}
```

- **Purpose:** Keyboard shortcuts for theater mode playback control
- **Bindings (when enabled && not in input field):**
  - Space: Play/pause
  - Escape: Exit theater
  - F: Toggle fullscreen
  - M: Mute/unmute
  - ArrowLeft/Right: Seek ±5s
  - Home/End: Jump to start/end
- **Input Protection:** Ignores shortcuts when focused on INPUT, TEXTAREA, SELECT (FR-007)
- **State Sync:** All actions update previewStore (position, muted) to keep UI consistent
- **Used by:** TheaterMode component

### useTimelineSync

**Location:** `gui/src/hooks/useTimelineSync.ts` (line 18)

```typescript
useTimelineSync(videoRef: React.RefObject<HTMLVideoElement | null>): {
  seekFromTimeline: (pos: number) => void
}
```

- **Purpose:** Bidirectional sync between preview player and timeline playhead
- **Behavior:**
  - Player → Timeline: Updates playheadPosition when video position changes (debounced 100ms, threshold 0.5s)
  - Timeline → Player: Seeks video element to given position via seekFromTimeline
  - Uses `isSeeking` ref guard to prevent infinite update loops
- **Debounce:** 100ms delay to avoid excessive updates
- **Threshold:** Only sync if position differs by > 0.5 seconds
- **Used by:** PreviewPage

**Key Constants:**
- `SYNC_DEBOUNCE_MS = 100` - Debounce interval
- `SYNC_THRESHOLD_S = 0.5` - Minimum position difference to trigger sync

### useJobProgress

**Location:** `gui/src/hooks/useJobProgress.ts` (line 10)

```typescript
useJobProgress(jobId: string | null, intervalMs?: number): JobProgress
// Returns: { progress, status, isComplete, error }
```

- **Purpose:** Poll job status endpoint for long-running operations (preview generation, rendering)
- **Behavior:**
  - Polls `/api/v1/jobs/{jobId}` at regular intervals (default 1000ms)
  - Stops polling when jobId is null or job completes
  - Tracks progress percentage, status, and completion state
  - Handles errors gracefully
- **Status Values:** 'pending' | 'running' | 'complete' | 'failed' | 'cancelled' | 'timeout'
- **Used by:** ScanModal (directory scan), potentially for preview generation

**Polling Pattern:**
1. On mount: Start interval polling if jobId provided
2. Each poll: GET `/api/v1/jobs/{jobId}`, update state
3. On completion (complete/failed/cancelled/timeout): Stop polling
4. On unmount: Clear interval, prevent memory leak

## Dependencies

### Internal Dependencies

- **Type imports:** Project, Clip, Video (from hooks themselves)
- **Store imports:** useEffectCatalogStore, useEffectFormStore, useEffectPreviewStore
- **Data imports:** None (utilities only)

### External Dependencies

- React: `useState`, `useEffect`, `useCallback`, `useRef`
- Native Web APIs: `fetch`, `WebSocket`, `setInterval`, `setTimeout`
- Prometheus format parsing (regex-based)

## Key Implementation Details

### Stale Request Prevention

All fetch hooks use an `active` flag pattern:
```typescript
useEffect(() => {
  let active = true
  async function fetch() {
    if (active) setState(result)  // Only update if still mounted
  }
  return () => { active = false }  // Cleanup cancels updates
}, [deps])
```

This prevents memory leaks when component unmounts mid-fetch.

### Prometheus Parsing

`parsePrometheus()` regex-matches:
- `http_requests_total` lines → sum values
- `http_request_duration_seconds_sum` → sum durations
- `http_request_duration_seconds_count` → count samples
- Calculate avg: `sum / count * 1000` (convert s to ms)

### Effect Categorization

`deriveCategory()` classifies effects for UI:
- Prefix-based: `audio_*` effects are 'audio'
- Special names: `volume`, `acrossfade` are 'audio'
- Transition check: `xfade` is 'transition'
- Default: 'video'

### WebSocket Reconnection

Uses exponential backoff with max cap:
```typescript
const delay = Math.min(BASE_DELAY * 2 ** retryCount, MAX_DELAY)
// 1s, 2s, 4s, 8s, ..., up to 30s
```

Resets on successful connect, allowing infinite retry.

## Relationships

```mermaid
---
title: Hooks Dependency Graph
---
flowchart LR
    subgraph "Data Fetching"
        H1[useProjects]
        H2[useVideos]
        H3[useEffects]
        H4[useHealth]
        H5[useMetrics]
        H10[useJobProgress]
    end
    subgraph "Real-time"
        H6[useWebSocket]
        H7[useActivityStore]
    end
    subgraph "Processing"
        H8[useDebounce]
        H9[useEffectPreview]
    end
    subgraph "Theater & Preview"
        H11[useFullscreen]
        H12[useTheaterShortcuts]
        H13[useTimelineSync]
    end

    H8 --> H9
    H9 --> "effectPreviewStore"
    H6 --> H7
    H6 --> H12
    H1 -->|Clip data| H2
    H3 -->|Effect definitions| H9
    H11 --> "theaterStore"
    H12 --> "previewStore"
    H13 --> "previewStore"
    H13 --> "timelineStore"
    H10 -.->|polls job status|"Long-running ops"

    class H1,H2,H3,H4,H5,H10 fetch
    class H6,H7 realtime
    class H8,H9 processing
    class H11,H12,H13 theater
```

