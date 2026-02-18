# Implementation Plan: clip-effect-api

## Overview

Add a POST endpoint to apply text overlay effects to clips. Extend the clip model with an `effects_json TEXT` column, add effects field to Python dataclass and API schemas, and create the endpoint that validates parameters, generates filter strings via Rust, and stores effect configuration.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `src/stoat_ferret/db/schema.py` | Modify | Add effects_json TEXT column to clips table |
| `src/stoat_ferret/db/models.py` | Modify | Add effects field to Clip dataclass |
| `src/stoat_ferret/db/clip_repository.py` | Modify | Handle effects JSON serialization/deserialization |
| `src/stoat_ferret/api/schemas/clip.py` | Modify | Add effects field to ClipCreate/ClipUpdate/ClipResponse |
| `src/stoat_ferret/api/routers/effects.py` | Modify | Add POST clip effect apply endpoint |
| `src/stoat_ferret/api/schemas/effect.py` | Modify | Add effect apply request/response schemas |
| `tests/test_api/test_effects.py` | Modify | Add clip effect application tests |
| `tests/test_api/test_clips.py` | Modify | Update clip tests for effects field |
| `tests/test_blackbox/test_core_workflow.py` | Modify | Add black box test for apply -> verify flow |
| `tests/test_clip_model.py` | Modify | Add effects field tests |
| `tests/test_db_schema.py` | Modify | Verify effects_json column |
| `docs/design/05-api-specification.md` | Modify | Reconcile with actual endpoints (Impact #3) |

## Test Files

`tests/test_api/test_effects.py tests/test_api/test_clips.py tests/test_blackbox/test_core_workflow.py tests/test_clip_model.py tests/test_db_schema.py`

## Implementation Stages

### Stage 1: Clip Model Extension

1. Add `effects_json TEXT` column to clips table in `src/stoat_ferret/db/schema.py`
2. Add `effects: list[dict[str, Any]] | None = None` to Clip dataclass in `src/stoat_ferret/db/models.py`
3. Update `src/stoat_ferret/db/clip_repository.py` to handle JSON serialization:
   - On write: `json.dumps(effects)` (following `audit.py` pattern)
   - On read: `json.loads(effects_json)` if not None
4. Update tests for clip model and schema

**Verification:**
```bash
uv run pytest tests/test_clip_model.py tests/test_db_schema.py -v
```

### Stage 2: API Schema Updates

1. Add `effects` field to `ClipCreate`, `ClipUpdate`, `ClipResponse` in `src/stoat_ferret/api/schemas/clip.py`
2. Add `EffectApplyRequest` and `EffectApplyResponse` schemas in `src/stoat_ferret/api/schemas/effect.py`
3. Update existing clip API tests to handle effects field

**Verification:**
```bash
uv run pytest tests/test_api/test_clips.py -v
```

### Stage 3: Effect Application Endpoint

1. Add POST endpoint in `src/stoat_ferret/api/routers/effects.py` to apply effect to clip
2. Endpoint: receives clip_id, effect_type, effect_parameters
3. Validates effect type via EffectRegistry
4. Generates filter string via Rust builder (DrawtextBuilder)
5. Stores effect configuration in clip's effects_json
6. Returns generated filter string in response
7. Surface Rust validation errors as structured API error responses

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v
```

### Stage 4: Black Box Test and API Spec Reconciliation

1. Add black box test: apply text overlay -> read clip -> verify filter string in response
2. Reconcile `docs/design/05-api-specification.md` with actual implemented endpoints (Impact #3)

**Verification:**
```bash
uv run pytest tests/test_blackbox/test_core_workflow.py -v
```

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Clip model schema change — mitigated by ephemeral dev databases and `CREATE TABLE IF NOT EXISTS`. See `006-critical-thinking/risk-assessment.md` (Risk #1).

## Commit Message

```
feat(api): add clip effect application endpoint

BL-043: POST endpoint to apply text overlay to clips with effects stored
in clip model. Includes schema change, JSON serialization, and filter
string transparency.
```