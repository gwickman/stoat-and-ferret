# Evidence Trail: Clip Management GUI Omission

Chronological trace through design, backlog, version execution, and retrospective.

---

## 1. Design Phase (Pre-Implementation)

### API Specification (docs/design/05-api-specification.md)
- Lines 560-651: Full clip CRUD specified: `POST /projects/{id}/clips`, `PATCH /projects/{id}/clips/{clip_id}`, `DELETE /projects/{id}/clips/{clip_id}`, plus `POST /projects/{id}/clips/reorder`
- Lines 55-66: Endpoint group summary lists `/clips` as "Clip operations within projects"

### GUI Architecture (docs/design/08-gui-architecture.md)
- Lines 194-225: Phase 1 Project Manager mockup shows clips as a **read-only list** — no Add/Edit/Delete buttons in the wireframe
- Lines 547-551: Phase 1 Milestone 1.3 checklist: "Implement project details view" and "Add basic clip list display" — both unchecked, neither mentions CRUD controls
- Lines 574-577: Phase 3 Milestone 3.1: "Add clip selection and properties panel" — this is where clip interaction was implicitly deferred to

### Roadmap (docs/design/01-roadmap.md)
- Lines 145-149: Milestone 1.12 (GUI - Project Manager): "Implement project details view with clip list", "Display timeline positions calculated by Rust core", "Add project open/delete actions" — no clip CRUD actions specified
- Lines 315-321: Milestone 3.7 (GUI - Visual Timeline): "Add clip visualization with duration and thumbnails", "Create clip selection with properties panel"

**Key observation:** The design docs define clip CRUD at the API level but never specify clip CRUD *controls* in the GUI until Phase 3's timeline canvas. The Phase 1 wireframe shows clips read-only.

---

## 2. Backlog Creation (2026-02-08)

### BL-035: "Build project manager with list, creation, and details views"
- Added: 2026-02-08T17:58:20
- Priority: P1, Tags: v005, gui, projects
- Acceptance criteria (5 items):
  1. Project list displays name, creation date, and clip count
  2. New Project modal validates output settings
  3. **Project details view displays clip list with Rust-calculated timeline positions** (read-only)
  4. Delete action requires confirmation dialog
  5. Component unit tests pass
- **No acceptance criterion for clip Add/Edit/Delete**

**Note:** No companion backlog item existed for clip management controls until BL-075 (2026-02-23).

---

## 3. Backend Implementation (v003, 2026-02-08)

### v003 Theme 04: clip-model
- Retrospective (comms/outbox/versions/execution/v003/04-clip-model/retrospective.md):
  - 4 features: project-data-model, clip-data-model, clip-repository, clips-api
  - All 18/18 acceptance criteria passed
  - "REST API endpoints for full CRUD operations on projects and clips" — delivered
  - No mention of GUI for clip management

### v003 Clip Endpoints Delivered:
- `POST /api/v1/projects/{id}/clips` — create clip
- `GET /api/v1/projects/{id}/clips` — list clips (GET /timeline for detailed view)
- `PATCH /api/v1/projects/{id}/clips/{clip_id}` — update clip
- `DELETE /api/v1/projects/{id}/clips/{clip_id}` — delete clip

---

## 4. Testing Foundation (v004, 2026-02-09)

### BL-023: Black box test scenario catalog
- Core workflow test covers "scan -> project -> clips flow through REST API"
- Clip CRUD exercised in integration tests — backend confirmed working

---

## 5. GUI Implementation (v005, 2026-02-09)

### v005 Theme 03: gui-components, Feature 004: project-manager
- BL-035 completed: 2026-02-09T18:43:10
- Delivered: ProjectDetails.tsx (gui/src/components/ProjectDetails.tsx)
  - Lines 93-130: Read-only table with columns: #, Timeline Position, In Point, Out Point, Duration
  - **No Add/Edit/Delete buttons anywhere in the component**
  - Line 87-91: Empty state reads "No clips in this project yet." — no guidance on how to add clips
- 5/5 acceptance criteria passed (all read-only)

### v005 Theme 03 Retrospective
- Deliverables table: "Project details with timeline positions | Complete | Rust-calculated clip positions"
- Technical debt section: 5 items listed (WebSocket, sorting, polling, health, search) — **no mention of clip CRUD**
- Recommendations: 5 items — **no mention of clip CRUD**

### v005 Version Retrospective
- 11 technical debt items — **none about clip management controls**
- "All 4 themes and 11 features completed successfully with 100% acceptance criteria passing"

---

## 6. Effect Workshop (v007, 2026-02-19)

### v007 Theme 03: effect-workshop-gui
- Delivered ClipSelector.tsx — lets users select which clip to apply effects to
- ClipSelector line 14: "No clips in this project. Add clips to get started." — acknowledges clips need adding but provides no mechanism
- Effect CRUD (apply, edit, remove effects on clips) fully wired — demonstrates the GUI *can* wire CRUD to backend

---

## 7. Wiring Audits (Post-v005 and Post-v007)

### v005 Wiring Audit (comms/outbox/exploration/wiring-audit-v005/gaps-found.md)
- 3 gaps found: WebSocket broadcasts, pagination total, SPA routing
- **Clip CRUD GUI not flagged** — audit methodology focused on broken/degraded wiring, not absent wiring

### v006-v007 Wiring Audit (comms/outbox/exploration/wiring-audit-v006-v007/gaps-found.md)
- Gap 4: "Transition API has no GUI" — **same pattern** as clip CRUD
- Severity: minor (degraded). Backend endpoint works via API but has no GUI surface.

---

## 8. Gap Discovery (2026-02-23)

### clip-management-gaps exploration
- Identified the gap, created gap-analysis.md
- Characterized as "intentional phasing decision, not a missing implementation"
- Recommended Option A: minimal clip CRUD on ProjectDetails page

### BL-075 created: "Add clip management controls (Add/Edit/Delete) to project GUI"
- Added: 2026-02-23T10:21:43
- Priority: P1, Tags: gui, clips, crud, wiring-gap, user-feedback
- Description: "deferred from v005 (Phase 1 delivered read-only display)"

---

## Timeline Summary

| Date | Event | Clip CRUD Status |
|------|-------|-----------------|
| Pre-2026 | Design docs written | API specified, GUI deferred to Phase 3 implicitly |
| 2026-02-08 | BL-035 created | Read-only clip display specified; no CRUD controls |
| 2026-02-08 | v003 delivers clip API | Full CRUD backend operational |
| 2026-02-09 | v005 delivers ProjectDetails | Read-only table; no buttons |
| 2026-02-09 | v005 retrospective | Gap not mentioned |
| 2026-02-19 | v007 delivers Effect Workshop | ClipSelector references adding clips but provides no mechanism |
| 2026-02-21 | BL-066 created | Transition GUI gap tracked (same pattern) |
| 2026-02-23 | clip-management-gaps exploration | Gap formally identified |
| 2026-02-23 | BL-075 created | Clip CRUD GUI gap tracked |
