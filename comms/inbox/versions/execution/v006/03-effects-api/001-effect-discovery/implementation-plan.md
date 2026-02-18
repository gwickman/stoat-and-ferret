# Implementation Plan: effect-discovery

## Overview

Create a Python-side effect registry and GET /effects discovery endpoint. The registry follows the existing DI pattern via `create_app()` kwargs. Text overlay and speed control effects are registered with parameter schemas, AI hints, and Rust-generated filter previews.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `src/stoat_ferret/effects/__init__.py` | Create | Effects package init |
| `src/stoat_ferret/effects/registry.py` | Create | EffectRegistry class with register/get/list_all methods |
| `src/stoat_ferret/effects/definitions.py` | Create | EffectDefinition dataclass and built-in effect registrations |
| `src/stoat_ferret/api/routers/effects.py` | Create | GET /effects endpoint |
| `src/stoat_ferret/api/schemas/effect.py` | Create | Effect API response schemas |
| `src/stoat_ferret/api/app.py` | Modify | Add effect_registry kwarg to create_app(), include effects router |
| `tests/test_api/test_effects.py` | Create | Integration tests for effect discovery |
| `tests/test_api/__init__.py` | Modify | (if needed for new test file) |

## Test Files

`tests/test_api/test_effects.py tests/test_api/test_di_wiring.py`

## Implementation Stages

### Stage 1: Effect Registry Core

1. Create `src/stoat_ferret/effects/` package
2. Define `EffectDefinition` dataclass in `definitions.py`:
   - `name: str`, `description: str`, `parameter_schema: dict`, `ai_hints: dict[str, str]`, `preview_fn: Callable`
3. Implement `EffectRegistry` in `registry.py`:
   - `register(effect_type: str, definition: EffectDefinition) -> None`
   - `get(effect_type: str) -> EffectDefinition | None`
   - `list_all() -> list[EffectDefinition]`
4. Register text overlay and speed control effects in `definitions.py`

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v
```

### Stage 2: API Endpoint

1. Create `src/stoat_ferret/api/schemas/effect.py` with `EffectResponse`, `EffectListResponse` Pydantic models
2. Create `src/stoat_ferret/api/routers/effects.py` with GET `/effects` endpoint
3. Endpoint returns list of effects with name, description, parameter JSON schema, AI hints, and filter preview
4. Add dependency function for effect registry (following existing DI pattern)

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v
```

### Stage 3: DI Integration

1. Add `effect_registry: EffectRegistry | None = None` kwarg to `create_app()` in `app.py`
2. Store on `app.state.effect_registry`
3. Add fallback in dependency function: create default registry if not injected
4. Include effects router in app

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py tests/test_api/test_di_wiring.py -v
```

### Stage 4: Filter Preview Generation

1. Connect preview functions to Rust builders (DrawtextBuilder, SpeedControl)
2. Each effect's preview_fn generates a filter string with default parameters
3. Test preview output matches expected FFmpeg filter syntax

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v
```

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Registry design extensibility — mitigate with simple dict-based pattern matching existing `register_handler()`. See `004-research/codebase-patterns.md`.

## Commit Message

```
feat(api): add effect discovery endpoint with registry

BL-042: EffectRegistry with parameter schemas, AI hints, and GET /effects
endpoint. Text overlay and speed control registered as discoverable effects.
```