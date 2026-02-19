# Handoff: 002-transition-api-endpoint

## What Was Done

- Added `POST /projects/{project_id}/effects/transition` endpoint
- Transitions are stored in `Project.transitions` (list of dicts) persisted as `transitions_json` in SQLite
- Clip adjacency is validated by checking timeline order via `clip_repo.list_by_project()`
- Registry dispatch generates FFmpeg filter strings (uses existing xfade/acrossfade definitions)

## Key Design Decisions

- **Transitions stored on Project, not Clip**: Since transitions span two clips, they're stored on the project model rather than on individual clips. This avoids duplication and makes it clear transitions are a project-level concern.
- **Adjacency = consecutive in timeline order**: Two clips are "adjacent" if the source clip is immediately followed by the target clip when clips are sorted by `timeline_position`. No gap/overlap check is enforced.
- **Reuses effect registry**: Transition types like `xfade` and `acrossfade` are already registered in the effect registry, so the endpoint dispatches through the same registry mechanism.

## For Next Implementer

- The `transitions_json` column was added to the schema definition in `schema.py`. An alembic migration may be needed for existing production databases.
- The endpoint currently allows any registered effect type as a transition type. A future feature could restrict transition types to only crossfade-related effects.
- No duplicate transition check exists for the same clip pair. Out of scope per requirements.
