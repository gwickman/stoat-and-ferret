# Theme: effect-registry-api

## Goal

Refactor the effect registry to use builder-protocol dispatch (replacing if/elif), add JSON schema validation, create the transition API endpoint, and document the architectural changes. This theme is the architectural centerpiece connecting Rust builders to the GUI.

## Design Artifacts

See `comms/outbox/versions/design/v007/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | effect-registry-refactor | BL-047 | Add build_fn to EffectDefinition, replace _build_filter_string() dispatch with registry lookup, add JSON schema validation and Prometheus metrics |
| 002 | transition-api-endpoint | BL-046 | Create POST /effects/transition endpoint with clip adjacency validation and persistent storage |
| 003 | architecture-documentation | — | Update docs/design/02-architecture.md and 05-api-specification.md to reflect registry refactoring, new endpoints, and effect type additions |

## Dependencies

- T01 complete: all Rust builders registered so registry has full effect set
- Existing EffectRegistry (registry.py) and EffectDefinition (definitions.py) as refactoring base
- Existing DI pattern via create_app() kwargs (app.py)
- Existing Prometheus metrics pattern (middleware/metrics.py, ffmpeg/metrics.py)

## Technical Approach

1. **Registry refactoring** (F001): Add `build_fn: Callable[[dict[str, Any]], str]` to EffectDefinition. Move per-effect build logic from `_build_filter_string()` into callables. Replace if/elif dispatch with `definition.build_fn(parameters)`. Add JSON schema validation per effect. Add `stoat_ferret_effect_applications_total` Prometheus counter.

2. **Transition API** (F002): Create POST /effects/transition endpoint. Validate clip adjacency in timeline. Use registry dispatch for filter string generation. Store transition in project model.

3. **Architecture docs** (F003): Update 02-architecture.md and 05-api-specification.md to reflect structural changes.

See `comms/outbox/versions/design/v007/004-research/codebase-patterns.md` for refactoring details.

## Risks

| Risk | Mitigation |
|------|------------|
| Registry refactoring scope | Resolved: Only 2 branches in _build_filter_string(). Parity tests required. See 006-critical-thinking/risk-assessment.md |
| Pre-existing mypy errors (11) | Baseline mypy at start of F001, new code must not increase count. See 006-critical-thinking/risk-assessment.md |