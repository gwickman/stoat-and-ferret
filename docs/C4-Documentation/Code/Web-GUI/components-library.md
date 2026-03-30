# C4 Code Level: Library & Media Components

**Source:** `gui/src/components/Video*.tsx`, `gui/src/components/Directory*.tsx`, `gui/src/components/ScanModal.tsx`, `gui/src/components/ClipSelector.tsx`, `gui/src/components/ClipFormModal.tsx`

**Component:** Web GUI

## Purpose

Video library management: display videos, search/sort/paginate, scan directories for new videos, and create clips from video sources.

## Code Elements

### VideoCard

**Location:** `gui/src/components/VideoCard.tsx` (line 23)

**Props:**
```typescript
interface VideoCardProps {
  video: Video
}
```

- **Renders:** Card with thumbnail, filename, duration badge
- **Layout:**
  - Thumbnail image (aspect-video, lazy-loaded)
  - Filename (truncated, title tooltip)
  - Duration badge (bottom-right, black bg)
- **Duration formatting:** `formatDuration(video)` → "H:MM:SS" or "M:SS"
- **Thumbnail URL:** `/api/v1/videos/{id}/thumbnail`
- **No interaction:** Passive display only

### VideoGrid

**Location:** `gui/src/components/VideoGrid.tsx` (line 10)

**Props:**
```typescript
interface VideoGridProps {
  videos: Video[]
  loading: boolean
  error: string | null
}
```

- **Renders:** Responsive grid of VideoCards
- **Layout:** 2 cols (mobile) → 3 (tablet) → 4 (md) → 5 (lg)
- **States:**
  - Loading: "Loading videos..."
  - Error: Error message
  - Empty: "No videos found. Scan a directory to add videos."

### DirectoryBrowser

**Location:** `gui/src/components/DirectoryBrowser.tsx` (line 19)

**Props:**
```typescript
interface DirectoryBrowserProps {
  onSelect: (path: string) => void
  onCancel: () => void
  initialPath?: string
}
```

- **Purpose:** Filesystem directory navigation modal
- **Features:**
  - Current path display
  - Up button (navigate to parent)
  - Directory list (clickable entries)
  - Select button (returns current path)
- **Endpoints:**
  - GET `/api/v1/filesystem/directories?path={encodedPath}`
  - Returns: `{ path, directories: [{ name, path }, ...] }`
- **Parent navigation:** Regex replace trailing path segment
- **Overlay:** Click outside to cancel (if not loading)

**State:**
- `currentPath` - Currently browsed directory
- `directories` - Subdirectories in current path
- `isLoading`, `error`

### ScanModal

**Location:** `gui/src/components/ScanModal.tsx` (line 20)

**Props:**
```typescript
interface ScanModalProps {
  open: boolean
  onClose: () => void
  onScanComplete: () => void
}
```

- **Purpose:** Asynchronous directory scan for video files
- **Flow:**
  1. User enters directory path (or uses DirectoryBrowser)
  2. Toggle "Scan subdirectories" (default true)
  3. Click "Start Scan" → POST request, get job_id
  4. Poll `/api/v1/jobs/{job_id}` every 1s for status/progress
  5. Show progress bar (0-100%)
  6. Handle completion (complete/cancelled/failed/timeout)

- **Job polling states:**
  - `pending` → show nothing yet
  - `running` → show progress bar
  - `complete` → success message, enable close
  - `cancelled` → cancelled message
  - `failed` / `timeout` → error message

- **Abort button:** POST `/api/v1/jobs/{job_id}/cancel` (cancelling state)

- **Cleanup:** Clears interval on unmount or close

- **Sub-modal:** DirectoryBrowser for path selection

### ClipSelector

**Location:** `gui/src/components/ClipSelector.tsx` (line 18)

**Props:**
```typescript
interface ClipSelectorProps {
  clips: Clip[]
  selectedClipId: string | null
  onSelect: (clipId: string) => void
  pairMode?: boolean
  selectedFromId?: string | null
  selectedToId?: string | null
  onSelectPair?: (clipId: string, role: 'from' | 'to') => void
}
```

- **Modes:**
  - **Single mode:** Select one clip (blue highlight)
  - **Pair mode:** Select source (FROM, green) then target (TO, orange)
- **Display:** Button list showing clip source_video_id, positions, in/out points
- **Empty state:** "No clips in this project. Add clips to get started."
- **Pair mode logic:**
  - First click: selects FROM
  - Second click (different clip): selects TO
  - TO selection calls `onSelectPair(clipId, 'to')`

### ProxyStatusBadge

**Location:** `gui/src/components/library/ProxyStatusBadge.tsx` (line 34)

**Props:**
```typescript
interface ProxyStatusBadgeProps {
  videoId: string
  proxyStatus?: ProxyStatusValue  // 'ready' | 'generating' | 'none'
}
```

- **Purpose:** Displays color-coded proxy generation status indicator
- **Status Colors:**
  - `ready` → green-500 (✓ Proxy available)
  - `generating` → yellow-500 (⟳ Proxy in progress)
  - `none` → gray-500 (— No proxy)
- **Display:** Small rounded dot (2.5x2.5) with title tooltip
- **Real-time Updates:** Listens to `proxy.ready` WebSocket events
- **Event Parsing:**
  ```typescript
  if (data.type === 'proxy.ready' && data.payload?.video_id === videoId) {
    setStatus('ready')
  }
  ```
- **Used by:** VideoCard component in VideoGrid

**Styling:** Inline-block rounded-full, title attribute shows full label

### AudioWaveform

**Location:** `gui/src/components/AudioWaveform.tsx` (line 8)

**Props:**
```typescript
interface AudioWaveformProps {
  videoId: string
}
```

- **Purpose:** Displays audio waveform as background for timeline audio tracks
- **Fetching:** GET `/api/v1/videos/{videoId}/waveform.png`
- **Features:**
  - Lazy loads PNG waveform image via fetch
  - Shows gradient fallback if image unavailable
  - Uses `URL.createObjectURL(blob)` for blob URL
  - Cancellation support to prevent updates after unmount
- **Styling:**
  - Success: Background image with 60% opacity
  - Fallback: Gradient (darker-to-lighter-to-darker gray)
  - Positioned absolutely within clip container

**Error Handling:** If fetch fails or image unavailable, shows fallback gradient instead of error

### ClipFormModal

**Location:** `gui/src/components/ClipFormModal.tsx` (line 14)

**Props:**
```typescript
interface ClipFormModalProps {
  mode: 'add' | 'edit'
  clip?: Clip
  projectId: string
  onClose: () => void
  onSaved: () => void
}
```

- **Purpose:** Add or edit clip within a project
- **Fields:**
  - Source Video (add mode only, dropdown)
  - In Point (frames, number)
  - Out Point (frames, number)
  - Timeline Position (frames, number)
- **Validation:**
  - All fields required (except source in edit mode)
  - Numeric fields: non-negative
  - out_point > in_point
  - Error messages display per-field
- **Mode:**
  - Add: Fetches all videos (up to 1000), auto-selects first if available
  - Edit: Pre-fills from clip data, hides source field
- **Submit:**
  - Add: POST `/api/v1/projects/{id}/clips`
  - Edit: PATCH `/api/v1/projects/{id}/clips/{id}`
  - On success: calls onSaved + onClose
  - On error: shows error message

**Dependencies:**
- `useVideos()` - Fetch available videos
- `useClipStore()` - createClip, updateClip actions

## Dependencies

### Internal Dependencies

- **Type imports:** Video (useVideos), Clip (useProjects)
- **Hooks:** useVideos, useClipStore
- **Components:** VideoCard (VideoGrid), DirectoryBrowser (ScanModal)
- **API functions:** createClip, updateClip (useProjects)

### External Dependencies

- React hooks: `useState`, `useEffect`, `useCallback`, `useRef`
- Native Web APIs: `fetch`, `setInterval`, `navigator.clipboard`
- Tailwind CSS for styling

## Key Implementation Details

### Duration Formatting (VideoCard)

```typescript
function formatDuration(video: Video): string {
  if (video.frame_rate_denominator === 0) return '0:00'
  const fps = video.frame_rate_numerator / video.frame_rate_denominator
  const totalSeconds = Math.floor(video.duration_frames / fps)
  // Format as H:MM:SS or M:SS
}
```

Handles zero FPS safely, converts frame count to time.

### Directory Navigation (DirectoryBrowser)

Up button navigates to parent:
```typescript
const parent = currentPath.replace(/[\\/][^\\/]+$/, '')
if (parent && parent !== currentPath) {
  fetchDirectories(parent)
}
```

Removes trailing path segment using regex (handles both / and \).

### Job Polling Pattern (ScanModal)

```typescript
pollRef.current = setInterval(async () => {
  const status: JobStatus = await fetch(`/api/v1/jobs/${job_id}`).json()
  setProgress(status.progress)
  if (status.status === 'complete') {
    cleanup()
    setScanStatus('complete')
    onScanComplete()  // Parent refetches videos
  }
  // Handle other statuses (cancelled, failed, timeout)
}, 1000)
```

Polls every 1 second; cleans up interval and calls callback on completion.

### Pair Mode Selection (ClipSelector)

```typescript
const handleClick = () => {
  if (!selectedFromId) {
    onSelectPair(clip.id, 'from')
  } else if (clip.id === selectedFromId) {
    return  // Can't deselect
  } else {
    onSelectPair(clip.id, 'to')
  }
}
```

State machine: empty → from selected → to selected.

### Video Pre-fetching (ClipFormModal)

```typescript
useEffect(() => {
  if (mode === 'add' && !sourceVideoId && videos.length > 0) {
    setSourceVideoId(videos[0].id)
  }
}, [mode, sourceVideoId, videos])
```

Auto-selects first video when list loads in add mode.

### Clip Form Validation

Real-time validation clearing on field change:
```typescript
const validate = useCallback((): string | null => {
  if (!sourceVideoId && mode === 'add') return 'Source video is required'
  const inVal = parseInt(inPoint, 10)
  const outVal = parseInt(outPoint, 10)
  if (outVal <= inVal) return 'Out point must be greater than in point'
  // ... more checks
}, [sourceVideoId, inPoint, outPoint, timelinePosition, mode])
```

Catches invalid ranges and required fields.

## Relationships

```mermaid
---
title: Library & Media Components
---
classDiagram
    namespace LibraryPage {
        class LibraryPage {
            useLibraryStore()
            useVideos()
            render SearchBar, SortControls, VideoGrid, ScanModal
        }
    }

    namespace VideoLibrary {
        class VideoCard {
            thumbnail, filename, duration
        }
        class VideoGrid {
            grid of VideoCards
        }
        class ScanModal {
            directory path input
            recursive toggle
            progress bar
            polling job status
        }
        class DirectoryBrowser {
            filesystem tree
            up/select navigation
        }
    }

    namespace ClipManagement {
        class ClipSelector {
            single or pair mode
            clip list buttons
        }
        class ClipFormModal {
            add/edit clip form
            video dropdown (add mode)
            frame positions
        }
        class ProjectDetails {
            uses ClipFormModal
            uses ClipSelector
        }
    }

    LibraryPage --> VideoGrid
    LibraryPage --> ScanModal
    VideoGrid --> VideoCard
    ScanModal --> DirectoryBrowser

    ProjectDetails --> ClipFormModal
    ProjectDetails --> ClipSelector
    EffectsPage --> ClipSelector

    ScanModal -.->|refetch| LibraryPage
    ClipFormModal -.->|callback| ProjectDetails
```

## Code Locations

- **VideoCard.tsx**: Individual video card display
- **VideoGrid.tsx**: Responsive grid layout
- **DirectoryBrowser.tsx**: Filesystem navigation modal
- **ScanModal.tsx**: Async directory scan with job polling
- **ClipSelector.tsx**: Clip selection (single or pair mode)
- **ClipFormModal.tsx**: Clip create/edit form

