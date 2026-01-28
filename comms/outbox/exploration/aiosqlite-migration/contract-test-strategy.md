# Contract Test Strategy for Async Repositories

## Current Sync Test Pattern

The existing `tests/test_repository_contract.py` uses pytest's parametrized fixtures:

```python
@pytest.fixture(params=["sqlite", "memory"])
def repository(request: pytest.FixtureRequest) -> Generator[RepositoryType, None, None]:
    if request.param == "sqlite":
        conn = sqlite3.connect(":memory:")
        create_tables(conn)
        yield SQLiteVideoRepository(conn)
        conn.close()
    else:
        yield InMemoryVideoRepository()
```

This pattern tests both implementations with identical test methods, ensuring behavioral equivalence.

## Async Contract Test Pattern

### Option 1: Parallel Test File (Recommended)

Create `tests/test_async_repository_contract.py` mirroring the sync tests:

```python
"""Contract tests for AsyncVideoRepository implementations.

These tests run against both AsyncSQLiteVideoRepository and AsyncInMemoryVideoRepository
to verify they have identical behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from stoat_ferret.db.models import Video
from stoat_ferret.db.async_repository import (
    AsyncSQLiteVideoRepository,
    AsyncInMemoryVideoRepository,
)
from stoat_ferret.db.schema import create_tables_async  # or reuse sync


def make_test_video(**kwargs: object) -> Video:
    """Create a test video with default values."""
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Video.new_id(),
        "path": f"/videos/{Video.new_id()}.mp4",
        "filename": "test.mp4",
        "duration_frames": 1000,
        "frame_rate_numerator": 24,
        "frame_rate_denominator": 1,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "file_size": 1000000,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Video(**defaults)  # type: ignore[arg-type]


AsyncRepositoryType = AsyncSQLiteVideoRepository | AsyncInMemoryVideoRepository


@pytest.fixture(params=["sqlite", "memory"])
async def repository(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[AsyncRepositoryType, None]:
    """Provide both async repository implementations for contract testing."""
    if request.param == "sqlite":
        conn = await aiosqlite.connect(":memory:")
        # Note: create_tables is sync, run it on the underlying connection
        create_tables(conn._conn)  # Access internal sync connection
        yield AsyncSQLiteVideoRepository(conn)
        await conn.close()
    else:
        yield AsyncInMemoryVideoRepository()


class TestAsyncAddAndGet:
    """Tests for add() and get() methods."""

    @pytest.mark.asyncio
    async def test_add_and_get(self, repository: AsyncRepositoryType) -> None:
        """Adding a video allows retrieving it by ID."""
        video = make_test_video()
        await repository.add(video)
        retrieved = await repository.get(video.id)

        assert retrieved is not None
        assert retrieved.id == video.id
        assert retrieved.path == video.path
        assert retrieved.filename == video.filename

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(
        self, repository: AsyncRepositoryType
    ) -> None:
        """Getting a nonexistent video returns None."""
        result = await repository.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_add_duplicate_id_raises(
        self, repository: AsyncRepositoryType
    ) -> None:
        """Adding a video with duplicate ID raises ValueError."""
        video = make_test_video()
        await repository.add(video)

        duplicate = make_test_video(id=video.id, path="/videos/different.mp4")
        with pytest.raises(ValueError):
            await repository.add(duplicate)

    @pytest.mark.asyncio
    async def test_add_duplicate_path_raises(
        self, repository: AsyncRepositoryType
    ) -> None:
        """Adding a video with duplicate path raises ValueError."""
        video = make_test_video()
        await repository.add(video)

        duplicate = make_test_video(path=video.path)
        with pytest.raises(ValueError):
            await repository.add(duplicate)


# ... continue pattern for all other test classes
```

### Option 2: Shared Test Logic with Adapters

Create adapters that unify sync/async interfaces for testing:

```python
"""Unified contract tests using anyio for sync/async compatibility."""

from typing import Protocol, Union
import anyio

class UnifiedRepository(Protocol):
    """Protocol that works for both sync and async."""
    def add(self, video: Video) -> Video: ...
    def get(self, id: str) -> Video | None: ...


class SyncWrapper:
    """Wraps sync repository to run in async context."""
    def __init__(self, repo: SQLiteVideoRepository):
        self._repo = repo

    async def add(self, video: Video) -> Video:
        return await anyio.to_thread.run_sync(self._repo.add, video)

    async def get(self, id: str) -> Video | None:
        return await anyio.to_thread.run_sync(self._repo.get, id)


# Then use same async tests for all implementations
```

**Verdict**: More complexity than benefit. Keep tests separate.

### Option 3: pytest-asyncio Plugin with anyio

```python
import pytest
import anyio

@pytest.fixture(params=["sync-sqlite", "sync-memory", "async-sqlite", "async-memory"])
async def repository(request):
    """Unified fixture for all repository types."""
    # ...
```

**Verdict**: Mixing sync/async adds confusion. Better to keep clear separation.

## Recommended Approach

### File Structure

```
tests/
├── test_repository_contract.py        # Sync tests (existing)
├── test_async_repository_contract.py  # Async tests (new)
└── conftest.py                        # Shared fixtures
```

### conftest.py Shared Fixtures

```python
"""Shared test utilities for repository tests."""

from datetime import datetime, timezone

import pytest

from stoat_ferret.db.models import Video


def make_test_video(**kwargs: object) -> Video:
    """Create a test video with default values.

    Shared between sync and async contract tests.
    """
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": Video.new_id(),
        "path": f"/videos/{Video.new_id()}.mp4",
        "filename": "test.mp4",
        "duration_frames": 1000,
        "frame_rate_numerator": 24,
        "frame_rate_denominator": 1,
        "width": 1920,
        "height": 1080,
        "video_codec": "h264",
        "file_size": 1000000,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Video(**defaults)  # type: ignore[arg-type]
```

### pytest Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"  # Automatically detect and run async tests
```

Or use explicit markers:

```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
markers = [
    "asyncio: mark test as async",
]
```

### Schema Creation for Async Tests

Option A: Use sync schema creation on raw connection:

```python
@pytest.fixture
async def async_sqlite_repository():
    conn = await aiosqlite.connect(":memory:")
    # aiosqlite wraps a sync connection - access it for schema
    create_tables(conn._conn)
    yield AsyncSQLiteVideoRepository(conn)
    await conn.close()
```

Option B: Create async schema helper:

```python
async def create_tables_async(conn: aiosqlite.Connection) -> None:
    """Create database tables asynchronously."""
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
```

## Test Execution

```bash
# Run all tests
uv run pytest

# Run only sync contract tests
uv run pytest tests/test_repository_contract.py

# Run only async contract tests
uv run pytest tests/test_async_repository_contract.py

# Run with coverage
uv run pytest --cov=src --cov-fail-under=80
```

## Dependencies Required

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "aiosqlite>=0.19",
]
```

## Cross-Implementation Behavioral Verification

Both test files should verify:

1. **Add/Get semantics**: Same return values, same exceptions
2. **Duplicate handling**: Both raise `ValueError` for duplicate ID/path
3. **Search behavior**: Case-insensitive, partial matching
4. **Pagination**: Same ordering (created_at DESC), same limit/offset behavior
5. **Update semantics**: Path index updates correctly
6. **Delete semantics**: Returns True/False consistently

The parametrized fixture pattern naturally enforces this by running identical test code against both implementations.

## Summary

| Aspect | Recommendation |
|--------|----------------|
| Test organization | Separate files for sync/async |
| Fixture pattern | Same parametrized pattern, async generator |
| Shared code | `make_test_video()` in conftest.py |
| Test framework | pytest + pytest-asyncio |
| Async mode | `asyncio_mode = "auto"` |
