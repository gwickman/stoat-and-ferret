# Implementation Plan: effect-registry-refactor

## Overview

Refactor the effect registry to use builder-protocol dispatch. Add `build_fn` to EffectDefinition, replace the if/elif dispatch in `_build_filter_string()` with `definition.build_fn(parameters)`, add JSON schema validation per effect, register all existing and new effects, and add Prometheus metrics. Run mypy baseline at start to track error count.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret/effects/definitions.py` | Add `build_fn` field to EffectDefinition; add build functions and schemas for all effects |
| Modify | `src/stoat_ferret/effects/registry.py` | Add `validate()` method for JSON schema validation; update `create_default_registry()` |
| Modify | `src/stoat_ferret/api/routers/effects.py` | Replace `_build_filter_string()` with registry dispatch; add metrics |
| Modify | `src/stoat_ferret/api/schemas/effect.py` | Add schema validation error response models if needed |
| Modify | `src/stoat_ferret/ffmpeg/metrics.py` | Add `stoat_ferret_effect_applications_total` Counter (or create new metrics location) |
| Modify | `tests/test_api/test_effects.py` | Add parity tests, registry dispatch tests, metrics tests |

## Test Files

`tests/test_api/test_effects.py`

## Implementation Stages

### Stage 0: mypy baseline

1. Run `uv run mypy src/` and record current error count
2. Document baseline count in commit message

**Verification:**
```bash
uv run mypy src/ 2>&1 | tail -1
```

### Stage 1: Add build_fn to EffectDefinition

1. Add `build_fn: Callable[[dict[str, Any]], str] | None = None` field to EffectDefinition in `definitions.py`
2. Create build functions for text_overlay and speed_control (extract logic from `_build_filter_string()`)
3. Add JSON parameter schemas for text_overlay and speed_control
4. Update `create_default_registry()` to pass build_fn and schemas
5. Add parity tests: verify text_overlay and speed_control produce identical filter strings before/after

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "parity or text_overlay or speed_control"
```

### Stage 2: Replace dispatch with registry lookup

1. Replace `_build_filter_string()` body with `definition.build_fn(parameters)`
2. Add error handling for unknown effect types and missing build_fn
3. Verify all existing tests pass without modification

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v
```

### Stage 3: Register all new effects and add JSON schema validation

1. Create build functions for audio effects (audio_mix, volume, audio_fade, audio_ducking)
2. Create build functions for transition effects (video_fade, xfade, acrossfade)
3. Add JSON parameter schemas for all new effects
4. Add `validate()` method to registry.py that validates parameters against schema
5. Integrate validation into the effect application flow
6. Add registration completeness test

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "schema or registry or register"
```

### Stage 4: Add Prometheus metrics

1. Create `stoat_ferret_effect_applications_total` Counter with `effect_type` label
2. Increment counter in the effect application path (after successful apply)
3. Follow naming convention from existing `stoat_ferret_ffmpeg_executions_total`
4. Add test verifying counter increments

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "metric or prometheus"
```

### Stage 5: Final verification

1. Run full test suite
2. Run mypy and verify error count has not increased from baseline

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Test Infrastructure Updates

- Extend `tests/test_api/test_effects.py` with parity, schema, dispatch, and metrics tests
- No new test infrastructure files needed

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Refactoring changes critical effect application path — parity tests are essential. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`
- JSON schema validation library choice — use `jsonschema` (already a common Python library) or minimal custom validation

## Commit Message

```
feat: refactor effect registry with builder dispatch, JSON schema validation, and metrics
```