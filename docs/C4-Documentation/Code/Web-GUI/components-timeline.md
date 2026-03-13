# C4 Code Level: Timeline Components

**Source:** `gui/src/components/Timeline*.tsx`, `gui/src/components/Playhead.tsx`, `gui/src/components/ZoomControls.tsx`

**Component:** Web GUI

## Purpose

Interactive timeline visualization with tracks, clips, zoom, scrolling, and playhead positioning. Multi-level component hierarchy for canvas rendering.

## Code Elements

### TimelineCanvas

**Location:** `gui/src/components/TimelineCanvas.tsx` (line 19)

**Props:**
```typescript
interface TimelineCanvasProps {
  tracks: TrackType[]
  duration: number
}
```

- **Purpose:** Main timeline container with scroll area and zoom controls
- **State:**
  - `zoom` (1 = default, 0.1 min, 10 max, 0.25 step)
  - `scrollOffset` (tracks horizontal scroll position)
- **Layout:**
  - Header with duration display and ZoomControls
  - Scrollable area containing:
    - TimeRuler (above tracks)
    - Tracks list (sorted by z_index)
    - Playhead overlay (z-20, pointer-events-none)

**Features:**
- Zoom in/out: +0.25 per click, within bounds
- Zoom reset: Returns to 1.0
- Horizontal scroll tracking via onScroll
- Sorts tracks by z_index before rendering
- Empty state: "No tracks on the timeline. Add clips to get started."

**Helpers:**
- `MIN_ZOOM = 0.1`, `MAX_ZOOM = 10`, `ZOOM_STEP = 0.25`

### Track

**Location:** `gui/src/components/Track.tsx` (line 13)

**Props:**
```typescript
interface TrackProps {
  track: TrackType
  zoom: number
  scrollOffset: number
  selectedClipId: string | null
  onSelectClip: (clipId: string) => void
}
```

- **Renders:** Single timeline track with label and clips
- **Layout:**
  - Fixed-width label (w-32) showing track name, muted/locked indicators
  - Flex-1 content area (relative positioning for clips)
- **Label content:** Track name, optional "M" for muted, "L" for locked
- **Clip rendering:** Maps track.clips to TimelineClip components, passing positioning props

### TimelineClip

**Location:** `gui/src/components/TimelineClip.tsx` (line 13)

**Props:**
```typescript
interface TimelineClipProps {
  clip: ClipType
  zoom: number
  scrollOffset: number
  isSelected: boolean
  onSelect: (clipId: string) => void
}
```

- **Renders:** Positioned clip rectangle on track
- **Positioning:**
  - `start = clip.timeline_start ?? 0`
  - `end = clip.timeline_end ?? start + (out_point - in_point)`
  - `left = timeToPixel(start, zoom, scrollOffset)`
  - `width = timeToPixel(end) - timeToPixel(start)`
- **Styling:**
  - Selected: blue-400 border-2, blue-700/80 bg
  - Unselected: gray-600 border, indigo-800/70 bg, hover lighter
- **Content:** Duration in seconds (truncated)
- **Interaction:** Click or spacebar to select

### TimeRuler

**Location:** `gui/src/components/TimeRuler.tsx` (line 13)

**Props:**
```typescript
interface TimeRulerProps {
  duration: number
  zoom: number
  scrollOffset: number
  canvasWidth: number
  pixelsPerSecond?: number
}
```

- **Purpose:** Horizontal time ruler showing markers above tracks
- **Features:**
  - Zoom-responsive marker interval (via `getMarkerInterval()`)
  - Only renders visible markers (within canvas + 10px buffer)
  - Markers start from first visible (or just before) viewport
- **Marker layout:**
  - Tick mark (h-2)
  - Time label (e.g., "0:00", "1:30.5")
- **Helper:** `formatRulerTime(seconds)` → "M:SS" or "M:SS.d"

### Playhead

**Location:** `gui/src/components/Playhead.tsx` (line 11)

**Props:**
```typescript
interface PlayheadProps {
  position: number       // in seconds
  zoom: number
  scrollOffset: number
  height: number         // full track height
}
```

- **Renders:** Vertical red line at playhead position
- **Positioning:** `x = timeToPixel(position, zoom, scrollOffset)`
- **Styling:** w-0.5, bg-red-500, pointer-events-none (doesn't block interaction), z-20
- **Height:** Full track stack height

### ZoomControls

**Location:** `gui/src/components/ZoomControls.tsx` (line 11)

**Props:**
```typescript
interface ZoomControlsProps {
  zoom: number
  onZoomIn: () => void
  onZoomOut: () => void
  onReset: () => void
  minZoom?: number
  maxZoom?: number
}
```

- **Renders:** Three buttons (out, reset, in) in horizontal flex
- **Zoom out (−):** Disabled if zoom <= minZoom
- **Reset:** Shows current zoom as percentage (e.g., "100%", "250%")
- **Zoom in (+):** Disabled if zoom >= maxZoom

## Dependencies

### Internal Dependencies

- **Type imports:** Track, TimelineClip (from types/timeline)
- **Stores:** useTimelineStore (TimelineCanvas)
- **Utils:** timeToPixel, pixelToTime, getMarkerInterval, formatRulerTime (utils/timeline)
- **Components:** TimeRuler, Track, Playhead, ZoomControls

### External Dependencies

- React: `useState`, `useRef`, `useCallback`
- Tailwind CSS for styling

## Key Implementation Details

### Coordinate Math (utils/timeline)

Three core functions:

1. **timeToPixel(time, zoom, scrollOffset, pps)**
   - Formula: `time * pps * zoom - scrollOffset`
   - Converts seconds to screen x-coordinate

2. **pixelToTime(pixel, zoom, scrollOffset, pps)**
   - Formula: `(pixel + scrollOffset) / (pps * zoom)`
   - Inverse: converts screen x back to seconds

3. **getMarkerInterval(zoom, pps)**
   - Returns interval in seconds for ruler markers
   - Intervals: [0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300]
   - Chooses interval such that gap is 80-150px at current zoom
   - Default 100 pps (BASE_PIXELS_PER_SECOND)

### Clip Duration Calculation

```typescript
const start = clip.timeline_start ?? 0
const end = clip.timeline_end ?? start + (clip.out_point - clip.in_point)
const duration = end - start
```

Falls back to out_point - in_point if timeline_start/end not set.

### Viewport-Aware Marker Rendering

TimeRuler only renders visible markers:
```typescript
const startTime = Math.max(0, Math.floor(scrollOffset / (pps * zoom) / interval) * interval)
for (let t = startTime; t <= duration; t += interval) {
  const x = timeToPixel(t, zoom, scrollOffset, pps)
  if (x > canvasWidth + 10) break
  if (x >= -10) result.push({ time: t, x })
}
```

Efficiency: O(visible markers) not O(duration).

### Track Z-Index Ordering

TimelineCanvas sorts tracks before rendering:
```typescript
const sortedTracks = [...tracks].sort((a, b) => a.z_index - b.z_index)
```

Each Track sets `style={{ order: track.z_index }}` for flexbox ordering.

### Scroll Offset Tracking

TimelineCanvas listens to scroll and updates offset:
```typescript
const handleScroll = useCallback(() => {
  if (scrollRef.current) {
    setScrollOffset(scrollRef.current.scrollLeft)
  }
}, [])
```

Offset passed to all child components for consistent positioning.

### Playhead Overlay

Playhead is z-20 with `pointer-events-none`:
- Red color (bg-red-500)
- 2px width (w-0.5)
- Full height (sortedTracks.length * 48)
- Positioned via `left` style property
- Doesn't block clip clicking due to pointer-events-none

## Relationships

```mermaid
---
title: Timeline Components Hierarchy
---
classDiagram
    namespace TimelineCanvas {
        class TimelineCanvas {
            zoom, scrollOffset state
            handles scroll, zoom
            render header + scroll area
        }
        class TimelineCanvasHeader {
            duration display
            ZoomControls
        }
        class TimelineScrollArea {
            relative container
            TimeRuler
            TrackList
            Playhead
        }
    }

    namespace TrackLevel {
        class Track {
            label (w-32)
            clips content area
        }
        class TimelineClip {
            positioned rect
            onSelect callback
        }
    }

    namespace RulerLevel {
        class TimeRuler {
            time markers
            zoom-responsive
        }
        class Playhead {
            vertical red line
        }
        class ZoomControls {
            in/out/reset buttons
        }
    }

    TimelineCanvas --> TimelineCanvasHeader
    TimelineCanvas --> TimelineScrollArea
    TimelineCanvasHeader --> ZoomControls
    TimelineScrollArea --> TimeRuler
    TimelineScrollArea --> "Track[]"
    TimelineScrollArea --> Playhead
    Track --> "TimelineClip[]"

    TimelineClip -.->|uses| "timeToPixel()"
    TimeRuler -.->|uses| "getMarkerInterval(), formatRulerTime()"
    Playhead -.->|uses| "timeToPixel()"
```

## Code Locations

- **TimelineCanvas.tsx**: Main container with zoom/scroll
- **Track.tsx**: Single track display
- **TimelineClip.tsx**: Clip rectangle with positioning
- **TimeRuler.tsx**: Time ruler with zoom-responsive markers
- **Playhead.tsx**: Vertical playhead indicator
- **ZoomControls.tsx**: Zoom buttons

## Utilities

- **utils/timeline.ts**: timeToPixel, pixelToTime, getMarkerInterval, formatRulerTime

