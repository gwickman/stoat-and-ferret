# Requirements: architecture-documentation

## Goal

Update docs/design/02-architecture.md and 05-api-specification.md to reflect registry refactoring, new endpoints, and effect type additions.

## Background

This is a documentation feature driven by LRN-030 (architecture docs as explicit feature) and the impact analysis from Task 003. The registry refactoring (T02-F001) and transition endpoint (T02-F002) introduce structural changes that must be reflected in the authoritative design documents.

## Functional Requirements

**FR-001**: Update docs/design/02-architecture.md
- AC: Rust module additions documented (audio.rs, transitions.rs submodules)
- AC: Effects Service section rewritten to reflect registry-based dispatch
- AC: PyO3 bindings section updated with new audio/transition builder classes
- AC: Registered effects list updated (all 9+ effect types)
- AC: Prometheus metrics section updated with effect_applications_total counter

**FR-002**: Update docs/design/05-api-specification.md
- AC: POST /effects/transition endpoint documented with request/response schemas
- AC: Effect discovery response updated to include new effect types
- AC: Registry dispatch pattern documented

## Non-Functional Requirements

**NFR-001**: Documentation matches actual implementation
- Metric: All documented endpoints and types correspond to implemented code

## Out of Scope

- GUI architecture documentation (handled in T04-F002)
- API specification for CRUD endpoints (handled in T04-F002)
- Roadmap milestone updates (handled in T04-F002)

## Test Requirements

No tests — documentation feature.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `impact-analysis.md`: 13 documentation impacts consolidated into features