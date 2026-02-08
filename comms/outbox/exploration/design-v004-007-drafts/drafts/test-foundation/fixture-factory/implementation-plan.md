# Implementation Plan — fixture-factory

## Overview

Create a builder-pattern fixture factory for test data with `build()` for domain objects and `create_via_api()` for full HTTP path testing.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `tests/factories.py` | ProjectFactory, ClipFactory builder classes |
| Create | `tests/test_factories.py` | Unit tests for factory builders |
| Modify | `tests/conftest.py` | Add factory pytest fixtures |
| Modify | `tests/test_api/conftest.py` | Expose factory with TestClient for `create_via_api()` |

## Implementation Stages

### Stage 1: Builder Classes
Create `ProjectFactory` with chained methods: `.with_name()`, `.with_clip()`, `.with_text_overlay()`, `.build()`. Sensible defaults for all fields. `build()` returns `Project` domain object directly.

### Stage 2: create_via_api()
Add `create_via_api(client: TestClient)` method that POSTs to the API and returns the created resource. Requires TestClient from DI-wired `create_app()`.

### Stage 3: Pytest Fixtures
Add `project_factory` fixture to `conftest.py`. Add `api_factory` fixture to `test_api/conftest.py` that includes TestClient.

### Stage 4: Incremental Migration
Migrate 2–3 representative test files to use the factory, demonstrating the pattern. Leave remaining migration for future features.

## Quality Gates

- Factory builder tests: 5–8 tests
- `create_via_api()` integration tests: 2–3 tests
- All existing tests pass (no regressions)
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| Factory defaults diverge from real data | Use existing test data as baseline for defaults |
| `create_via_api()` couples factory to API contract | Acceptable — factory is a test utility, not production code |

## Commit Message

```
feat: add builder-pattern fixture factory for test data
```
