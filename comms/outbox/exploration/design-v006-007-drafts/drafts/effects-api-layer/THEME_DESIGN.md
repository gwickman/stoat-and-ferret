# Theme: effects-api-layer

## Goal

Bridge the Rust effects engine to the Python API layer. Create the effect discovery endpoint with a registry pattern and parameter schemas, extend the clip data model for effect storage, and implement the text overlay application endpoint. This theme transitions from Rust-side construction to Python-side orchestration.

## Design Artifacts

See `comms/outbox/versions/design/v006/006-critical-thinking/` for full risk analysis.
See `comms/outbox/versions/design/v006/005-logical-design/test-strategy.md` for test requirements.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | effect-discovery | BL-042 | Create GET /effects endpoint with registry service, parameter JSON schemas, and AI hints |
| 002 | clip-effect-model | BL-043 (partial) | Extend clip data model with effects storage across Python schema, DB repository, and Alembic migration |
| 003 | text-overlay-apply | BL-043 (partial) | Create POST endpoint to apply text overlay to clips with validation, persistence, and filter preview |

## Dependencies

- Theme 02, Features 002 and 003 (drawtext-builder + speed-control) must be complete before Feature 001 — effects must exist to be registered in the discovery endpoint
- Feature 002 (clip-effect-model) depends on Feature 001 (effect-discovery) — effect configuration format aligns with registry schema
- Feature 003 (text-overlay-apply) depends on Feature 002 (clip-effect-model) — endpoint stores effects on the clip model

## Technical Approach

**Effect discovery (BL-042):**
- `EffectRegistry` service: dictionary-based, following `AsyncioJobQueue.register_handler()` pattern
- DI via `create_app()` kwargs, stored on `app.state.effect_registry`
- Route handler access via `Depends()` function (same pattern as `get_repository()`)
- Each effect provides: name, description, parameter Pydantic model (auto JSON Schema via `.model_json_schema()`), AI hints dict
- Text overlay and speed control registered during app lifespan
- Server-side sorting for effect listing (per retrospective insight)

**Clip effect model (BL-043 partial):**
- Add `effects_json TEXT` column to clips table via Alembic migration (follows audit log `changes_json TEXT` pattern)
- Add `effects` field to `Clip` dataclass in Python (JSON string, parsed via helper)
- Add typed `effects` list to `ClipResponse` Pydantic schema
- Update `_row_to_clip()` in both `AsyncSQLiteClipRepository` and `AsyncInMemoryClipRepository`
- Rust `Clip` type unchanged — Python owns effect storage, Rust owns filter generation (LRN-011)

**Text overlay apply (BL-043 partial):**
- POST endpoint receives text overlay parameters, validates via Rust drawtext builder
- Stores effect configuration in clip model
- Response includes generated FFmpeg filter string for transparency
- WebSocket events: `effect.applied`, `effect.removed` extending existing `EventType` enum
- Validation errors from Rust surface as structured API error responses

See `comms/outbox/versions/design/v006/004-research/` for evidence.

## Risks

| Risk | Mitigation |
|------|------------|
| Clip effects storage model design | Resolved: `effects_json TEXT` via audit log pattern — see `006-critical-thinking/risk-assessment.md` |
| Effect registry extensibility | Dictionary-based pattern following job handler registry; designed for v007 extension — see `006-critical-thinking/risk-assessment.md` |
| BL-043 depends on two substantial impacts | Split into 3 features (discovery → model → endpoint) using proven codebase patterns — see `006-critical-thinking/risk-assessment.md` |
