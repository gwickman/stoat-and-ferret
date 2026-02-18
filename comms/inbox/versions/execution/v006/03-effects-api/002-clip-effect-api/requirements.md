# Requirements: clip-effect-api

## Goal

POST endpoint to apply text overlay to clips with effect storage in clip model.

## Background

Backlog Item: BL-043

No API endpoint exists to apply effects to clips. The Rust drawtext builder will generate filter strings, but there is no REST endpoint to receive effect parameters, apply them to a specific clip, and store the configuration in the project model. M2.2 requires this bridge between the Rust effects engine and the clip/project data model. The clip model currently has no field for storing applied effects.

## Functional Requirements

### FR-001: Apply Effect Endpoint

POST endpoint applies text overlay parameters to a specified clip. Accepts effect type and parameters, validates via effect registry, generates filter string via Rust builder.

**Acceptance criteria:** POST endpoint applies text overlay parameters to a specified clip.

### FR-002: Persistent Storage

Effect configuration stored persistently in the clip/project model. Add `effects_json TEXT` column to clips table in `schema.py`. Add `effects: list[dict[str, Any]] | None = None` to Python Clip dataclass. Repository handles JSON serialization following `audit.py` `json.dumps()` pattern.

**Acceptance criteria:** Effect configuration stored persistently in the clip/project model.

### FR-003: Filter String Transparency

Response includes the generated FFmpeg filter string for transparency, allowing clients to inspect what filter commands will be generated.

**Acceptance criteria:** Response includes the generated FFmpeg filter string for transparency.

### FR-004: Structured Error Responses

Validation errors from Rust surface as structured API error responses with actionable messages.

**Acceptance criteria:** Validation errors from Rust surface as structured API error responses.

### FR-005: Black Box Test

Black box test covers the apply -> verify filter string flow (end-to-end).

**Acceptance criteria:** Black box test covers the apply -> verify filter string flow.

## Non-Functional Requirements

### NFR-001: Schema Change

Clip model schema change via `CREATE TABLE IF NOT EXISTS` — dev databases are ephemeral, no migration framework needed.

### NFR-002: Rust Clip Unchanged

Rust clip struct remains unchanged — effects are Python-side business logic. Rust generates filter strings from effect parameters.

## Out of Scope

- Removing effects from clips (update/delete operations for effects)
- Multiple effect types in a single request
- Effect ordering or priority
- Real-time effect preview rendering

## Test Requirements

- Black box test: apply effect -> read clip -> verify filter string
- Integration tests for POST endpoint
- Tests for clip model with effects field (serialization/deserialization)
- Tests for validation error propagation from Rust
- Tests for API schema (ClipCreate/ClipUpdate/ClipResponse with effects)

## Sub-tasks

- Impact #3: Reconcile 05-api-specification.md with actual implementation

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.