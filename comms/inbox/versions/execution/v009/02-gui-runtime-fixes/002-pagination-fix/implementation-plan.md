# Implementation Plan: pagination-fix

## Overview

Add `count()` method to `AsyncProjectRepository` at the protocol, SQLite, and InMemory levels (mirroring `AsyncVideoRepository`). Wire into the projects router for correct `total` in responses. Add frontend pagination state and UI to the Projects page following the Library page pattern.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/db/project_repository.py` | Modify | Add `count()` to protocol and both implementations |
| `src/stoat_ferret/api/routers/projects.py` | Modify | Use `repo.count()` for total instead of `len(projects)` |
| `gui/src/stores/projectStore.ts` | Modify | Add `page` and `pageSize` state (matching libraryStore pattern) |
| `gui/src/hooks/useProjects.ts` | Modify | Accept `page`/`pageSize` params, send `limit`/`offset` to API |
| `gui/src/pages/ProjectsPage.tsx` | Modify | Add Previous/Next pagination UI (matching LibraryPage pattern) |
| `tests/test_project_repository.py` | Create | Tests for count() in both repository implementations |
| `tests/test_api/test_projects_pagination.py` | Create | Integration test for correct total in API response |

## Test Files

`tests/test_project_repository.py tests/test_api/test_projects_pagination.py`

## Implementation Stages

### Stage 1: Add count() to repository

1. Add `async def count(self) -> int: ...` to `AsyncProjectRepository` protocol
2. Add SQLite implementation: `SELECT COUNT(*) FROM projects`
3. Add InMemory implementation: `len(self._projects)`

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_project_repository.py -x
```

### Stage 2: Wire count() into projects router

1. In the projects list endpoint, replace `total=len(projects)` with `total=await repo.count()`

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_api/test_projects_pagination.py -x
```

### Stage 3: Add frontend pagination

1. Add `page: number` (0-indexed) and `pageSize: number` (default 20) to `projectStore.ts`
2. Add `setPage`, `resetPage` actions to project store
3. Update `useProjects` hook to accept `page`/`pageSize` and compute `limit`/`offset`
4. Add Previous/Next buttons to `ProjectsPage.tsx` with page count display
5. Add page reset when projects are created or deleted

**Verification:**
```bash
cd gui && npx tsc -b && npx vitest run
```

## Test Infrastructure Updates

- Backend: Add project repository test file mirroring video repository count() tests
- Frontend: Add vitest tests for pagination state and UI if matching patterns exist

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx tsc -b && npx vitest run
```

## Risks

- Frontend scope increase from Low to Medium — mitigated by following proven Library page pattern. See `006-critical-thinking/risk-assessment.md`.
- `total` field value change (page-size → true count) — frontend already expects true total for video pagination.

## Commit Message

```
feat(api): fix projects pagination total count and add UI

BL-064: Add count() to AsyncProjectRepository matching video repository
pattern. Wire into projects router for correct total. Add pagination state
and UI to Projects page following Library page pattern.
```