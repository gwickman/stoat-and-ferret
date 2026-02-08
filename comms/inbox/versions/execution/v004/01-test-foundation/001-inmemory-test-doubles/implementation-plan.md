# Implementation Plan — inmemory-test-doubles

## Overview

Enhance `AsyncInMemoryProjectRepository` with deepcopy isolation and seed helpers. Create `InMemoryJobQueue` with synchronous deterministic execution and configurable outcomes.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|--------|
| Modify | `src/stoat_ferret/db/project_repository.py` | Add deepcopy isolation to AsyncInMemoryProjectRepository |
| Modify | `src/stoat_ferret/db/async_repository.py` | Add seed helpers to AsyncInMemoryVideoRepository |
| Modify | `src/stoat_ferret/db/clip_repository.py` | Add seed helpers to AsyncInMemoryClipRepository |
| Create | `src/stoat_ferret/jobs/queue.py` | AsyncJobQueue protocol + InMemoryJobQueue implementation |
| Create | `src/stoat_ferret/jobs/__init__.py` | Package init |
| Create | `tests/test_doubles/test_inmemory_job_queue.py` | InMemoryJobQueue unit tests |
| Create | `tests/test_doubles/test_inmemory_isolation.py` | Deepcopy isolation tests |
| Create | `tests/test_doubles/__init__.py` | Package init |
| Create | `tests/test_contract/test_repository_parity.py` | InMemory vs SQLite contract tests |

## Implementation Stages

### Stage 1: Deepcopy Isolation
Add `copy.deepcopy()` to all read operations in `AsyncInMemoryProjectRepository`. Add isolation tests proving mutating returned objects doesn't affect the store.

### Stage 2: Seed Helpers
Add `seed(items: list[T])` methods to `AsyncInMemoryProjectRepository`, `AsyncInMemoryVideoRepository`, and `AsyncInMemoryClipRepository`.

### Stage 3: InMemoryJobQueue
Create `AsyncJobQueue` protocol with `submit()`, `get_status()`, and `get_result()` methods. Implement `InMemoryJobQueue` with synchronous execution and configurable outcomes (success/failure/timeout).

### Stage 4: Contract Tests
Add parametrized contract tests verifying InMemory repositories produce the same observable results as SQLite implementations for core operations (CRUD, queries).

## Quality Gates

- All existing tests pass (no regressions)
- New unit tests for InMemoryJobQueue: 8–10 tests
- Deepcopy isolation tests: 3–5 tests
- Contract tests: 5–8 tests
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| Deepcopy performance | Flat scalar dataclasses — negligible (R2 resolved) |
| Contract test false positives | Test observable behavior, not internal state |

## Commit Message

```
feat: add InMemory test doubles with deepcopy isolation and job queue
```