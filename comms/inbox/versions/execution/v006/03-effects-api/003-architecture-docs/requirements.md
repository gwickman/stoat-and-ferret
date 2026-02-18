# Requirements: architecture-docs

## Goal

Update 02-architecture.md with new Rust modules, Effects Service, and clip model extension.

## Background

Impact Assessment #2 (Substantial Impact — Feature Scope)

The architecture document (`docs/design/02-architecture.md`) is the authoritative system reference. v006 changes it materially: new Rust modules (expressions, graph validation, composition, drawtext, speed), Effects Service with registry/discovery/application, clip model extension with effects storage, and updated PyO3 bindings. This feature updates the documentation to reflect the actual v006 implementation.

## Functional Requirements

### FR-001: Rust Module Documentation

Update the Rust module structure in 02-architecture.md to include new v006 modules: `expression.rs`, `drawtext.rs`, `speed.rs`, and any graph validation / composition additions to `filter.rs` or new files.

**Acceptance criteria:** Architecture doc includes all new Rust modules with descriptions.

### FR-002: Effects Service Documentation

Document the Effects Service including the `EffectRegistry`, discovery endpoint, and clip effect application endpoint. Replace the placeholder Effects Service description with the actual implementation.

**Acceptance criteria:** Effects Service fully documented with registry, discovery, and application patterns.

### FR-003: Clip Model Extension

Document the clip model extension with `effects_json` field and the JSON serialization pattern.

**Acceptance criteria:** Clip model documentation reflects effects storage.

### FR-004: PyO3 Bindings Update

Update the PyO3 bindings section with new classes and functions exposed to Python.

**Acceptance criteria:** PyO3 bindings section lists all new v006 types.

### FR-005: API Specification Reconciliation

Reconcile `docs/design/05-api-specification.md` with actual implemented endpoints (GET /effects, POST clip effect apply).

**Acceptance criteria:** API specification matches actual implementation.

## Non-Functional Requirements

### NFR-001: Accuracy

Documentation reflects actual implementation, not planned design. This feature runs last in the theme to ensure all code is final.

## Out of Scope

- C4 architecture documentation update (tracked as BL-018)
- CHANGELOG updates (version-level bookkeeping)
- Roadmap checkbox updates (version close process)

## Test Requirements

- No automated tests — documentation-only feature
- Manual review: verify all new modules, endpoints, and model changes are documented

## Sub-tasks

- Impact #5: Update PLAN.md status (version-level bookkeeping)
- Impact #7: Check off M2.1-2.3 items in 01-roadmap.md

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.