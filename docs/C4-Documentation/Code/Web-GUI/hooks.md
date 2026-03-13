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
- **Used by:** Shell (initializes), DashboardPage (listens for activity)

**Connection flow:**
1. New connection via `new WebSocket(url)`
2. On open: reset retry count, set state to 'connected'
3. On message: update lastMessage (subscribers listen to this)
4. On close: set state to 'reconnecting', schedule reconnect with backoff
5. On error: just trigger close (reconnect logic in onclose)

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
    end
    subgraph "Real-time"
        H6[useWebSocket]
        H7[useActivityStore]
    end
    subgraph "Processing"
        H8[useDebounce]
        H9[useEffectPreview]
    end

    H8 --> H9
    H9 --> "effectPreviewStore"
    H6 --> H7
    H1 -->|Clip data| H2
    H3 -->|Effect definitions| H9

    class H1,H2,H3,H4,H5 fetch
    class H6,H7 realtime
    class H8,H9 processing
```

