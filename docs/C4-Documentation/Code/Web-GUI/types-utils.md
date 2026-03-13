# C4 Code Level: Types & Utilities

**Source:** `gui/src/types/timeline.ts`, `gui/src/utils/timeline.ts`, `gui/src/data/presetPositions.ts`

**Component:** Web GUI

## Purpose

Type definitions and utility functions for timeline/compose domain, coordinate calculations, and preset layout data.

## Code Elements

### Timeline Types

**Location:** `gui/src/types/timeline.ts`

#### TimelineClip

```typescript
export interface TimelineClip {
  id: string
  project_id: string
  source_video_id: string
  track_id: string | null
  timeline_start: number | null      // Seconds on timeline
  timeline_end: number | null        // Seconds on timeline
  in_point: number                   // Frames in source
  out_point: number                  // Frames in source
}
```

- Represents clip positioned on timeline
- Nullable timeline_start/end indicate not yet placed
- in_point/out_point define source range (in frames)

#### Track

```typescript
export interface Track {
  id: string
  project_id: string
  track_type: string
  label: string
  z_index: number
  muted: boolean
  locked: boolean
  clips: TimelineClip[]
}
```

- Contains multiple clips
- Ordered by z_index (0 = bottom, higher = top)
- muted/locked flags for UI state

#### TimelineResponse

```typescript
export interface TimelineResponse {
  project_id: string
  tracks: Track[]
  duration: number               // Total timeline in seconds
  version: number
}
```

- Complete timeline data from API
- Returned by GET `/api/v1/projects/{id}/timeline`

#### LayoutPosition

```typescript
export interface LayoutPosition {
  x: number
  y: number
  width: number
  height: number
  z_index: number
}
```

- Normalized position (all 0-1 except z_index)
- Represents relative placement on 16:9 canvas
- Supports layering via z_index

#### LayoutPreset

```typescript
export interface LayoutPreset {
  name: string
  description: string
  ai_hint: string
  min_inputs: number
  max_inputs: number
}
```

- Metadata for layout preset
- AI hint suggests use cases
- Constraints on input count

#### LayoutPresetListResponse

```typescript
export interface LayoutPresetListResponse {
  presets: LayoutPreset[]
  total: number
}
```

- API response from GET `/api/v1/compose/presets`

### Timeline Utilities

**Location:** `gui/src/utils/timeline.ts`

#### Constants

- `BASE_PIXELS_PER_SECOND = 100` - Default scaling at zoom 1.0

#### timeToPixel()

```typescript
export function timeToPixel(
  time: number,
  zoom: number,
  scrollOffset: number,
  pixelsPerSecond: number = BASE_PIXELS_PER_SECOND,
): number
```

- **Purpose:** Convert timeline seconds to screen x-coordinate
- **Formula:** `time * pixelsPerSecond * zoom - scrollOffset`
- **Params:**
  - `time` - Time in seconds
  - `zoom` - Zoom multiplier (1.0 = normal, 2.0 = 2x magnified)
  - `scrollOffset` - Horizontal scroll position in pixels
  - `pixelsPerSecond` - Default 100 (can customize)
- **Returns:** x-coordinate on screen
- **Usage:** Position clips, playhead, ruler markers

#### pixelToTime()

```typescript
export function pixelToTime(
  pixel: number,
  zoom: number,
  scrollOffset: number,
  pixelsPerSecond: number = BASE_PIXELS_PER_SECOND,
): number
```

- **Purpose:** Convert screen x-coordinate to timeline seconds (inverse of timeToPixel)
- **Formula:** `(pixel + scrollOffset) / (pixelsPerSecond * zoom)`
- **Safety:** Returns 0 if zoom or pixelsPerSecond is 0
- **Usage:** Calculate time from mouse position

#### getMarkerInterval()

```typescript
export function getMarkerInterval(
  zoom: number,
  pixelsPerSecond: number = BASE_PIXELS_PER_SECOND,
): number
```

- **Purpose:** Determine appropriate time interval for ruler markers at current zoom
- **Algorithm:**
  1. Calculate effective pixels per second: `effectivePps = pps * zoom`
  2. Target marker gap: 80-150 pixels
  3. Choose interval from [0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300] seconds
  4. First interval with gap >= 80px is chosen
  5. Fallback to 600s if all intervals too small
- **Returns:** Interval in seconds
- **Usage:** TimeRuler determines marker spacing

#### formatRulerTime()

```typescript
export function formatRulerTime(seconds: number): string
```

- **Purpose:** Format seconds for ruler display
- **Format:**
  - Whole seconds: "M:SS" (e.g., "1:30")
  - Fractional: "M:SS.d" (e.g., "0:00.5")
- **Logic:** If seconds % 1 === 0, no decimal; else show one decimal place
- **Padding:** seconds padStart to width 4 ("00" min)
- **Examples:**
  - 0 → "0:00"
  - 30 → "0:30"
  - 90 → "1:30"
  - 0.5 → "0:00.5"

### Preset Positions Data

**Location:** `gui/src/data/presetPositions.ts`

**Export:** `PRESET_POSITIONS: Record<string, LayoutPosition[]>`

Available presets:

| Preset | Description | Positions |
|--------|-------------|-----------|
| **PipTopLeft** | Picture-in-picture top-left | [Full (0,0,1,1,z:0), PiP (0.02,0.02,0.25,0.25,z:1)] |
| **PipTopRight** | Picture-in-picture top-right | [Full (0,0,1,1,z:0), PiP (0.73,0.02,0.25,0.25,z:1)] |
| **PipBottomLeft** | Picture-in-picture bottom-left | [Full (0,0,1,1,z:0), PiP (0.02,0.73,0.25,0.25,z:1)] |
| **PipBottomRight** | Picture-in-picture bottom-right | [Full (0,0,1,1,z:0), PiP (0.73,0.73,0.25,0.25,z:1)] |
| **SideBySide** | Left/right split | [Left (0,0,0.5,1,z:0), Right (0.5,0,0.5,1,z:0)] |
| **TopBottom** | Top/bottom split | [Top (0,0,1,0.5,z:0), Bottom (0,0.5,1,0.5,z:0)] |
| **Grid2x2** | 2x2 grid (4 inputs) | [TL (0,0,0.5,0.5,z:0), TR (0.5,0,0.5,0.5,z:0), BL (0,0.5,0.5,0.5,z:0), BR (0.5,0.5,0.5,0.5,z:0)] |

**Usage:** composeStore loads positions for selected preset

## Dependencies

### Internal Dependencies

None (pure types and utilities)

### External Dependencies

None (TypeScript only, no runtime deps)

## Key Implementation Details

### Coordinate System

All timeline math uses consistent coordinate system:
- X-axis: 0 at left edge, increases rightward
- Unit: pixels on screen
- Origin: Top-left of scrollable timeline area
- Scroll offset: Subtracted from calculated position (offsets left edge)

### Zoom Calculations

Zoom affects pixel density:
- zoom = 1.0: 100 pixels per second (default)
- zoom = 2.0: 200 pixels per second (2x magnified)
- zoom = 0.5: 50 pixels per second (2x compressed)

Formula: `pixelsPerSecond * zoom = effective pixel density`

### Marker Interval Selection

Dynamic interval selection ensures readable spacing:
- High zoom (2.0+): Small intervals (0.1-0.5s) fit in view
- Low zoom (0.5-): Large intervals (10-60s+) prevent crowding
- Algorithm prevents interval smaller than 80px apart or larger than 150px

### LayoutPosition Normalization

All coordinates in [0,1] range:
- (0, 0) = top-left of 16:9 canvas
- (1, 1) = bottom-right of 16:9 canvas
- (0.5, 0) = top-center
- Aspect ratio maintained: 16:9 regardless of actual pixel size

### Preset Design

Presets follow conventions:
- Background layer always z:0 (full-size or base)
- Overlay layers z:1+ (on top)
- PiP corner layouts use ±0.02 margin (1.6% of width/height)
- PiP size: 0.25 (25% of dimension)

## Relationships

```mermaid
---
title: Types & Utilities
---
classDiagram
    namespace Types {
        class TimelineClip {
            id, source_video_id, track_id
            timeline_start, timeline_end
            in_point, out_point
        }
        class Track {
            id, label, z_index
            muted, locked
            clips: TimelineClip[]
        }
        class TimelineResponse {
            project_id, duration, version
            tracks: Track[]
        }
        class LayoutPosition {
            x, y, width, height
            z_index
        }
        class LayoutPreset {
            name, description
            ai_hint
            min_inputs, max_inputs
        }
        class LayoutPresetListResponse {
            presets: LayoutPreset[]
            total: number
        }
    }

    namespace Utilities {
        class CoordinateMath {
            timeToPixel()
            pixelToTime()
            getMarkerInterval()
            formatRulerTime()
        }
    }

    namespace Data {
        class PresetPositions {
            "PRESET_POSITIONS: Record"
            "PipTopLeft, PipTopRight, ..."
        }
    }

    TimelineResponse --> Track
    Track --> TimelineClip
    LayoutPresetListResponse --> LayoutPreset

    CoordinateMath -.->|uses| "zoom, scrollOffset"
    PresetPositions -.->|defines| LayoutPosition
```

## Code Locations

- **types/timeline.ts**: Type definitions
- **utils/timeline.ts**: Coordinate math and formatting
- **data/presetPositions.ts**: Preset layout data

## Usage Examples

### Positioning a Clip

```typescript
const start = clip.timeline_start ?? 0
const end = clip.timeline_end ?? start + (clip.out_point - clip.in_point)
const left = timeToPixel(start, zoom, scrollOffset)
const width = timeToPixel(end, zoom, scrollOffset) - left

// Apply style: left={left}px, width={width}px
```

### Ruler Markers

```typescript
const interval = getMarkerInterval(zoom)  // e.g., 1.0 seconds
for (let t = startTime; t <= duration; t += interval) {
  const x = timeToPixel(t, zoom, scrollOffset)
  const label = formatRulerTime(t)  // e.g., "0:15"
  // Render marker at x with label
}
```

### Selecting Preset

```typescript
const selectedPreset = 'SideBySide'
const positions = PRESET_POSITIONS[selectedPreset]  // Array of LayoutPosition
// positions[0] = { x:0, y:0, width:0.5, height:1, z_index:0 }
// positions[1] = { x:0.5, y:0, width:0.5, height:1, z_index:0 }
```

