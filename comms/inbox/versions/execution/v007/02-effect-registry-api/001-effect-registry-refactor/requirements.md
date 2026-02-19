# Requirements: effect-registry-refactor

## Goal

Add build_fn to EffectDefinition, replace _build_filter_string() dispatch with registry lookup, add JSON schema validation and Prometheus metrics.

## Background

Backlog Item: BL-047

M2.6 specifies a central effect registry where each effect is registered with its JSON schema, Rust validation functions, and builder protocol. The v006 discovery endpoint provides basic listing, but the full registry pattern — schema validation, builder injection, and metrics tracking — is missing. The current `_build_filter_string()` in effects.py uses if/elif dispatch over effect_type strings with only 2 branches (text_overlay, speed_control). This was the documented refactoring trigger from v006 (LRN-029): "refactor to registry dispatch when 3rd effect type added."

## Functional Requirements

**FR-001**: EffectDefinition includes build_fn for filter string generation
- AC: `build_fn: Callable[[dict[str, Any]], str]` field added to EffectDefinition
- AC: Each registered effect provides its own build function
- AC: Build function receives parameter dict, returns FFmpeg filter string

**FR-002**: Registry dispatch replaces if/elif in _build_filter_string()
- AC: `_build_filter_string()` body replaced with `definition.build_fn(parameters)`
- AC: Existing text_overlay and speed_control effects produce identical filter strings (parity tests)
- AC: Unknown effect_type raises appropriate error

**FR-003**: JSON schema validation enforces parameter constraints
- AC: Each EffectDefinition includes a JSON schema for its parameters
- AC: `registry.validate(effect_type, parameters)` validates against schema
- AC: Invalid parameters return structured error messages
- AC: Missing required fields detected and reported
- AC: Type mismatches detected and reported

**FR-004**: All existing and new effects registered in the registry
- AC: text_overlay, speed_control registered (existing)
- AC: audio_mix, volume, audio_fade, audio_ducking registered (from T01-F001)
- AC: video_fade, xfade, acrossfade registered (from T01-F002)
- AC: Registry completeness test verifies all 9+ effect types

**FR-005**: Prometheus counter increments by effect type on application
- AC: `stoat_ferret_effect_applications_total` Counter created with `effect_type` label
- AC: Counter increments on each successful effect application
- AC: Follows existing naming convention (prefix `stoat_ferret_`)

## Non-Functional Requirements

**NFR-001**: mypy baseline maintained — new code must not increase error count
- Metric: Run mypy at start, record count. After feature, count must not increase.

**NFR-002**: No regression in effect application API behavior
- Metric: Existing tests/test_api/test_effects.py passes without modification

## Out of Scope

- Effect dependency resolution between effects
- Effect ordering/priority within a clip
- Visual schema editor

## Test Requirements

- ~3 unit tests: EffectDefinition with build_fn callable invocation
- ~5 unit tests: JSON schema validation (valid, invalid, missing fields)
- ~4 unit tests: Registry dispatch for each registered effect type
- ~1 registration completeness test: all effect types registered
- ~2 unit tests: Prometheus counter increments
- ~2 parity tests: text_overlay and speed_control filter string output before/after
- ~1 contract test: EffectDefinition schema round-trip

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `codebase-patterns.md`: Registry refactoring approach, DI pattern, Prometheus metrics
- `evidence-log.md`: Prometheus counter naming convention