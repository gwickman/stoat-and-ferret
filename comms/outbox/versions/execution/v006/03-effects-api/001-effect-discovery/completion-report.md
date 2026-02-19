---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-effect-discovery

## Summary

Implemented the effect discovery feature: an `EffectRegistry` class with `register()`, `get()`, and `list_all()` methods, plus a `GET /api/v1/effects` endpoint that returns all registered effects with name, description, parameter JSON schema, AI hints, and Rust-generated filter previews. Text overlay and speed control are registered as built-in discoverable effects.

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001 | GET /effects returns a list of all available effects | PASS |
| FR-002 | Each effect includes name, description, and parameter JSON schema | PASS |
| FR-003 | AI hints included for each parameter to guide user input | PASS |
| FR-004 | Text overlay and speed control registered as discoverable effects | PASS |
| FR-005 | Response includes Rust-generated filter preview for default parameters | PASS |

## Files Created

| File | Purpose |
|------|---------|
| `src/stoat_ferret/effects/__init__.py` | Effects package init |
| `src/stoat_ferret/effects/registry.py` | EffectRegistry class with register/get/list_all |
| `src/stoat_ferret/effects/definitions.py` | EffectDefinition dataclass, built-in effects, default registry factory |
| `src/stoat_ferret/api/schemas/effect.py` | EffectResponse and EffectListResponse Pydantic models |
| `src/stoat_ferret/api/routers/effects.py` | GET /effects endpoint with DI dependency function |
| `tests/test_api/test_effects.py` | 14 tests covering registry, endpoint, DI, and filter previews |

## Files Modified

| File | Change |
|------|--------|
| `src/stoat_ferret/api/app.py` | Added `effect_registry` kwarg to `create_app()`, stored on `app.state`, included effects router |

## Quality Gates

- ruff check: PASS (0 errors)
- ruff format: PASS (all files formatted)
- mypy: PASS (0 issues in 49 source files)
- pytest: PASS (722 passed, 20 skipped, 93.63% coverage)

## Design Decisions

- **DI pattern**: Follows existing `create_app()` kwarg pattern. Effect registry stored on `app.state.effect_registry`. Dependency function falls back to a default registry if not injected.
- **Default registry**: Created via `create_default_registry()` factory in `definitions.py` to avoid circular imports between registry and definitions.
- **Preview functions**: Each effect definition includes a `preview_fn` callable that generates a filter string using the Rust builders (DrawtextBuilder, SpeedControl) with default parameters.
- **No speculative abstractions**: Registry is a simple dict-based class. No categories, tagging, or plugin system added — per YAGNI and out-of-scope items.
