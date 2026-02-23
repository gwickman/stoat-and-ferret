# Gap Analysis: Clip Management

## Design Intent

The project roadmap (`docs/design/01-roadmap.md`) defines six phases. Clip management was split across phases:

- **Phase 1 (v001-v005):** Core infrastructure, clip validation (Rust), clip API (Python), GUI shell with read-only clip display
- **Phase 2 (v006-v007):** Effects engine — apply/edit/remove effects on existing clips via GUI
- **Phase 3 (planned, not started):** Composition Engine — Timeline Canvas with clip selection, properties panel, drag-and-drop reordering, multi-track support

The GUI architecture document (`docs/design/08-gui-architecture.md`, Phase 3 checklist at line 574) explicitly defers clip management UI to Phase 3:
- Build horizontal timeline component
- Implement track rendering (video, text, audio)
- Add clip selection and properties panel
- Create zoom and scroll controls

**Conclusion:** The absence of Add/Update/Remove clip buttons is an intentional phasing decision, not a missing implementation.

---

## Current State vs Design Specs

### What v005 Was Designed to Deliver (and Did)

Per `docs/versions/v005/VERSION_DESIGN.md`, Theme 03 (gui-components) included a project manager with:
- Project list with clip counts — **Delivered** (ProjectCard)
- Project details with clip table — **Delivered** (ProjectDetails)
- No clip CRUD UI was specified

The v005 retrospective (`03-gui-components_retrospective.md`) confirms delivery: "Project details with timeline positions | Complete | Rust-calculated clip positions"

### What v007 Delivered for Clip Interaction

v007 Theme 03 (effect-workshop-gui) added:
- ClipSelector for choosing which clip to apply effects to — **Delivered**
- Effect stack per clip with edit/remove — **Delivered**
- No clip CRUD UI was specified

### What Phase 3 Is Designed to Deliver (Not Started)

The GUI architecture (`docs/design/08-gui-architecture.md`) describes Phase 3 timeline components:
- `TimelineCanvas.tsx` — horizontal scrolling timeline
- `Track.tsx` — video, text, audio tracks
- `Clip.tsx` — clip component with selection and properties
- `Playhead.tsx` — playback position indicator

The API spec (`docs/design/05-api-specification.md`) also defines a `POST /projects/{id}/clips/reorder` endpoint that hasn't been implemented yet — this would pair with drag-and-drop reordering in the Timeline Canvas.

---

## Gap Summary

| Capability | Design Spec | Backend | Frontend | Gap Type |
|-----------|-------------|---------|----------|----------|
| View clips | Phase 1 | Done | Done | None |
| Add clip to project | Phase 1 API, Phase 3 GUI | Done | **Missing** | GUI not wired |
| Update clip timing | Phase 1 API, Phase 3 GUI | Done | **Missing** | GUI not wired |
| Delete clip | Phase 1 API, Phase 3 GUI | Done | **Missing** | GUI not wired |
| Reorder clips | Phase 3 | **Missing** | **Missing** | Not implemented |
| Timeline canvas | Phase 3 | N/A | **Missing** | Not implemented |
| Clip properties panel | Phase 3 | N/A | **Missing** | Not implemented |
| Multi-track editing | Phase 3 | N/A | **Missing** | Not implemented |

---

## Recommendations

### Option A: Minimal — Add Clip CRUD to ProjectDetails (Low Effort)

Add three controls to the existing ProjectDetails component without building the full Timeline Canvas:

1. **"Add Clip" button** above the clips table — opens a modal with:
   - Source video dropdown (fetched from `/api/v1/videos`)
   - In point, out point, timeline position fields
   - Calls `POST /api/v1/projects/{id}/clips`

2. **Per-row Edit button** in the clips table — opens a modal with:
   - Editable in_point, out_point, timeline_position fields
   - Calls `PATCH /api/v1/projects/{id}/clips/{clip_id}`

3. **Per-row Delete button** in the clips table — with confirmation dialog:
   - Calls `DELETE /api/v1/projects/{id}/clips/{clip_id}`

**Scope:** ~3 new components (AddClipModal, EditClipModal, delete confirmation), 3 new API functions in `useProjects.ts`. Estimated as a single theme with 3 features.

### Option B: Full Phase 3 — Timeline Canvas (High Effort)

Build the complete Timeline Canvas as designed in `08-gui-architecture.md`. This provides a visual timeline for clip management but is significantly more work and includes features beyond basic CRUD (drag-and-drop, multi-track, zoom, playhead).

### Recommendation

**Option A** is recommended as an interim solution. It closes the most-reported gap (no way to manage clips) with minimal effort, using backend endpoints that are already implemented and tested. The full Timeline Canvas can still be built in Phase 3, at which point Option A's modals could be superseded by inline timeline editing.

If Option A is chosen, consider adding a backlog item for `POST /projects/{id}/clips/reorder` as well, since the endpoint is designed but not implemented.
