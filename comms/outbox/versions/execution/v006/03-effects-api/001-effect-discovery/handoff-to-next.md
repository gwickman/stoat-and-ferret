# Handoff: 001-effect-discovery -> next feature

## What Was Built

- `EffectRegistry` class in `src/stoat_ferret/effects/registry.py` with `register()`, `get()`, `list_all()` methods
- `EffectDefinition` dataclass in `src/stoat_ferret/effects/definitions.py` with name, description, parameter_schema, ai_hints, preview_fn
- `GET /api/v1/effects` endpoint returning all effects with full metadata and filter previews
- Text overlay and speed control registered as built-in effects
- DI via `create_app(effect_registry=...)` kwarg

## Key Integration Points

- **Adding new effects**: Create an `EffectDefinition` and call `registry.register("effect_type", definition)` in `create_default_registry()` in `definitions.py`
- **DI in tests**: Pass `effect_registry=` to `create_app()` for test isolation, or rely on the default registry fallback
- **Filter previews**: Each effect's `preview_fn` uses the Rust builders to generate a real FFmpeg filter string

## Dependencies for Next Features

- The `EffectRegistry` is ready to be used by v007 Effect Workshop for dynamic effect loading
- The parameter schemas follow JSON Schema format, suitable for generating frontend parameter forms
- The endpoint response structure (`EffectListResponse`) can be extended with additional metadata fields without breaking clients
