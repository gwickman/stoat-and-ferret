---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 002-clip-effect-api

## Summary

Implemented POST endpoint to apply text overlay effects to clips with persistent storage in the clip model. The endpoint validates effect types via the effect registry, generates FFmpeg filter strings via Rust builders (DrawtextBuilder/SpeedControl), stores effect configuration in the clip's `effects_json` column, and returns the generated filter string for transparency.

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001 | POST endpoint applies text overlay parameters to a specified clip | PASS |
| FR-002 | Effect configuration stored persistently in the clip/project model | PASS |
| FR-003 | Response includes the generated FFmpeg filter string for transparency | PASS |
| FR-004 | Validation errors from Rust surface as structured API error responses | PASS |
| FR-005 | Black box test covers the apply -> verify filter string flow | PASS |

## Changes Made

### Schema & Model
- `src/stoat_ferret/db/schema.py`: Added `effects_json TEXT` column to clips table
- `src/stoat_ferret/db/models.py`: Added `effects: list[dict[str, Any]] | None` field to Clip dataclass
- `src/stoat_ferret/db/clip_repository.py`: Added JSON serialization/deserialization for effects in add/update/read operations

### API Schemas
- `src/stoat_ferret/api/schemas/clip.py`: Added `effects` field to `ClipResponse`
- `src/stoat_ferret/api/schemas/effect.py`: Added `EffectApplyRequest` and `EffectApplyResponse` schemas

### Endpoint
- `src/stoat_ferret/api/routers/effects.py`: Added `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` endpoint with:
  - Project/clip existence validation
  - Effect type validation via registry
  - Filter string generation via Rust builders
  - Effect storage on clip model
  - Structured error responses for unknown effects and invalid parameters

### Documentation
- `docs/design/05-api-specification.md`: Reconciled "Add Effect to Clip" section with actual implementation (Impact #3)

### Tests
- `tests/test_api/test_effects.py`: 7 new tests for clip effect application (apply, persistence, error cases, transparency, clip response)
- `tests/test_blackbox/test_core_workflow.py`: 1 new black box test (apply -> read -> verify filter string)
- `tests/test_clip_model.py`: 2 new tests for effects field (defaults to None, stores list)
- `tests/test_db_schema.py`: 1 new test for effects_json column

## Quality Gates

- ruff check: pass
- ruff format: pass
- mypy: pass
- pytest: 733 passed, 20 skipped, coverage 93%
