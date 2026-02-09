# Implementation Plan - 002: Pagination Total Count

## Overview

Add a `count()` method to the `AsyncVideoRepository` protocol and both implementations (SQLite and InMemory), then fix the `list_videos` and `search` endpoints to return the true total count instead of the page length.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/db/async_repository.py` | Modify | Add `count()` to `AsyncVideoRepository` protocol |
| `src/stoat_ferret/db/async_sqlite_repository.py` | Modify | Implement `count()` with `SELECT COUNT(*)` |
| `src/stoat_ferret/db/async_inmemory_repository.py` | Modify | Implement `count()` with `len()` |
| `src/stoat_ferret/api/routers/videos.py` | Modify | Fix `list_videos` and `search` to use `count()` for total |
| `tests/test_repository.py` | Modify | Add `count()` tests for both implementations |
| `tests/test_videos_router.py` | Modify | Update pagination tests to verify true total |

## Implementation Stages

### Stage 1: Repository Protocol and Implementations

1. Add `async def count(self) -> int` to `AsyncVideoRepository` protocol
2. Implement in `AsyncSQLiteVideoRepository`: execute `SELECT COUNT(*) FROM videos` and return result
3. Implement in `AsyncInMemoryVideoRepository`: return `len(self._videos)`
4. Add unit tests for both implementations

**Verification:**
```bash
uv run pytest tests/test_repository.py -v -k count
```

### Stage 2: Router Fix

1. In `list_videos` endpoint: call `repo.count()` and use result as `total` instead of `len(videos)`
2. In `search` endpoint: use full result count (not page-sliced count) as `total`
3. Update existing pagination tests to verify `total` reflects full dataset size

**Verification:**
```bash
uv run pytest tests/test_videos_router.py -v
uv run ruff check src/ tests/
uv run mypy src/
```

## Test Infrastructure Updates

- Repository tests extended with `count()` assertions
- Router tests verify `total` field accuracy across pagination scenarios (page 1, page 2, etc.)

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

None significant. This is a focused tech debt fix with well-defined scope (protocol + 2 implementations + 2 router lines).

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
fix: return true total count in paginated list and search endpoints

- Add count() method to AsyncVideoRepository protocol
- Implement count() in SQLite (SELECT COUNT(*)) and InMemory (len())
- Fix list_videos and search endpoints to return true total
- Update pagination tests to verify total accuracy

Fixes BL-034
```