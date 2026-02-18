# Theme: effects-api

## Goal

Create the Python-side effect registry, discovery API endpoint, clip effect application endpoint, and update architecture documentation. This bridges the Rust filter engine with the REST API and data model. Corresponds to M2.2–M2.3 API integration.

## Design Artifacts

See `comms/outbox/versions/design/v006/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | effect-discovery | BL-042 | Effect registry with parameter schemas, AI hints, and GET /effects endpoint |
| 002 | clip-effect-api | BL-043 | POST endpoint to apply text overlay to clips with effect storage in clip model |
| 003 | architecture-docs | Impact #2 | Update 02-architecture.md with new Rust modules, Effects Service, and clip model extension |

## Dependencies

- Theme 02 must be complete (both drawtext and speed builders needed for effect registration)
- Features within this theme are strictly sequential: discovery -> clip-effect-api -> architecture-docs

## Technical Approach

- **Effect discovery (BL-042):** Python-side `EffectRegistry` class following `register_handler()` pattern from job queue (LRN-009). Added as `effect_registry` kwarg to `create_app()` following existing DI pattern (LRN-005). GET `/effects` endpoint returns name, description, parameter JSON schema, AI hints, and Rust-generated filter preview. See `004-research/codebase-patterns.md` (DI/create_app Pattern, Effect Registry).
- **Clip effect API (BL-043):** Add `effects_json TEXT` column to clips table in `schema.py`. Add `effects` field to Python Clip dataclass and API schemas. POST endpoint applies text overlay parameters to a clip, stores configuration, returns generated FFmpeg filter string. Follow existing `json.dumps()` pattern from `audit.py`. See `006-critical-thinking/risk-assessment.md` (Risk #1).
- **Architecture docs (Impact #2):** Update `docs/design/02-architecture.md` with new Rust modules, Effects Service, and clip model extension. Reconcile `05-api-specification.md` with actual implementation.

## Risks

| Risk | Mitigation |
|------|------------|
| Clip effect model design | Add `effects_json TEXT` to clips table; Python-only; follow `audit.py` JSON pattern. See `006-critical-thinking/risk-assessment.md` |