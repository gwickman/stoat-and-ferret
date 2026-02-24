# Implementation Plan: clip-crud-controls

## Overview

Add clip CRUD controls to the ProjectDetails page by creating a `clipStore.ts` Zustand store, a `ClipFormModal.tsx` form component, and wiring Add/Edit/Delete buttons to existing backend endpoints. Follows existing frontend patterns for stores, modals, and API client calls.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `gui/src/stores/clipStore.ts` | Create | Zustand store for clip CRUD operations |
| `gui/src/components/ClipFormModal.tsx` | Create | Add/Edit clip form modal |
| `gui/src/components/ProjectDetails.tsx` | Modify | Add CRUD buttons to clip table, wire to clipStore |
| `gui/src/hooks/useProjects.ts` | Modify | Add createClip, updateClip, deleteClip API client functions |
| `gui/src/stores/__tests__/clipStore.test.ts` | Create | Store unit tests |
| `gui/src/components/__tests__/ClipFormModal.test.tsx` | Create | Form component tests |
| `gui/src/components/__tests__/ProjectDetails.test.tsx` | Modify | Update for new CRUD buttons |

## Test Files

`gui/src/stores/__tests__/clipStore.test.ts gui/src/components/__tests__/ClipFormModal.test.tsx gui/src/components/__tests__/ProjectDetails.test.tsx`

## Implementation Stages

### Stage 1: API client functions and store

1. Add API client functions to `gui/src/hooks/useProjects.ts`:
   - `createClip(projectId, data)` — POST `/api/v1/projects/{id}/clips`
   - `updateClip(projectId, clipId, data)` — PATCH `/api/v1/projects/{id}/clips/{clipId}`
   - `deleteClip(projectId, clipId)` — DELETE `/api/v1/projects/{id}/clips/{clipId}`
   - Follow existing fetch pattern with error handling
2. Create `gui/src/stores/clipStore.ts`:
   - State interface: `clips: ClipResponse[]`, `isLoading: boolean`, `error: string | null`
   - Actions: `fetchClips(projectId)`, `createClip(projectId, data)`, `updateClip(projectId, clipId, data)`, `deleteClip(projectId, clipId)`
   - Each mutation action: set `isLoading: true`, await API call, await `fetchClips` to refresh, set `isLoading: false`
   - Error handling: catch → set `error` message, set `isLoading: false`
   - Follow `effectStackStore.ts` pattern (sequential await, isLoading guard)
3. Write `gui/src/stores/__tests__/clipStore.test.ts`:
   - createClip calls POST and updates state
   - updateClip calls PATCH and updates state
   - deleteClip calls DELETE and removes clip
   - Error handling sets error state

**Verification:**
```bash
cd gui && npx vitest run src/stores/__tests__/clipStore.test.ts
```

### Stage 2: ClipFormModal component

1. Create `gui/src/components/ClipFormModal.tsx`:
   - Props: `mode: 'add' | 'edit'`, `clip?: ClipResponse` (for edit), `projectId: string`, `onClose()`, `onSave()`
   - Local state: `sourceVideoId`, `inPoint`, `outPoint`, `timelinePosition`, `error`, `isSubmitting`
   - Source video `<select>` dropdown populated from `useVideos` hook
   - Tailwind styling matching existing modals (`CreateProjectModal.tsx` pattern)
   - Submit: call `clipStore.createClip` or `clipStore.updateClip` based on mode
   - Display backend validation errors (e.g., invalid time ranges) in form
   - Disable submit button during submission
2. Write `gui/src/components/__tests__/ClipFormModal.test.tsx`:
   - Renders empty form for Add mode
   - Renders pre-populated form for Edit mode
   - Validates required fields
   - Displays backend errors
   - Disables submit during submission

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/ClipFormModal.test.tsx
```

### Stage 3: Wire into ProjectDetails

1. Modify `gui/src/components/ProjectDetails.tsx`:
   - Import `clipStore` and `ClipFormModal`
   - Add "Add Clip" button above the clip table
   - Add Edit and Delete buttons to each clip row
   - Add state for `showClipForm`, `editingClip`, `showDeleteConfirm`, `deletingClip`
   - Add Clip → opens ClipFormModal in add mode
   - Edit → opens ClipFormModal in edit mode with clip data
   - Delete → shows DeleteConfirmation dialog, on confirm calls `clipStore.deleteClip`
   - After any mutation, refresh clips via `clipStore.fetchClips`
   - Disable action buttons when `clipStore.isLoading` is true
2. Update `gui/src/components/__tests__/ProjectDetails.test.tsx`:
   - Add Clip button renders
   - Edit/Delete buttons render per clip row
   - Delete triggers confirmation dialog

**Verification:**
```bash
cd gui && npx vitest run src/components/__tests__/ProjectDetails.test.tsx src/components/__tests__/ClipFormModal.test.tsx src/stores/__tests__/clipStore.test.ts
```

## Test Infrastructure Updates

New test files:
- `gui/src/stores/__tests__/clipStore.test.ts` — store tests (4 cases)
- `gui/src/components/__tests__/ClipFormModal.test.tsx` — form tests (5 cases)

Existing test updates:
- `gui/src/components/__tests__/ProjectDetails.test.tsx` — add CRUD button tests (3+ cases)

## Quality Gates

```bash
cd gui
npx tsc -b
npx vitest run
```

## Risks

- Race condition on rapid mutations — mitigated by `isLoading` guard disabling buttons
- Source video dropdown may not scale for very large libraries — acceptable for v011, add search in future if needed
- See `comms/outbox/versions/design/v011/006-critical-thinking/risk-assessment.md` for full risk analysis

## Commit Message

```
feat(gui): add clip CRUD controls to ProjectDetails (BL-075)
```
