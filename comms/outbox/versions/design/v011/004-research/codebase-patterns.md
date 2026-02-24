# Codebase Patterns: v011 Research

## BL-075 — Clip CRUD Backend Endpoints

### Endpoint Signatures

**File:** `src/stoat_ferret/api/routers/projects.py`

| Method | Route | Function (line) | Request Model | Response | Status |
|--------|-------|-----------------|---------------|----------|--------|
| GET | `/api/v1/projects/{project_id}/clips` | `list_clips` (212) | — | `ClipListResponse` | 200 |
| POST | `/api/v1/projects/{project_id}/clips` | `add_clip` (245) | `ClipCreate` | `ClipResponse` | 201 |
| PATCH | `/api/v1/projects/{project_id}/clips/{clip_id}` | `update_clip` (313) | `ClipUpdate` | `ClipResponse` | 200 |
| DELETE | `/api/v1/projects/{project_id}/clips/{clip_id}` | `delete_clip` (385) | — | Empty | 204 |

### Pydantic Models

**File:** `src/stoat_ferret/api/schemas/clip.py`

**ClipCreate** (lines 11-17): `source_video_id: str`, `in_point: int` (ge=0), `out_point: int` (ge=0), `timeline_position: int` (ge=0)

**ClipUpdate** (lines 20-25): All optional — `in_point: int | None`, `out_point: int | None`, `timeline_position: int | None`

**ClipResponse** (lines 28-41): `id`, `project_id`, `source_video_id`, `in_point`, `out_point`, `timeline_position`, `effects`, `created_at`, `updated_at`

**Note:** No `label` field exists in any clip schema. BL-075 AC3 references "label" — this needs design clarification.

### Validation

Endpoints use Rust core validation via `clip.validate(source_path, source_duration_frames)` for bounds checking (in_point < out_point, within source video duration). Pydantic handles ge=0 constraints.

## BL-075 — Frontend Patterns

### Current Clip Display

**File:** `gui/src/components/ProjectDetails.tsx` — read-only table with columns: Index, Timeline Position, In Point, Out Point, Duration. Uses `fetchClips()` from `useProjects.ts` hook.

### Zustand Independent Store Pattern

**7 stores in `gui/src/stores/`:** projectStore, effectStackStore, effectCatalogStore, effectFormStore, effectPreviewStore, libraryStore, activityStore.

Common structure:
- Typed state interface with `isLoading: boolean`, `error: string | null`
- Synchronous actions via `set()`
- Async actions: `async (args) => { set({ isLoading: true }); try { ... set({ data, isLoading: false }) } catch { set({ error, isLoading: false }) } }`
- Single responsibility per store

### API Client Pattern

**File:** `gui/src/hooks/useProjects.ts` — native Fetch API, no centralized client. Pattern:
```typescript
const res = await fetch(url, { method, headers, body })
if (!res.ok) { const detail = await res.json().catch(() => null); throw new Error(...) }
return res.json()
```

### Form/Modal Pattern

**UI Library:** Tailwind CSS (custom components, no component library).

**Modal:** Fixed overlay `bg-black/50` with click-outside-to-close. Examples: `CreateProjectModal.tsx`, `DeleteConfirmation.tsx`, `ScanModal.tsx`.

**Form:** Local state for fields + errors + submitting. Inline validation with red error text. Disabled submit button during operation. Pattern in `CreateProjectModal.tsx`.

**Schema-driven form:** `EffectParameterForm.tsx` renders fields dynamically from JSON Schema (type → input widget mapping: number→slider, enum→dropdown, color→picker).

## BL-070 — Scan Directory UI

**File:** `gui/src/components/ScanModal.tsx` (lines 135-151) — plain `<input type="text">` with placeholder `/path/to/videos`. No browse button, no file picker API usage.

**Backend scan endpoint:** `POST /api/v1/videos/scan` in `src/stoat_ferret/api/routers/videos.py` (line 167). Accepts `{ path: str, recursive: bool }`. Validates path with `os.path.isdir()` and `allowed_scan_roots` security check.

**No directory listing endpoint exists** in the backend.

## BL-071 — Settings Class

**File:** `src/stoat_ferret/api/settings.py` (lines 13-102)

| Field | Type | Default | Env Var |
|-------|------|---------|---------|
| database_path | str | "data/stoat.db" | STOAT_DATABASE_PATH |
| api_host | str | "127.0.0.1" | STOAT_API_HOST |
| api_port | int | 8000 | STOAT_API_PORT |
| debug | bool | False | STOAT_DEBUG |
| log_level | Literal[...] | "INFO" | STOAT_LOG_LEVEL |
| thumbnail_dir | str | "data/thumbnails" | STOAT_THUMBNAIL_DIR |
| gui_static_path | str | "gui/dist" | STOAT_GUI_STATIC_PATH |
| ws_heartbeat_interval | int | 30 | STOAT_WS_HEARTBEAT_INTERVAL |
| log_backup_count | int | 5 | STOAT_LOG_BACKUP_COUNT |
| log_max_bytes | int | 10485760 | STOAT_LOG_MAX_BYTES |
| allowed_scan_roots | list[str] | [] | STOAT_ALLOWED_SCAN_ROOTS |

**Config:** `env_prefix="STOAT_"`, reads `.env` file, case insensitive. Cached via `@lru_cache`.

**Gap:** `docs/setup/04_configuration.md` documents only 9 variables (missing `log_backup_count` and `log_max_bytes`).

## BL-076 — Impact Assessment Consumption

**File:** `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/003-impact-assessment.md` — Task 003 reads `docs/auto-dev/IMPACT_ASSESSMENT.md` for project-specific checks. If file doesn't exist, it documents "No project-specific impact checks configured" and continues. The file location `docs/auto-dev/IMPACT_ASSESSMENT.md` is the expected path.

## BL-019 — AGENTS.md Structure

**Best insertion point:** After Commands section (line 46), before Type Stubs (line 48). `.gitignore` already has `nul` entry (line 219).
