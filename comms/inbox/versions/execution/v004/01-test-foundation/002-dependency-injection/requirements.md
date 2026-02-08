# Requirements — dependency-injection

## Goal

Add optional injectable parameters to `create_app()` replacing the `dependency_overrides` pattern for test wiring.

## Background

`create_app()` currently takes zero parameters (`src/stoat_ferret/api/app.py:43`). Tests use `app.dependency_overrides` to swap in test doubles (4 override points in `tests/test_api/conftest.py:129-132`). This is global state mutation that can leak between tests. See `004-research/external-research.md` §1 for the recommended pattern. Note: `get_repository` and `get_video_repository` both alias the same instance — DI migration should consolidate.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|--------|
| FR-1 | `create_app()` accepts optional `repository`, `video_repository`, `clip_repository`, `executor`, and `job_queue` parameters | BL-021 |
| FR-2 | When parameters are `None`, production implementations are used (current behavior preserved) | BL-021 |
| FR-3 | When parameters are provided, injected instances are used instead of production defaults | BL-021 |
| FR-4 | Test conftest migrated from `dependency_overrides` to `create_app()` parameters | BL-021 |
| FR-5 | At least one integration test demonstrates the test wiring end-to-end | BL-021 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Zero `dependency_overrides` remaining in test conftest after migration |
| NFR-2 | Production behavior identical — no change when all params are None |
| NFR-3 | Type-safe: all parameters typed with their respective protocol types |

## Out of Scope

- Modifying the lifespan context manager beyond conditional logic for injected vs production deps
- Adding new dependency types not currently in the override list
- Changing router dependency signatures — only the app factory changes

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Unit | `create_app()` with None params uses production defaults | 1–2 |
| Unit | `create_app()` with injected repos uses provided instances | 2–3 |
| Integration | End-to-end: `create_app(repository=InMemoryRepo())` → TestClient → API call → verify InMemory state | 2–3 |
| Regression | All existing API tests pass unchanged after conftest migration | (existing) |