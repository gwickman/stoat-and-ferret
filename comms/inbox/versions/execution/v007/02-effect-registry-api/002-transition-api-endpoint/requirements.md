# Requirements: transition-api-endpoint

## Goal

Create POST /effects/transition endpoint with clip adjacency validation and persistent storage.

## Background

Backlog Item: BL-046

M2.5 specifies an `/effects/transition` endpoint for applying transitions between adjacent clips, but no such endpoint exists. The Rust transition builders (T01) generate filter strings, and the registry (T02-F001) provides dispatch. This feature wires them into a REST endpoint that validates clip adjacency, generates the filter string, and stores the transition in the project model.

## Functional Requirements

**FR-001**: POST /effects/transition applies a transition between two specified clips
- AC: Request body includes source_clip_id, target_clip_id, transition_type, and parameters
- AC: Registry dispatch generates the FFmpeg filter string
- AC: Response includes the generated filter string (transparency requirement)
- AC: Returns 201 Created on success

**FR-002**: Validates that the two clips are adjacent in the project timeline
- AC: Non-adjacent clips return 400 with descriptive error
- AC: Same clip for source and target returns 400
- AC: Non-existent clip IDs return 404
- AC: Empty timeline returns 400

**FR-003**: Response includes the generated FFmpeg filter string
- AC: Response body contains `filter_string` field showing exact FFmpeg command
- AC: Response body contains `transition_type` and `parameters` echo-back

**FR-004**: Transition configuration stored persistently in the project model
- AC: Transition stored in project data (alongside clip effects)
- AC: Transition retrievable after server restart
- AC: Stored data includes source/target clip IDs, transition type, parameters, and filter string

**FR-005**: Black box test covers apply transition and verify filter output flow
- AC: Full flow test: create project, add clips, apply transition, verify response

## Non-Functional Requirements

**NFR-001**: Response schema matches OpenAPI specification
- Metric: Contract test validates response against schema

**NFR-002**: Endpoint follows existing router patterns
- Metric: Consistent with effects.py router structure

## Out of Scope

- Multiple simultaneous transitions between the same clip pair
- Transition preview rendering
- Undo/redo for transitions

## Test Requirements

- ~4 unit tests: Clip adjacency validation (adjacent pass, non-adjacent fail, empty timeline, same clip)
- ~2 unit tests: Transition parameter validation via registry schema
- ~2 unit tests: Transition storage in project model
- ~1 system test: POST /effects/transition black-box test
- ~1 parity test: Response schema matches OpenAPI spec
- ~2 contract tests: TransitionRequest/TransitionResponse schema round-trip

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `codebase-patterns.md`: Effect registry pattern, DI pattern
- `impact-analysis.md`: API endpoint additions