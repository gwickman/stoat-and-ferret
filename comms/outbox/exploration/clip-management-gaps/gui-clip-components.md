# GUI Clip Components Inventory

## Existing Components

### 1. ClipSelector (`gui/src/components/ClipSelector.tsx`)

**Purpose:** Renders clips as selectable buttons for the Effects workflow.

**User actions:** View clips, select a clip for effect application.

**What it shows:**
- `source_video_id` as label
- Timeline position, in/out points as secondary text
- Visual highlight (blue border) for selected clip
- Empty state: "No clips in this project. Add clips to get started."

**Missing:** No add/edit/delete controls. Selection only.

---

### 2. ProjectDetails (`gui/src/components/ProjectDetails.tsx`)

**Purpose:** Displays a project's metadata and a table of its clips.

**User actions:** View clips in a table, navigate back to project list, delete the project.

**What it shows:**
- Clip table with columns: #, Timeline Position, In Point, Out Point, Duration
- All frame values formatted as timecode using project FPS
- Loading, error, and empty states

**Missing:** No Add Clip button, no per-row Edit or Delete buttons, no clip selection for management.

---

### 3. EffectsPage (`gui/src/pages/EffectsPage.tsx`)

**Purpose:** Effect Workshop — select a project and clip, then manage effects on it.

**Clip-related actions:** Select project (dropdown), select clip (via ClipSelector), apply/edit/remove effects on the selected clip.

**Missing:** Cannot create, modify, or delete clips. Only uses clips as targets for effects.

---

### 4. ProjectCard (`gui/src/components/ProjectCard.tsx`)

**Purpose:** Summary card for a project in the projects list.

**What it shows:** Project name, creation date, clip count (e.g., "5 clips"), resolution, FPS.

**Missing:** No clip management actions from this level.

---

### 5. ProjectList (`gui/src/components/ProjectList.tsx`)

**Purpose:** Grid layout rendering multiple ProjectCard components.

**Clip-related:** Passes `clipCounts` to each card for display.

---

### 6. EffectStack (`gui/src/components/EffectStack.tsx`)

**Purpose:** Ordered list of effects applied to the currently selected clip.

**User actions:** View effects, edit effect parameters, remove effects with confirmation.

**Missing:** This manages *effects on clips*, not clips themselves.

---

## Data Layer

### Clip Type (`gui/src/hooks/useProjects.ts:18-27`)

```typescript
export interface Clip {
  id: string
  project_id: string
  source_video_id: string
  in_point: number
  out_point: number
  timeline_position: number
  created_at: string
  updated_at: string
}
```

### API Hooks (`gui/src/hooks/useProjects.ts:118-123`)

Only one clip-related API function exists:

- `fetchClips(projectId)` — `GET /api/v1/projects/{projectId}/clips`

**Missing API functions:**
- No `createClip()` — would call `POST /api/v1/projects/{projectId}/clips`
- No `updateClip()` — would call `PATCH /api/v1/projects/{projectId}/clips/{clipId}`
- No `deleteClip()` — would call `DELETE /api/v1/projects/{projectId}/clips/{clipId}`

### State Store (`gui/src/stores/effectStackStore.ts`)

Manages `selectedClipId` and effects for the Effects workflow. No clip CRUD state.

---

## Summary of What's Missing in the GUI

| Capability | Backend API | GUI Control | Status |
|-----------|-------------|-------------|--------|
| List clips | GET endpoint | ProjectDetails table, ClipSelector | Implemented |
| Add clip | POST endpoint | None | **Missing** |
| Update clip | PATCH endpoint | None | **Missing** |
| Delete clip | DELETE endpoint | None | **Missing** |
| Reorder clips | Not implemented | None | Not implemented |
