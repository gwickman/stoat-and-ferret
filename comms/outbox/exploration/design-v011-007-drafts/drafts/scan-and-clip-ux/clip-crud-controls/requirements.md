# Requirements: clip-crud-controls

## Goal

Wire frontend clip management to existing backend CRUD endpoints so users can add, edit, and delete clips from the ProjectDetails GUI.

## Background

Backlog Item: BL-075 — Add clip management controls (Add/Edit/Delete) to project GUI.

The GUI currently displays clips in a read-only table on the ProjectDetails page but provides no controls to add, edit, or remove clips. The backend API has full CRUD support (POST, PATCH, DELETE on `/api/v1/projects/{id}/clips`) — all implemented and integration-tested — but the frontend never calls the write endpoints. This gap was deferred from v005.

**Note on `label` field:** BL-075 AC3 references "label" but no `label` field exists in any clip schema or data model (confirmed by investigation — see `006-critical-thinking/investigation-log.md`). The form uses `timeline_position` instead. If label support is desired, it requires a backend schema change first.

## Functional Requirements

**FR-001: Clip store**
- New `clipStore.ts` Zustand store following the independent-store pattern (per LRN-037)
- Store manages clip CRUD operations with `isLoading` and `error` state
- Acceptance: Store provides `createClip`, `updateClip`, `deleteClip`, and `fetchClips` actions

**FR-002: Add Clip button**
- ProjectDetails page includes an Add Clip button that opens a ClipFormModal
- Acceptance: Add Clip button renders and opens the form modal on click

**FR-003: Clip form modal**
- `ClipFormModal.tsx` with fields: `source_video_id` (dropdown from `useVideos` hook), `in_point`, `out_point`, `timeline_position`
- Form renders empty for Add mode and pre-populated for Edit mode
- Acceptance: Form renders correct fields with appropriate initial values per mode

**FR-004: Source video selection**
- Simple `<select>` dropdown populated from `useVideos` hook (`GET /api/v1/videos`)
- Styled with existing Tailwind pattern (`rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white`)
- Acceptance: Dropdown lists available library videos by title

**FR-005: Edit controls**
- Each clip row in the clips table has Edit and Delete action buttons
- Edit button opens ClipFormModal pre-populated with current clip properties (in/out points, timeline_position)
- Acceptance: Edit button opens modal with correct pre-filled values

**FR-006: Delete with confirmation**
- Delete button prompts for confirmation using the existing `DeleteConfirmation.tsx` pattern
- Confirmed deletion removes the clip via DELETE endpoint
- Acceptance: Delete prompts for confirmation, then removes the clip on confirm

**FR-007: Error display**
- Add/Edit forms validate input and display errors from the backend (e.g., invalid time ranges from Rust core validation)
- Acceptance: Backend validation errors appear in the form UI

**FR-008: List refresh**
- Clip list refreshes after any add/update/delete operation
- Acceptance: Table reflects changes immediately after mutation

**FR-009: Race condition mitigation**
- Sequential await pattern with `isLoading` guard disabling buttons during operations
- Matches `effectStackStore` convention
- Acceptance: Action buttons are disabled during pending operations

## Non-Functional Requirements

**NFR-001: Consistency**
- UI patterns (modals, forms, error display, button styling) match existing components
- Metric: Visual inspection confirms consistent Tailwind styling

**NFR-002: Responsiveness**
- CRUD operations complete and reflect in UI within 1 second under normal conditions
- Metric: p95 operation time < 1s

## Out of Scope

- `label` field (not in backend schema — requires schema migration first)
- Drag-and-drop clip reordering
- Bulk clip operations (multi-select, batch delete)
- Optimistic updates or AbortController (defer to future if needed)
- Backend API changes (all endpoints exist and are tested)

## Test Requirements

**Frontend (Vitest):**
- `clipStore.ts`: createClip action calls POST endpoint and updates store state
- `clipStore.ts`: updateClip action calls PATCH endpoint and updates store state
- `clipStore.ts`: deleteClip action calls DELETE endpoint and removes clip from state
- `clipStore.ts`: error handling sets error state on API failure
- `ClipFormModal.tsx`: renders empty form for Add mode
- `ClipFormModal.tsx`: renders pre-populated form for Edit mode
- `ClipFormModal.tsx`: validates required fields before submission
- `ClipFormModal.tsx`: displays backend validation errors
- `ClipFormModal.tsx`: disabled submit button during submission
- `ProjectDetails.tsx`: renders Add Clip button
- `ProjectDetails.tsx`: renders Edit/Delete buttons per clip row
- `ProjectDetails.tsx`: delete triggers confirmation dialog
- API client: `createClip()`, `updateClip()`, `deleteClip()` functions with mock fetch

**Existing tests affected:**
- `gui/src/components/__tests__/ProjectDetails.test.tsx` — update for new Add/Edit/Delete buttons

## Reference

See `comms/outbox/versions/design/v011/004-research/` for supporting evidence:
- `codebase-patterns.md` — clip endpoint signatures, Pydantic models, Zustand patterns, form/modal patterns
- `evidence-log.md` — clip schema fields, Zustand store count
