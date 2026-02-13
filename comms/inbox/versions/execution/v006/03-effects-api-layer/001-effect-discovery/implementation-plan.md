# Implementation Plan: effect-discovery

## Overview

Create a GET /effects endpoint with an effect registry service, parameter JSON schemas, and AI hints. The registry follows the existing job handler dictionary pattern, injected via `create_app()` DI. Text overlay and speed control are registered as discoverable effects.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `src/stoat_ferret/api/services/effects.py` | Create | EffectRegistry service with registration and listing |
| `src/stoat_ferret/api/schemas/effect.py` | Create | Pydantic models for effect metadata and parameters |
| `src/stoat_ferret/api/routers/effects.py` | Create | GET /effects endpoint |
| `src/stoat_ferret/api/app.py` | Modify | Add effect_registry to create_app() kwargs and lifespan registration |
| `src/stoat_ferret/api/routers/__init__.py` | Modify | Include effects router |
| `tests/test_api/test_effects.py` | Create | Unit and system tests for effects endpoint |

## Implementation Stages

### Stage 1: Effect Registry Service

1. Create `src/stoat_ferret/api/services/effects.py` with:
   - `EffectRegistry` class with dictionary-based registration (following `AsyncioJobQueue.register_handler()` pattern)
   - `register(name, description, param_model, ai_hints, preview_fn)` method
   - `list_effects() -> list[EffectInfo]` method with server-side sorting
   - `get_effect(name) -> Optional[EffectInfo]` method
2. Create `src/stoat_ferret/api/schemas/effect.py` with:
   - `EffectParameter` model for individual parameter metadata
   - `EffectInfo` model with name, description, parameters (JSON schema), ai_hints, preview
   - `EffectListResponse` model for the endpoint response

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "test_registry"
```

### Stage 2: GET /effects Endpoint

1. Create `src/stoat_ferret/api/routers/effects.py` with:
   - `GET /effects` endpoint returning list of registered effects
   - Dependency function `get_effect_registry(request)` checking `request.app.state.effect_registry` (following `get_repository()` pattern in `src/stoat_ferret/api/routers/videos.py`)
   - JSON schema for each effect's parameters via Pydantic `.model_json_schema()`
   - Filter preview for default parameters via Rust builder invocation
2. Update `src/stoat_ferret/api/routers/__init__.py` to include effects router

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "test_endpoint"
```

### Stage 3: DI Integration and Effect Registration

1. Update `src/stoat_ferret/api/app.py`:
   - Add `effect_registry: Optional[EffectRegistry] = None` to `create_app()` kwargs
   - Store on `app.state.effect_registry`
   - In lifespan: create default registry, register text overlay and speed control effects
2. Register effects with parameter Pydantic models that produce JSON schemas
3. AI hints for each parameter (e.g., text: "Enter the overlay text", font_size: "Typical range 12-72")

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v
uv run pytest tests/test_api/test_di_wiring.py -v
```

## Test Infrastructure Updates

- New test file follows existing patterns in `tests/test_api/`
- Tests inject EffectRegistry via `create_app()` kwargs (LRN-005)

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Effect registry extensibility for v007 — mitigated by dictionary-based pattern following proven job handler approach. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: create effect discovery API endpoint with registry service

Add GET /effects endpoint with EffectRegistry service, parameter JSON
schemas, AI hints, and filter previews. Register text overlay and speed
control as discoverable effects. Covers BL-042.
```