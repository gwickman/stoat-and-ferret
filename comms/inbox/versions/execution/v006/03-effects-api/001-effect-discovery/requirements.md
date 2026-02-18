# Requirements: effect-discovery

## Goal

Effect registry with parameter schemas, AI hints, and GET /effects endpoint.

## Background

Backlog Item: BL-042

M2.2 and 05-api-specification.md specify an `/effects` discovery endpoint, but no such endpoint exists. The frontend needs a way to discover available effects with their parameter schemas and AI hints. Without a discovery endpoint, the GUI must hard-code knowledge of available effects, breaking the extensibility model and preventing the v007 Effect Workshop from dynamically generating parameter forms.

## Functional Requirements

### FR-001: Effect List Endpoint

GET `/effects` returns a list of all available effects with full metadata.

**Acceptance criteria:** GET /effects returns a list of all available effects.

### FR-002: Parameter Schema

Each effect includes name, description, and parameter JSON schema defining the structure and types of effect parameters.

**Acceptance criteria:** Each effect includes name, description, and parameter JSON schema.

### FR-003: AI Hints

AI hints included for each parameter to guide user input (e.g., "Font size in pixels, typical range 12-72").

**Acceptance criteria:** AI hints included for each parameter to guide user input.

### FR-004: Effect Registration

Text overlay and speed control registered as discoverable effects. Registration follows `register_handler()` pattern from job queue (LRN-009). `EffectRegistry` class with `register()`, `get()`, `list_all()` methods.

**Acceptance criteria:** Text overlay and speed control registered as discoverable effects.

### FR-005: Filter Preview

Response includes Rust-generated filter preview for default parameters, demonstrating the generated FFmpeg filter string.

**Acceptance criteria:** Response includes Rust-generated filter preview for default parameters.

## Non-Functional Requirements

### NFR-001: DI Pattern

Effect registry added as `effect_registry` kwarg to `create_app()` following existing DI pattern (LRN-005). Dependency function with fallback for non-injected case.

### NFR-002: Extensibility

Registry design supports future effect types (v007 Effect Workshop) without API changes.

## Out of Scope

- Effect parameter validation (handled by individual builders)
- Effect preview rendering (video frame generation)
- Effect categories or tagging system
- WebSocket-based effect updates

## Test Requirements

- Integration tests for GET /effects endpoint
- Tests for effect registration and discovery
- Tests for parameter schema structure
- Tests for filter preview generation
- DI injection tests following existing pattern

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.