# API Clip Endpoints Inventory

All clip endpoints are in `src/stoat_ferret/api/routers/projects.py` under the `/api/v1/projects` prefix.

## Core Clip CRUD

### 1. List Clips — `GET /api/v1/projects/{project_id}/clips`
- **Handler:** `list_clips()` (projects.py:212-242)
- **Response:** `ClipListResponse` — list of clips + total count
- **Status:** Fully implemented
- **GUI wired:** Yes — called by `fetchClips()` in `useProjects.ts`, used by ProjectDetails and EffectsPage

### 2. Create Clip — `POST /api/v1/projects/{project_id}/clips`
- **Handler:** `add_clip()` (projects.py:245-310)
- **Request:** `ClipCreate` — source_video_id, in_point, out_point, timeline_position
- **Response:** `ClipResponse` (201 Created)
- **Validation:** Checks project exists, video exists, then runs Rust clip validation
- **Status:** Fully implemented
- **GUI wired:** No — no frontend function or UI to call this

### 3. Update Clip — `PATCH /api/v1/projects/{project_id}/clips/{clip_id}`
- **Handler:** `update_clip()` (projects.py:313-382)
- **Request:** `ClipUpdate` — in_point, out_point, timeline_position (all optional)
- **Response:** `ClipResponse`
- **Validation:** Re-validates with Rust after applying partial updates
- **Status:** Fully implemented
- **GUI wired:** No — no frontend function or UI to call this

### 4. Delete Clip — `DELETE /api/v1/projects/{project_id}/clips/{clip_id}`
- **Handler:** `delete_clip()` (projects.py:385-412)
- **Response:** 204 No Content
- **Status:** Fully implemented
- **GUI wired:** No — no frontend function or UI to call this

---

## Clip Effect Endpoints (in `src/stoat_ferret/api/routers/effects.py`)

These operate on effects *within* a clip and are fully wired to the GUI's Effect Workshop.

| Endpoint | Method | GUI Wired |
|----------|--------|-----------|
| `/projects/{id}/clips/{id}/effects` | POST | Yes (EffectsPage) |
| `/projects/{id}/clips/{id}/effects/{index}` | PATCH | Yes (EffectsPage) |
| `/projects/{id}/clips/{id}/effects/{index}` | DELETE | Yes (EffectsPage) |
| `/projects/{id}/effects/transition` | POST | Yes (EffectsPage) |

---

## Pydantic Schemas (`src/stoat_ferret/api/schemas/clip.py`)

| Schema | Fields | Used By |
|--------|--------|---------|
| `ClipCreate` (line 11) | source_video_id, in_point (>=0), out_point (>=0), timeline_position (>=0) | POST handler |
| `ClipUpdate` (line 20) | in_point?, out_point?, timeline_position? (all optional, >=0) | PATCH handler |
| `ClipResponse` (line 28) | id, project_id, source_video_id, in_point, out_point, timeline_position, effects, created_at, updated_at | All responses |
| `ClipListResponse` (line 44) | clips[], total | GET handler |

---

## Database Layer

- **Model:** `src/stoat_ferret/db/models.py:59-107` — Clip dataclass with effects as `list[dict]`
- **Schema:** `src/stoat_ferret/db/schema.py:99-119` — `clips` table with project_id FK (CASCADE), source_video_id FK (RESTRICT), indexes on project and timeline
- **Repository:** `src/stoat_ferret/db/clip_repository.py` — `AsyncClipRepository` protocol + SQLite and in-memory implementations

---

## Designed but Not Implemented

The API specification (`docs/design/05-api-specification.md`) also describes:

- **Reorder Clips** — `POST /projects/{project_id}/clips/reorder` with an `order` array
  - Not implemented in backend or frontend
  - Would recalculate timeline positions

---

## Test Coverage

Integration tests in `tests/test_api/test_clips.py` cover all four CRUD operations including error cases (404, validation errors). The backend is production-ready for clip management.

---

## Summary

| Endpoint | Implemented | Tested | GUI Wired |
|----------|-------------|--------|-----------|
| List clips | Yes | Yes | Yes |
| Create clip | Yes | Yes | **No** |
| Update clip | Yes | Yes | **No** |
| Delete clip | Yes | Yes | **No** |
| Reorder clips | No | No | No |
