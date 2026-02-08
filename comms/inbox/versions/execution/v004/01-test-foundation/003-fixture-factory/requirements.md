# Requirements — fixture-factory

## Goal

Build builder-pattern fixture factory with `build()` and `create_via_api()` methods for test data construction.

## Background

Tests currently construct project and clip objects inline with repetitive setup code. The `07-quality-architecture.md` spec requires `with_clip()`, `with_text_overlay()`, `build()`, and `create_via_api()` methods. Without a fixture factory, tests are verbose, inconsistent, and fragile when data models change. Depends on dependency injection (BL-021) for `create_via_api()` to work with TestClient.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|--------|
| FR-1 | Builder creates test projects with configurable clips and effects via chained methods | BL-022 |
| FR-2 | `with_clip()` adds clip configuration with sensible defaults | BL-022 |
| FR-3 | `with_text_overlay()` adds text overlay to the current clip configuration | BL-022 |
| FR-4 | `build()` returns domain objects directly for unit tests without HTTP | BL-022 |
| FR-5 | `create_via_api()` exercises the full HTTP path via TestClient for black box tests | BL-022 |
| FR-6 | Pytest fixtures expose the factory for use in test modules | BL-022 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Factory produces objects satisfying all existing test assertions |
| NFR-2 | Builder methods return `self` for fluent chaining |
| NFR-3 | Sensible defaults for all builder fields — minimal setup for common cases |

## Out of Scope

- Migrating all existing tests to use the factory — migration is incremental
- Factory for Rust domain objects — Python-side only
- Randomized/property-based factory generation — that's BL-009 guidance territory

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Unit | Builder chaining: `with_clip()`, `with_text_overlay()`, `build()` returns correct domain object | 5–8 |
| Unit | `build()` returns domain objects without HTTP | 2–3 |
| Integration | `create_via_api()` exercises full HTTP path via TestClient | 2–3 |
| Regression | Existing tests migrated to factory maintain same assertions | (existing) |