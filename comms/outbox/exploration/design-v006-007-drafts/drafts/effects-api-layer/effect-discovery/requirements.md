# Requirements: effect-discovery

## Goal

Create GET /effects endpoint with registry service, parameter JSON schemas, and AI hints.

## Background

Backlog Item: BL-042

M2.2 and 05-api-specification.md specify an `/effects` discovery endpoint, but no such endpoint exists. The frontend needs a way to discover available effects with their parameter schemas and AI hints. Without a discovery endpoint, the GUI must hard-code knowledge of available effects, breaking the extensibility model and preventing the v007 Effect Workshop from dynamically generating parameter forms.

## Functional Requirements

**FR-001: GET /effects endpoint**
- Returns a list of all available effects
- AC: Endpoint returns JSON array of effect objects with 200 status

**FR-002: Effect metadata**
- Each effect includes name, description, and parameter JSON schema
- Parameter schemas generated via Pydantic `.model_json_schema()`
- AC: Each effect in the response has name, description, and valid JSON Schema for parameters

**FR-003: AI hints**
- AI hints included for each parameter to guide user input
- AC: Each parameter in the schema has associated AI hint text

**FR-004: Effect registration**
- Text overlay (from BL-040) and speed control (from BL-041) registered as discoverable effects
- AC: GET /effects returns both text_overlay and speed_control effects

**FR-005: Filter preview**
- Response includes Rust-generated filter preview for default parameters
- AC: Each effect includes a preview string showing the FFmpeg filter with default values

**FR-006: Effect registry service**
- Dictionary-based registry following `AsyncioJobQueue.register_handler()` pattern
- DI via `create_app()` kwargs, stored on `app.state.effect_registry`
- Route handler access via `Depends()` function (same as `get_repository()` pattern)
- Effects registered during app lifespan (like job handlers)
- AC: Registry injectable in tests via `create_app()` kwargs; production uses lifespan registration

**FR-007: Server-side sorting**
- Effect listing sorted server-side (per retrospective insight)
- AC: Effects returned in consistent, sorted order

## Non-Functional Requirements

**NFR-001: Extensibility**
- v007 effects can register via `registry.register()` without changes to registry infrastructure
- AC: Adding a new effect type requires only calling `register()` with the effect definition

**NFR-002: Test coverage**
- Python coverage maintained above 80% threshold
- AC: New code has comprehensive unit and system tests

## Out of Scope

- Effect category/grouping (v007 concern)
- Effect search or filtering (v007 concern)
- Effect versioning or deprecation

## Test Requirements

- **Unit tests:** Effect registry service (registration, retrieval, listing, DI integration), parameter JSON schema generation, AI hints, filter preview generation
- **System/Golden tests:** GET /effects endpoint returns complete effect list with expected structure; text overlay and speed control registered

Reference: `See comms/outbox/versions/design/v006/004-research/ for supporting evidence`
