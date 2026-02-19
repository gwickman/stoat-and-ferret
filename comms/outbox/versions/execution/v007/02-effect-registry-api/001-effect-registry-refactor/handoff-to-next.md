# Handoff: 001-effect-registry-refactor -> 002-transition-api-endpoint

## What was done

- `EffectDefinition` now has a `build_fn` field that takes a parameter dict and returns an FFmpeg filter string
- The effects router uses `definition.build_fn(parameters)` instead of if/elif dispatch
- JSON schema validation is integrated into the apply-effect endpoint via `registry.validate()`
- All 9 effects are registered: text_overlay, speed_control, audio_mix, volume, audio_fade, audio_ducking, video_fade, xfade, acrossfade
- `stoat_ferret_effect_applications_total` Prometheus counter tracks effect usage by type

## Key patterns for next feature

- To add a new effect: create a `_build_<name>()` function in `definitions.py`, define the `EffectDefinition` constant, and register it in `create_default_registry()`
- JSON schema validation happens automatically via the `parameter_schema` on each definition
- Build functions should use the Rust builders (e.g., `FadeBuilder`, `XfadeBuilder`) and return `str(filter.build())`

## Dependencies added

- `jsonschema>=4.26` (runtime) for JSON schema validation
- `types-jsonschema` (dev) for mypy type stubs
