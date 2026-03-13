# C4 Code Level: Layout & Compose Components

**Source:** `gui/src/components/Layout*.tsx`, `gui/src/components/LayerStack.tsx`

**Component:** Web GUI

## Purpose

Multi-input video composition: select layout presets, preview position placement, manage layer order, and customize coordinates manually.

## Code Elements

### LayoutSelector

**Location:** `gui/src/components/LayoutSelector.tsx` (line 5)

**Props:** None (reads from store)

- **Purpose:** Display and select layout presets
- **Rendering:** Button grid of presets (only if presets exist)
- **Layout:** Grid 2 cols (mobile) → 3 (tablet) → 4 (desktop)
- **Button content:** Preset name (bold) + description (small text)
- **Styling:**
  - Selected: blue-500 border, blue-900/30 bg
  - Unselected: gray-700 border, gray-800 bg, hover border change
- **Interaction:** Click preset name → `selectPreset(name)`

**Store:** `useComposeStore()`
- `presets` - List of available presets
- `selectedPreset` - Currently selected preset name
- `selectPreset(name)` - Select preset, load positions from PRESET_POSITIONS

### LayoutPreview

**Location:** `gui/src/components/LayoutPreview.tsx` (line 12)

**Props:** None (reads from store)

- **Purpose:** Visual preview of layout positions
- **Rendering:** 16:9 aspect ratio container with position rectangles
- **Rectangle colors:** Color palette (blue, red, green, yellow) cycling through positions
- **Positioning:**
  - `left = pos.x * 100%`
  - `top = pos.y * 100%`
  - `width = pos.width * 100%`
  - `height = pos.height * 100%`
  - `z-index = pos.z_index`
- **Labels:** Each rect labeled "1", "2", etc. (index + 1)
- **Empty state:** "Select a preset to preview"

**Store:** `useComposeStore()`
- `getActivePositions()` - Returns selected preset positions or custom positions

### LayerStack

**Location:** `gui/src/components/LayerStack.tsx` (line 8)

**Props:** None (reads from store)

- **Purpose:** Display layers in z-order and allow manual position editing
- **Sections:**
  1. Layer list: Sorted by z_index descending (highest on top)
  2. Custom inputs: Edit coordinates if customPositions active
- **Layer display:**
  - Layer name (e.g., "Layer 1", "Layer 2")
  - z-index value
  - Sorted descending by z_index
- **Custom position editing:**
  - Grid of 4 inputs per position: x, y, width, height
  - Range: 0-1, step 0.01
  - Updates trigger `updateCustomPosition(index, field, value)`

**Store:** `useComposeStore()`
- `positions` - Active positions (from `getActivePositions()`)
- `customPositions` - Custom position overrides
- `updateCustomPosition(index, field, value)` - Update single field (with clamping)

**Field constants:**
```typescript
const COORD_FIELDS: (keyof LayoutPosition)[] = ['x', 'y', 'width', 'height']
```

## Dependencies

### Internal Dependencies

- **Type imports:** LayoutPreset, LayoutPosition (from types/timeline)
- **Stores:** useComposeStore
- **Data imports:** (None directly, store loads PRESET_POSITIONS)

### External Dependencies

- React: `useState` (LayerStack for editing)
- Tailwind CSS for styling

## Key Implementation Details

### Layout Preset Data (composeStore)

Presets loaded from API; positions defined in client-side `PRESET_POSITIONS`:
```typescript
export const PRESET_POSITIONS: Record<string, LayoutPosition[]> = {
  PipTopLeft: [
    { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },  // Background
    { x: 0.02, y: 0.02, width: 0.25, height: 0.25, z_index: 1 },  // PiP
  ],
  // ... other presets
}
```

When preset selected, composeStore copies positions to `customPositions` allowing manual edit.

### LayoutPosition Clamping

`updateCustomPosition()` in composeStore clamps values:
```typescript
const clamped = field === 'z_index'
  ? Math.round(value)  // z_index: round to integer
  : Math.min(1, Math.max(0, value))  // x,y,width,height: clamp [0,1]
```

Prevents invalid coordinates while allowing integer z_index.

### 16:9 Aspect Ratio Preview

LayoutPreview uses CSS aspect-ratio:
```typescript
<div className="...overflow-hidden rounded border border-gray-700 bg-gray-900"
     style={{ aspectRatio: '16 / 9' }}>
```

Maintains 16:9 regardless of container size.

### Color Cycling

LayoutPreview cycles through color palette:
```typescript
const COLORS = [
  'rgba(59, 130, 246, 0.5)',   // blue
  'rgba(239, 68, 68, 0.5)',    // red
  'rgba(34, 197, 94, 0.5)',    // green
  'rgba(234, 179, 8, 0.5)',    // yellow
]

// In map: backgroundColor: COLORS[i % COLORS.length]
```

### Z-Order Sorting

LayerStack sorts positions by z_index descending (highest on top):
```typescript
const sortedLayers = positions
  .map((pos, i) => ({ ...pos, index: i }))
  .sort((a, b) => b.z_index - a.z_index)
```

Displays highest z_index first for visual hierarchy clarity.

### Custom Position Entry Points

Users can enter custom positions in two ways:
1. **Select preset** → composeStore copies to customPositions → LayerStack shows editable inputs
2. **Direct setCustomPositions()** → Clears selectedPreset, allows full custom layout

### Selection Clearing

When custom positions set, selectedPreset cleared:
```typescript
setCustomPositions: (positions) => {
  set({ customPositions: positions, selectedPreset: null })
}
updateCustomPosition: (...) => {
  set({ customPositions: updated, selectedPreset: null })
}
```

Ensures custom edits don't accidentally revert to preset.

## Relationships

```mermaid
---
title: Layout & Compose Components
---
classDiagram
    namespace TimelinePage {
        class TimelinePage {
            useComposeStore()
            useTimelineStore()
            render Layout section if presets.length > 0
        }
    }

    namespace LayoutComponents {
        class LayoutSelector {
            presets button grid
            selectPreset()
        }
        class LayoutPreview {
            16:9 container
            position rects
        }
        class LayerStack {
            layer list (sorted z_index)
            custom coord inputs
        }
    }

    namespace Data {
        class ComposeStore {
            presets, selectedPreset
            customPositions
            selectPreset(), updateCustomPosition()
            getActivePositions()
        }
        class PresetPositions {
            "PRESET_POSITIONS: Record"
            "PipTopLeft, PipTopRight, ..."
        }
    }

    TimelinePage --> LayoutSelector
    TimelinePage --> LayoutPreview
    TimelinePage --> LayerStack

    LayoutSelector --> ComposeStore
    LayoutPreview --> ComposeStore
    LayerStack --> ComposeStore

    ComposeStore --> PresetPositions
```

## Code Locations

- **LayoutSelector.tsx**: Preset selection buttons
- **LayoutPreview.tsx**: 16:9 preview visualization
- **LayerStack.tsx**: Layer list and coordinate editor
- **data/presetPositions.ts**: Preset position definitions

## Layout Presets Available

From `presetPositions.ts`:
- **PipTopLeft**: Background (full) + PiP (top-left 25%)
- **PipTopRight**: Background (full) + PiP (top-right 25%)
- **PipBottomLeft**: Background (full) + PiP (bottom-left 25%)
- **PipBottomRight**: Background (full) + PiP (bottom-right 25%)
- **SideBySide**: Left (50%) + Right (50%)
- **TopBottom**: Top (50%) + Bottom (50%)
- **Grid2x2**: 2x2 grid (4 inputs)

