# C4 Code Level: Zustand Stores

**Source:** `gui/src/stores/`

**Component:** Web GUI

## Purpose

Centralized state management using Zustand. Each store manages domain-specific state (UI selections, fetched data, loading states) with actions for mutations and async operations.

## Code Elements

### activityStore

**Location:** `gui/src/stores/activityStore.ts` (line 19)

- **State:**
  - `entries: ActivityEntry[]` - Activity log entries (max 50)
- **Actions:**
  - `addEntry(entry: Omit<ActivityEntry, 'id'>)` - Prepend to entries, trim to 50
- **Used by:** ActivityLog component (receives from WebSocket messages)

**ActivityEntry:**
```typescript
interface ActivityEntry {
  id: string
  type: string              // Event type from WebSocket
  timestamp: string         // ISO string
  details: Record<string, unknown>  // Event payload
}
```

### clipStore

**Location:** `gui/src/stores/clipStore.ts` (line 46)

- **State:**
  - `clips: Clip[]` - Clips for current project
  - `isLoading: boolean`
  - `error: string | null`
- **Actions:**
  - `fetchClips(projectId)` - GET `/api/v1/projects/{id}/clips`
  - `createClip(projectId, data)` - POST + refetch
  - `updateClip(projectId, clipId, data)` - PATCH + refetch
  - `deleteClip(projectId, clipId)` - DELETE + refetch
  - `reset()` - Clear state
- **Used by:** ProjectDetails component for clip CRUD

### composeStore

**Location:** `gui/src/stores/composeStore.ts` (line 31)

- **State:**
  - `presets: LayoutPreset[]` - Available layout presets from API
  - `isLoading: boolean`
  - `error: string | null`
  - `selectedPreset: string | null` - Currently selected preset name
  - `customPositions: LayoutPosition[]` - Manual position overrides
- **Actions:**
  - `fetchPresets()` - GET `/api/v1/compose/presets`
  - `selectPreset(name)` - Select preset by name, load positions from API
  - `setCustomPositions(positions)` - Direct custom position override
  - `updateCustomPosition(index, field, value)` - Update single field with clamping
  - `getActivePositions()` - Return selected preset positions or custom positions
  - `reset()` - Clear state
- **Used by:** LayoutSelector, LayoutPreview, LayerStack in TimelinePage

**Key Detail:** `updateCustomPosition` clamps width/height/x/y to [0,1], rounds z_index. Presets are now fetched from API rather than hardcoded client-side.

### effectCatalogStore

**Location:** `gui/src/stores/effectCatalogStore.ts` (line 16)

- **State:**
  - `searchQuery: string`
  - `selectedCategory: string | null` - 'video', 'audio', 'transition', or null
  - `selectedEffect: string | null` - Effect type identifier
  - `viewMode: 'grid' | 'list'`
- **Actions:**
  - `setSearchQuery(query)`
  - `setSelectedCategory(category)`
  - `selectEffect(effectType)`
  - `toggleViewMode()`
- **Used by:** EffectCatalog component in EffectsPage

### effectFormStore

**Location:** `gui/src/stores/effectFormStore.ts` (line 51)

- **State:**
  - `parameters: Record<string, unknown>` - Current form field values
  - `validationErrors: Record<string, string>` - Per-field error messages
  - `schema: ParameterSchema | null` - JSON schema defining the form
  - `isDirty: boolean` - Whether any parameter changed from default
- **Actions:**
  - `setParameter(key, value)` - Update single parameter, set isDirty
  - `setSchema(schema)` - Load new schema, populate defaults from schema
  - `setValidationErrors(errors)` - Update validation messages
  - `resetForm()` - Clear all fields, errors, schema
- **Used by:** EffectParameterForm component; populated from Effect.parameter_schema

**Schema Extraction:** `defaultsFromSchema()` walks schema.properties and extracts default values

### effectPreviewStore

**Location:** `gui/src/stores/effectPreviewStore.ts` (line 17)

- **State:**
  - `filterString: string` - Generated FFmpeg filter string
  - `isLoading: boolean` - Preview API call in flight
  - `error: string | null`
- **Actions:**
  - `setFilterString(str)` - Set filter, clear error
  - `setLoading(isLoading)`
  - `setError(error)` - Set error, clear loading
  - `reset()` - Clear all
- **Used by:** FilterPreview component; updated by useEffectPreview hook

### effectStackStore

**Location:** `gui/src/stores/effectStackStore.ts` (line 31)

- **State:**
  - `selectedClipId: string | null` - Currently selected clip
  - `effects: AppliedEffect[]` - Effects on selected clip
  - `isLoading: boolean`
  - `error: string | null`
- **Actions:**
  - `selectClip(clipId)` - Set selected clip, clear effects
  - `setEffects(effects)`
  - `setLoading(isLoading)`
  - `setError(error)`
  - `fetchEffects(projectId, clipId)` - GET `/api/v1/projects/{id}/clips` (finds clip by id)
  - `removeEffect(projectId, clipId, index)` - DELETE `/api/v1/projects/{id}/clips/{id}/effects/{index}` + refetch
  - `reset()`
- **Used by:** EffectStack component; displays applied effects with edit/remove UI

**AppliedEffect:**
```typescript
interface AppliedEffect {
  effect_type: string
  parameters: Record<string, unknown>
  filter_string: string      // Generated FFmpeg filter
}
```

### libraryStore

**Location:** `gui/src/stores/libraryStore.ts` (line 18)

- **State:**
  - `searchQuery: string`
  - `sortField: SortField` - 'date' | 'name' | 'duration'
  - `sortOrder: SortOrder` - 'asc' | 'desc'
  - `page: number` - 0-indexed
  - `pageSize: number` - Default 20
- **Actions:**
  - `setSearchQuery(query)` - Resets page to 0
  - `setSortField(field)` - Resets page to 0
  - `setSortOrder(order)` - Resets page to 0
  - `setPage(page)`
- **Used by:** LibraryPage; params passed to useVideos

### projectStore

**Location:** `gui/src/stores/projectStore.ts` (line 16)

- **State:**
  - `selectedProjectId: string | null`
  - `createModalOpen: boolean`
  - `deleteModalOpen: boolean`
  - `page: number` - Pagination for project list
  - `pageSize: number` - Default 20
- **Actions:**
  - `setSelectedProjectId(id)`
  - `setCreateModalOpen(open)`
  - `setDeleteModalOpen(open)`
  - `setPage(page)`
  - `resetPage()` - Reset to 0
- **Used by:** ProjectsPage for modal and selection state

### timelineStore

**Location:** `gui/src/stores/timelineStore.ts` (line 30)

- **State:**
  - `tracks: Track[]` - Timeline tracks with clips
  - `duration: number` - Total timeline length in seconds
  - `version: number` - Timeline version
  - `isLoading: boolean`
  - `error: string | null`
  - `selectedClipId: string | null`
  - `playheadPosition: number` - Current playhead in seconds
- **Actions:**
  - `fetchTimeline(projectId)` - GET `/api/v1/projects/{id}/timeline`
  - `selectClip(clipId)`
  - `setPlayheadPosition(position)`
  - `reset()`
- **Used by:** TimelineCanvas, Track, TimelineClip, Playhead components

### transitionStore

**Location:** `gui/src/stores/transitionStore.ts` (line 19)

- **State:**
  - `sourceClipId: string | null` - "From" clip
  - `targetClipId: string | null` - "To" clip
- **Actions:**
  - `selectSource(clipId)` - Set source, clear target
  - `selectTarget(clipId)`
  - `isReady()` - Getter: both source AND target selected
  - `reset()` - Clear both
- **Used by:** TransitionPanel (pair-mode clip selection)

### previewStore

**Location:** `gui/src/stores/previewStore.ts` (line 59)

- **State:**
  - `sessionId: string | null` - Active preview session ID
  - `status: PreviewStatus | null` - 'initializing' | 'generating' | 'ready' | 'seeking' | 'error' | 'expired'
  - `quality: PreviewQuality` - 'low' | 'medium' | 'high' (default: medium)
  - `position: number` - Current playback position in seconds
  - `duration: number` - Total video duration in seconds
  - `volume: number` - Volume level [0.0, 1.0]
  - `muted: boolean` - Audio mute state
  - `progress: number` - Generation progress [0.0, 1.0]
  - `error: string | null` - Error message

- **Actions:**
  - `connect(projectId)` - POST `/api/v1/projects/{id}/preview/start` with quality
  - `disconnect()` - DELETE `/api/v1/preview/{sessionId}`, reset state
  - `setQuality(projectId, quality)` - Delete old session, create new at quality
  - `setVolume(volume)` - Clamp to [0.0, 1.0]
  - `setMuted(muted)` - Toggle mute state
  - `setPosition(position)` - Clamp to [0, duration]
  - `setProgress(progress)` - Clamp to [0.0, 1.0]
  - `setStatus(status)` - Update preview status
  - `setError(error)` - Set error message (null to clear)
  - `reset()` - Clear all state to initial

- **Used by:** PreviewPage, PreviewPlayer, PlayerControls, QualitySelector, PreviewStatus, TheaterMode

### theaterStore

**Location:** `gui/src/stores/theaterStore.ts` (line 24)

- **State:**
  - `isFullscreen: boolean` - Whether theater mode is in fullscreen
  - `isHUDVisible: boolean` - Whether HUD overlay is visible
  - `lastMouseMoveTime: number` - Timestamp of last mouse movement (ms since epoch)

- **Actions:**
  - `enterTheater()` - Enter fullscreen, show HUD, set lastMouseMoveTime
  - `exitTheater()` - Exit fullscreen, reset to initial state
  - `showHUD()` - Show HUD overlay, set lastMouseMoveTime
  - `hideHUD()` - Hide HUD overlay
  - `reset()` - Reset to initial state

- **Used by:** TheaterMode, useFullscreen, useTheaterShortcuts

**Key Detail:** `isFullscreen` derived from browser `fullscreenchange` events (via useFullscreen hook), not button state. Ensures accuracy with ESC key, F11, etc.

## Dependencies

### Internal Dependencies

- Type imports: `Clip` (useProjects), `LayoutPosition`, `LayoutPreset`, `TimelineResponse`, `Track` (types)
- Zustand: `create` hook

### External Dependencies

- API endpoints (via fetch):
  - `/api/v1/projects/{id}/clips` (clipStore)
  - `/api/v1/compose/presets` (composeStore)
  - `/api/v1/projects/{id}/timeline` (timelineStore)

## Key Implementation Details

### Async Error Handling Pattern

All async actions follow this pattern:
```typescript
async actionName(params) {
  set({ isLoading: true, error: null })
  try {
    const res = await fetch(...)
    if (!res.ok) throw new Error(detail?.detail?.message ?? `Failed: ${res.status}`)
    set({ data: result, isLoading: false })
  } catch (err) {
    set({ error: err.message, isLoading: false })
  }
}
```

### Refetch Pattern

Create/Update/Delete actions refetch to get fresh data:
```typescript
deleteClip: async (projectId, clipId) => {
  await fetch(...)
  await get().fetchClips(projectId)  // Refetch
}
```

### Defaults from Schema (effectFormStore)

When effect selected, schema is loaded. `defaultsFromSchema()` extracts `.default` values from schema properties and populates form:
```typescript
setSchema: (schema) => set({
  schema,
  parameters: defaultsFromSchema(schema),  // Load defaults
  validationErrors: {},
  isDirty: false,
})
```

### Preset Data Structure (composeStore)

Presets loaded from API; positions lookup from `PRESET_POSITIONS` (hardcoded client data):
```typescript
selectPreset: (name) => {
  const positions = PRESET_POSITIONS[name]  // Client-side data
  if (positions) set({ selectedPreset: name, customPositions: positions })
}
```

## Relationships

```mermaid
---
title: Zustand Stores Architecture
---
classDiagram
    namespace Stores {
        class ActivityStore {
            entries: ActivityEntry[]
            addEntry()
        }
        class ClipStore {
            clips: Clip[]
            fetchClips(), createClip(), updateClip(), deleteClip()
        }
        class ComposeStore {
            presets: LayoutPreset[]
            selectedPreset: string | null
            customPositions: LayoutPosition[]
            selectPreset(), updateCustomPosition()
        }
        class EffectCatalogStore {
            searchQuery, selectedCategory, selectedEffect
            selectEffect(), setSearchQuery()
        }
        class EffectFormStore {
            parameters, schema, validationErrors
            setParameter(), setSchema()
        }
        class EffectPreviewStore {
            filterString, isLoading, error
            setFilterString()
        }
        class EffectStackStore {
            selectedClipId, effects
            selectClip(), fetchEffects(), removeEffect()
        }
        class LibraryStore {
            searchQuery, sortField, sortOrder, page
            setSearchQuery(), setSortField(), setSortOrder()
        }
        class ProjectStore {
            selectedProjectId, page
            setSelectedProjectId(), setPage()
        }
        class TimelineStore {
            tracks, duration, selectedClipId, playheadPosition
            fetchTimeline(), selectClip(), setPlayheadPosition()
        }
        class TransitionStore {
            sourceClipId, targetClipId
            selectSource(), selectTarget(), isReady()
        }
        class PreviewStore {
            sessionId, status, quality
            position, duration, volume, muted
            progress, error
            connect(), disconnect(), setQuality()
        }
        class TheaterStore {
            isFullscreen, isHUDVisible
            lastMouseMoveTime
            enterTheater(), exitTheater(), showHUD(), hideHUD()
        }
    }

    EffectFormStore --> EffectCatalogStore : "schema from selected effect"
    EffectPreviewStore --> EffectFormStore : "triggered by parameter changes"
    EffectStackStore --> ClipStore : "uses clip data"
    PreviewStore --> ProjectStore : "selectedProjectId"
    PreviewStore --> TimelineStore : "syncs playhead position"
    TheaterStore -.->|derives from fullscreenchange event|"Fullscreen API"
```

