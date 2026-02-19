---
status: complete
acceptance_passed: 14
acceptance_total: 14
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-effect-registry-refactor

## Summary

Refactored the effect registry to use builder-protocol dispatch. Added `build_fn` to `EffectDefinition`, replaced the if/elif dispatch in the effects router with `definition.build_fn(parameters)`, added JSON schema validation via `jsonschema`, registered all 9 built-in effects, and added a Prometheus counter for effect application tracking.

## Acceptance Criteria

### FR-001: EffectDefinition includes build_fn
- [x] `build_fn: Callable[[dict[str, Any]], str]` field added to EffectDefinition
- [x] Each registered effect provides its own build function
- [x] Build function receives parameter dict, returns FFmpeg filter string

### FR-002: Registry dispatch replaces if/elif
- [x] `_build_filter_string()` removed; endpoint uses `definition.build_fn(parameters)`
- [x] Parity tests verify text_overlay and speed_control produce identical filter strings
- [x] Unknown effect_type raises appropriate error (400 EFFECT_NOT_FOUND)

### FR-003: JSON schema validation
- [x] Each EffectDefinition includes a JSON schema for its parameters
- [x] `registry.validate(effect_type, parameters)` validates against schema
- [x] Invalid parameters return structured error messages
- [x] Missing required fields detected and reported
- [x] Type mismatches detected and reported

### FR-004: All effects registered
- [x] text_overlay, speed_control registered (existing)
- [x] audio_mix, volume, audio_fade, audio_ducking registered (from T01-F001)
- [x] video_fade, xfade, acrossfade registered (from T01-F002)
- [x] Registry completeness test verifies all 9 effect types

### FR-005: Prometheus counter
- [x] `stoat_ferret_effect_applications_total` Counter created with `effect_type` label
- [x] Counter increments on each successful effect application

## Non-Functional Requirements

- **NFR-001**: mypy baseline maintained — 0 errors before and after (49 source files)
- **NFR-002**: All existing tests pass without modification (840 passed, 20 skipped)

## Files Modified

| File | Change |
|------|--------|
| `src/stoat_ferret/effects/definitions.py` | Added `build_fn` field, 7 new build functions, 7 new effect definitions, updated `create_default_registry()` |
| `src/stoat_ferret/effects/registry.py` | Added `validate()` method with JSON schema validation, `EffectValidationError` class |
| `src/stoat_ferret/api/routers/effects.py` | Replaced `_build_filter_string()` with registry dispatch, added schema validation, added Prometheus counter |
| `tests/test_api/test_effects.py` | Added 18 new tests (parity, schema validation, dispatch, completeness, metrics) |
| `pyproject.toml` | Added `jsonschema` dependency and `types-jsonschema` dev dependency |

## Test Results

- 840 passed, 20 skipped, 0 failures
- Coverage: 92.20% (threshold: 80%)
- New tests: 18 added to `tests/test_api/test_effects.py`

## Quality Gates

- ruff check: pass
- ruff format: pass
- mypy: pass (0 errors, 49 files)
- pytest: pass (840 passed, 92.20% coverage)
