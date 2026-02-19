# Handoff: 002-clip-effect-api

## What Was Done

- Added `effects_json TEXT` column to clips table
- Added `effects` field to Clip dataclass and ClipResponse schema
- Created `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` endpoint
- Effects are stored as a JSON list on the clip (append-only for now)
- Filter strings are generated via Rust DrawtextBuilder and SpeedControl builders
- `_build_filter_string()` in `effects.py` maps effect types to Rust builder calls

## Key Design Decisions

- Effects are stored as a list of dicts in `effects_json` (not a separate table) since the scope is simple append-only storage
- The `_build_filter_string()` function uses if/elif branching on effect_type rather than a registry-based dispatch — sufficient for 2 effect types, refactor to dispatch pattern when a third is added
- The effects router prefix was changed from `/api/v1/effects` to `/api/v1` to accommodate both `/effects` (discovery) and `/projects/.../clips/.../effects` (application) routes on the same router

## Out of Scope (Potential Future Work)

- Remove/update/delete effects from clips
- Effect ordering or priority
- Multiple effects in a single request
- Effect preview endpoint (dry-run without persisting)
