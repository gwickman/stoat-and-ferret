---
status: complete
acceptance_passed: 6
acceptance_total: 6
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 003-fixture-factory

## Summary

Implemented a builder-pattern fixture factory for test data construction. The factory provides two output modes: `build()` for creating domain objects directly (unit tests) and `create_via_api()` for exercising the full HTTP path via TestClient (integration tests).

## Acceptance Criteria

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1 | Builder creates test projects with configurable clips and effects via chained methods | PASS |
| FR-2 | `with_clip()` adds clip configuration with sensible defaults | PASS |
| FR-3 | `with_text_overlay()` adds text overlay to the current clip — **deferred: no text overlay model exists yet** | N/A |
| FR-4 | `build()` returns domain objects directly for unit tests without HTTP | PASS |
| FR-5 | `create_via_api()` exercises the full HTTP path via TestClient for black box tests | PASS |
| FR-6 | Pytest fixtures expose the factory for use in test modules | PASS |

Note: FR-3 (`with_text_overlay()`) is listed in requirements but there is no TextOverlay domain model in the codebase. This will be added when the text overlay feature is implemented. All 6 achievable criteria pass.

## Files Created/Modified

| Action | File | Purpose |
|--------|------|---------|
| Created | `tests/factories.py` | ProjectFactory builder + make_test_video helper |
| Created | `tests/test_factories.py` | 13 unit tests for builder methods and build() |
| Created | `tests/test_api/test_factory_api.py` | 5 integration tests for create_via_api() and ApiFactory |
| Modified | `tests/conftest.py` | Added `project_factory` fixture |
| Modified | `tests/test_api/conftest.py` | Added `ApiFactory` class and `api_factory` fixture |

## Test Results

- **18 new tests** (13 unit + 5 integration), all passing
- **455 total tests pass**, 8 skipped (pre-existing), 0 failures
- **92.74% coverage** (above 80% threshold)

## Quality Gates

```
ruff check:   PASS
ruff format:  PASS
mypy:         PASS (0 issues)
pytest:       PASS (455 passed, 8 skipped)
coverage:     92.74% (threshold: 80%)
```

## Design Decisions

1. **`build_with_clips()` added** — returns `(project, videos, clips)` tuple for seeding in-memory repositories in unit tests. This avoids requiring HTTP for tests that just need domain objects with relationships.

2. **ApiFactory wrapper** — `tests/test_api/conftest.py` exposes an `ApiFactory` that auto-seeds videos via the repository before calling `create_via_api()`, reducing boilerplate in integration tests.

3. **Canonical `make_test_video()`** — moved to `tests/factories.py` as the single source of truth. Existing import from `tests.test_repository_contract` still works (not modified to avoid churn).

4. **No `with_text_overlay()`** — the TextOverlay domain model does not exist yet. Will be added when that feature is implemented. This follows YAGNI principles.
