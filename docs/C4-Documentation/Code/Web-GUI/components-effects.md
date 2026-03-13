# C4 Code Level: Effect Components

**Source:** `gui/src/components/Effect*.tsx`, `gui/src/components/FilterPreview.tsx`, `gui/src/components/TransitionPanel.tsx`

**Component:** Web GUI

## Purpose

Effect workshop UI: catalog browsing, parameter configuration, live preview, effect stacking, and transition application.

## Code Elements

### EffectCatalog

**Location:** `gui/src/components/EffectCatalog.tsx` (line 79)

**Props:** None (reads from stores)

- **Features:**
  - Search bar (real-time filter)
  - Category dropdown (derived from effects)
  - View toggle (grid/list mode)
- **Display:**
  - Grid (default): 1 col (mobile) → 2 (tablet) → 3 (desktop)
  - List: single column, flex-row cards with gap
- **EffectCard:** Shows effect name, category badge, description; selectable with keyboard
- **Filtering:**
  - By search query (case-insensitive name match)
  - By selected category
  - Results combined (both filters apply)

**Helper:**
- `deriveCategory(effectType)` - Via useEffects hook
- `CategoryBadge` - Color-coded badges (blue/green/purple)

**States:**
- Loading: "Loading effects..."
- Error: Message + retry button
- Empty (filtered): "No effects match your search."

### EffectParameterForm

**Location:** `gui/src/components/EffectParameterForm.tsx` (line 324)

**Props:** None (reads from store)

- **Purpose:** Schema-driven form generator for effect parameters
- **Rendering:** Only renders if schema + schema.properties exist
- **Fields:** Dynamically generated per schema property via `SchemaField` component

**Field Components:**
1. **NumberField** - Input + optional range slider
   - Renders slider if min/max defined
   - Input always shown (complementary to slider)
2. **StringField** - Text input with optional placeholder
3. **EnumField** - Dropdown with enum options
4. **BooleanField** - Checkbox
5. **ColorField** - HTML color picker

**Field Selection Logic:**
- `format: "color"` → ColorField
- `type: "string"` + `enum` → EnumField
- `type: "number"` | `"integer"` → NumberField
- `type: "string"` → StringField
- `type: "boolean"` → BooleanField
- Default: StringField

**Helper:**
- `labelFor(key, prop)` - Returns prop.description or key with underscores replaced by spaces

### EffectStack

**Location:** `gui/src/components/EffectStack.tsx` (line 13)

**Props:**
```typescript
interface EffectStackProps {
  effects: AppliedEffect[]
  isLoading: boolean
  onEdit: (index: number, effect: AppliedEffect) => void
  onRemove: (index: number) => void
}
```

- **Renders:** Ordered list of applied effects with edit/remove buttons
- **Display:** For each effect:
  - Effect type (bold)
  - Parameter summary (first 3 params)
  - Edit button
  - Remove button or confirmation prompt
  - Filter string (pre-formatted, monospace)
- **States:**
  - Loading: "Loading effects..."
  - Empty: "No effects applied to this clip."
- **Confirmation:** Two-button confirm/cancel for deletion

**Feature:** `highlightFilter()` function from FilterPreview provides syntax highlighting in pre tag

### FilterPreview

**Location:** `gui/src/components/FilterPreview.tsx` (line 75)

**Props:** None (reads from store)

- **Purpose:** Display generated FFmpeg filter string with copy button
- **Rendering:** Only shows if filterString exists OR loading OR error
- **Features:**
  - Syntax highlighting via `highlightFilter()` function
  - Copy-to-clipboard button (shows "Copied!" confirmation for 2s)
  - Error/loading states

**Syntax Highlighting:**
- Pad labels `[xxx]` → cyan-400
- Filter names (drawtext, fade, xfade, etc.) → yellow-300
- Default text → gray-200

**Helper:**
- `highlightFilter(filter)` - Regex-based tokenization returning React nodes with className styling

### TransitionPanel

**Location:** `gui/src/components/TransitionPanel.tsx` (line 16)

**Props:**
```typescript
interface TransitionPanelProps {
  projectId: string
  clips: Clip[]
}
```

- **Purpose:** Apply transitions between adjacent clips
- **Flow:**
  1. ClipSelector in pair-mode (select FROM and TO clips)
  2. Transition type catalog (buttons for each transition effect)
  3. EffectParameterForm (if transition type selected)
  4. Apply button (only enabled if both clips + type selected)
  5. Status message (success or error)

**Features:**
- Uses `useTransitionStore()` for source/target selection
- Uses `useEffectFormStore()` for parameters
- Filters effects: category === 'transition' OR effect_type === 'acrossfade'
- Reset button (clears selections and form)
- Error handling: "Clips are not adjacent" error specifically handled

**Stores:**
- `useTransitionStore()`: sourceClipId, targetClipId, selectSource, selectTarget, isReady
- `useEffectFormStore()`: parameters, schema, setSchema, resetForm

**API:**
- POST `/api/v1/projects/{id}/effects/transition`
- Payload: `{ source_clip_id, target_clip_id, transition_type, parameters }`

## Dependencies

### Internal Dependencies

- **Type imports:** Effect, AppliedEffect, ParameterSchema, LayoutPosition
- **Stores:** useEffectCatalogStore, useEffectFormStore, useEffectPreviewStore, useEffectStackStore, useTransitionStore
- **Hooks:** useEffects, useProjects, useDebounce
- **Components:** ClipSelector, EffectParameterForm (TransitionPanel)

### External Dependencies

- React: `useState`, `useEffect`, `useCallback`, `useMemo`
- Tailwind CSS for styling

## Key Implementation Details

### Schema-Driven Form Generation

EffectParameterForm walks schema.properties and renders SchemaField for each:
```typescript
const entries = Object.entries(schema.properties)
entries.map(([key, prop]) => (
  <SchemaField name={key} prop={prop} value={parameters[key]} onChange={setParameter} />
))
```

No hardcoded field mapping; purely data-driven from schema.

### Syntax Highlighting Regex

FilterPreview uses single regex with two capture groups:
```typescript
const pattern = /(\[[^\]]+\])|(\b(?:drawtext|fade|...|acrossfade)\b)/g
```
- Group 1: Pad labels `[...]`
- Group 2: Known filter names

Loops through matches, wrapping each in styled span.

### Effect Categorization (EffectCatalog)

```typescript
const categories = useMemo(() => {
  const cats = new Set(effects.map(e => deriveCategory(e.effect_type)))
  return Array.from(cats).sort()
}, [effects])
```

Dynamically derives categories from loaded effects, ensuring only used categories appear in dropdown.

### Transition Adjacency Check

API validates clips are adjacent; client catches 400 + checks error message:
```typescript
if (res.status === 400 && message.includes('adjacent')) {
  setSubmitStatus('Error: Selected clips are not adjacent on the timeline.')
}
```

### Parameter Form Pre-fill (EffectsPage)

When editing an existing effect:
```typescript
for (const [key, value] of Object.entries(effect.parameters)) {
  useEffectFormStore.getState().setParameter(key, value)
}
```

After schema is set, walks existing parameters and sets each in form.

## Relationships

```mermaid
---
title: Effect Components Interaction
---
classDiagram
    namespace EffectsPage {
        class Tab {
            activeTab: 'effects' | 'transitions'
        }
        class EffectsTab {
            ClipSelector
            EffectCatalog
            EffectParameterForm
            FilterPreview
            EffectStack
        }
        class TransitionsTab {
            TransitionPanel
        }
    }

    namespace Stores {
        class EffectCatalogStore {
            selectedEffect, searchQuery, selectedCategory
        }
        class EffectFormStore {
            parameters, schema, validationErrors
        }
        class EffectPreviewStore {
            filterString
        }
        class EffectStackStore {
            selectedClipId, effects
        }
        class TransitionStore {
            sourceClipId, targetClipId
        }
    }

    Tab --> EffectsTab
    Tab --> TransitionsTab

    EffectsTab --> EffectCatalog
    EffectCatalog --> EffectCatalogStore
    EffectCatalog --> EffectParameterForm

    EffectParameterForm --> EffectFormStore
    EffectFormStore -.->|triggers useEffectPreview| FilterPreview
    FilterPreview --> EffectPreviewStore

    EffectsTab --> EffectStack
    EffectStack --> EffectStackStore

    TransitionsTab --> TransitionPanel
    TransitionPanel --> TransitionStore
    TransitionPanel --> EffectFormStore
```

## Code Locations

- **EffectCatalog.tsx**: Browse and filter effects
- **EffectParameterForm.tsx**: Dynamic form for effect parameters
- **EffectStack.tsx**: List of applied effects with edit/remove
- **FilterPreview.tsx**: FFmpeg filter string display with syntax highlight
- **TransitionPanel.tsx**: Transition application workflow

