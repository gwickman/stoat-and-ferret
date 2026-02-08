# Implementation Plan — dependency-injection

## Overview

Add optional injectable parameters to `create_app()` and migrate test conftest from `dependency_overrides` to direct parameter injection.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret/api/app.py` | Add optional params to `create_app()` |
| Modify | `src/stoat_ferret/api/routers/videos.py` | Update dependency functions to use app.state |
| Modify | `src/stoat_ferret/api/routers/projects.py` | Update dependency functions to use app.state |
| Modify | `tests/test_api/conftest.py` | Replace `dependency_overrides` with `create_app()` params |
| Create | `tests/test_api/test_di_wiring.py` | Integration test for DI end-to-end |

## Implementation Stages

### Stage 1: Extend create_app()
Add optional parameters to `create_app()`: `repository`, `video_repository`, `clip_repository`, `executor`, `job_queue`. When `None`, use production defaults via lifespan. When provided, store on `app.state` and skip production initialization for those deps.

### Stage 2: Update Dependency Functions
Modify `get_repository()`, `get_video_repository()`, `get_project_repository()`, `get_clip_repository()` to read from `request.app.state` instead of constructing new instances. This allows both injected and lifespan-initialized deps to be retrieved uniformly.

### Stage 3: Migrate Test Conftest
Replace 4 `dependency_overrides` lines with `create_app(video_repository=inmem_video, project_repository=inmem_project, ...)`. Consolidate `get_repository`/`get_video_repository` alias.

### Stage 4: Integration Test
Add `test_di_wiring.py` demonstrating: `create_app(repository=InMemoryRepo())` → TestClient → API call → verify data in InMemory store.

## Quality Gates

- All existing API tests pass without modification (regression)
- Zero `dependency_overrides` remaining in conftest
- `uv run ruff check src/ tests/` passes
- `uv run mypy src/` passes
- New integration test passes

## Risks

| Risk | Mitigation |
|------|------------|
| Breaking existing tests during migration | Stage 3 is incremental — migrate one override at a time |
| Lifespan initialization conflict | Conditional logic: skip production init for injected deps |

## Commit Message

```
feat: add dependency injection to create_app() for test wiring
```
