# Implementation Plan: Async Repository

## Step 1: Add Dependencies
Update `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing
    "aiosqlite>=0.19",
]

[project.optional-dependencies]
dev = [
    # ... existing
    "pytest-asyncio>=0.23",
    "httpx>=0.26",
]
```

## Step 2: Configure pytest
Update `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "api: API endpoint tests",
    "contract: Contract tests for protocol compliance",
]
```

## Step 3: Create Async Repository Module
Create `src/stoat_ferret/db/async_repository.py`:

```python
"""Async repository implementations for FastAPI."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

import aiosqlite

from stoat_ferret.db.models import Video

if TYPE_CHECKING:
    from stoat_ferret.db.audit import AuditLogger


class AsyncVideoRepository(Protocol):
    """Protocol defining async video repository operations."""

    async def add(self, video: Video) -> Video: ...
    async def get(self, id: str) -> Video | None: ...
    async def get_by_path(self, path: str) -> Video | None: ...
    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]: ...
    async def search(self, query: str, limit: int = 100) -> list[Video]: ...
    async def update(self, video: Video) -> Video: ...
    async def delete(self, id: str) -> bool: ...


class AsyncSQLiteVideoRepository:
    """Async SQLite implementation of VideoRepository."""

    def __init__(
        self,
        conn: aiosqlite.Connection,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row
        self._audit = audit_logger

    async def add(self, video: Video) -> Video:
        """Add a video to the repository."""
        try:
            await self._conn.execute(
                """
                INSERT INTO videos (
                    id, path, filename, duration_frames,
                    frame_rate_numerator, frame_rate_denominator,
                    width, height, video_codec, audio_codec,
                    file_size, thumbnail_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video.id, video.path, video.filename, video.duration_frames,
                    video.frame_rate_numerator, video.frame_rate_denominator,
                    video.width, video.height, video.video_codec, video.audio_codec,
                    video.file_size, video.thumbnail_path,
                    video.created_at.isoformat(), video.updated_at.isoformat(),
                ),
            )
            await self._conn.commit()
            if self._audit:
                self._audit.log_change("INSERT", "video", video.id)
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Video already exists: {e}") from e
        return video

    async def get(self, id: str) -> Video | None:
        """Get a video by ID."""
        cursor = await self._conn.execute("SELECT * FROM videos WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return self._row_to_video(row) if row else None

    async def get_by_path(self, path: str) -> Video | None:
        """Get a video by file path."""
        cursor = await self._conn.execute("SELECT * FROM videos WHERE path = ?", (path,))
        row = await cursor.fetchone()
        return self._row_to_video(row) if row else None

    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination."""
        cursor = await self._conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._row_to_video(row) for row in rows]

    async def search(self, query: str, limit: int = 100) -> list[Video]:
        """Search videos using FTS5."""
        cursor = await self._conn.execute(
            """
            SELECT v.* FROM videos v
            JOIN videos_fts fts ON v.rowid = fts.rowid
            WHERE videos_fts MATCH ?
            LIMIT ?
            """,
            (f'"{query}"*', limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_video(row) for row in rows]

    async def update(self, video: Video) -> Video:
        """Update an existing video."""
        cursor = await self._conn.execute(
            """
            UPDATE videos SET
                path = ?, filename = ?, duration_frames = ?,
                frame_rate_numerator = ?, frame_rate_denominator = ?,
                width = ?, height = ?, video_codec = ?, audio_codec = ?,
                file_size = ?, thumbnail_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                video.path, video.filename, video.duration_frames,
                video.frame_rate_numerator, video.frame_rate_denominator,
                video.width, video.height, video.video_codec, video.audio_codec,
                video.file_size, video.thumbnail_path, video.updated_at.isoformat(),
                video.id,
            ),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Video {video.id} does not exist")
        return video

    async def delete(self, id: str) -> bool:
        """Delete a video by ID."""
        cursor = await self._conn.execute("DELETE FROM videos WHERE id = ?", (id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_video(self, row: aiosqlite.Row) -> Video:
        """Convert database row to Video."""
        return Video(
            id=row["id"],
            path=row["path"],
            filename=row["filename"],
            duration_frames=row["duration_frames"],
            frame_rate_numerator=row["frame_rate_numerator"],
            frame_rate_denominator=row["frame_rate_denominator"],
            width=row["width"],
            height=row["height"],
            video_codec=row["video_codec"],
            audio_codec=row["audio_codec"],
            file_size=row["file_size"],
            thumbnail_path=row["thumbnail_path"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class AsyncInMemoryVideoRepository:
    """Async in-memory implementation for testing."""

    def __init__(self) -> None:
        self._videos: dict[str, Video] = {}
        self._by_path: dict[str, str] = {}

    async def add(self, video: Video) -> Video:
        if video.id in self._videos:
            raise ValueError(f"Video {video.id} already exists")
        if video.path in self._by_path:
            raise ValueError(f"Video with path {video.path} already exists")
        self._videos[video.id] = video
        self._by_path[video.path] = video.id
        return video

    async def get(self, id: str) -> Video | None:
        return self._videos.get(id)

    async def get_by_path(self, path: str) -> Video | None:
        video_id = self._by_path.get(path)
        return self._videos.get(video_id) if video_id else None

    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        sorted_videos = sorted(
            self._videos.values(), key=lambda v: v.created_at, reverse=True
        )
        return sorted_videos[offset : offset + limit]

    async def search(self, query: str, limit: int = 100) -> list[Video]:
        query_lower = query.lower()
        results = [
            v for v in self._videos.values()
            if query_lower in v.filename.lower() or query_lower in v.path.lower()
        ]
        return results[:limit]

    async def update(self, video: Video) -> Video:
        if video.id not in self._videos:
            raise ValueError(f"Video {video.id} does not exist")
        old_video = self._videos[video.id]
        if old_video.path != video.path:
            del self._by_path[old_video.path]
            self._by_path[video.path] = video.id
        self._videos[video.id] = video
        return video

    async def delete(self, id: str) -> bool:
        video = self._videos.get(id)
        if video is None:
            return False
        del self._by_path[video.path]
        del self._videos[id]
        return True
```

## Step 4: Update Module Exports
Update `src/stoat_ferret/db/__init__.py`:
```python
from stoat_ferret.db.async_repository import (
    AsyncInMemoryVideoRepository,
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
```

## Step 5: Create Contract Tests
Create `tests/test_async_repository_contract.py`:

```python
"""Contract tests for async VideoRepository implementations."""

import sqlite3
from collections.abc import AsyncGenerator

import aiosqlite
import pytest

from stoat_ferret.db.async_repository import (
    AsyncInMemoryVideoRepository,
    AsyncSQLiteVideoRepository,
)
from stoat_ferret.db.schema import create_tables

# Reuse helper from sync tests
from tests.test_repository_contract import make_test_video

AsyncRepositoryType = AsyncSQLiteVideoRepository | AsyncInMemoryVideoRepository


@pytest.fixture(params=["sqlite", "memory"])
async def repository(request: pytest.FixtureRequest) -> AsyncGenerator[AsyncRepositoryType, None]:
    """Provide both async repository implementations."""
    if request.param == "sqlite":
        # Create schema using sync connection
        sync_conn = sqlite3.connect(":memory:")
        create_tables(sync_conn)
        schema_dump = list(sync_conn.iterdump())
        sync_conn.close()
        
        # Apply schema to async connection
        conn = await aiosqlite.connect(":memory:")
        for line in schema_dump:
            if not line.startswith("INSERT"):
                await conn.execute(line)
        await conn.commit()
        
        yield AsyncSQLiteVideoRepository(conn)
        await conn.close()
    else:
        yield AsyncInMemoryVideoRepository()


@pytest.mark.contract
class TestAsyncAddAndGet:
    """Tests for async add() and get() methods."""

    async def test_add_and_get(self, repository: AsyncRepositoryType) -> None:
        """Adding a video allows retrieving it by ID."""
        video = make_test_video()
        await repository.add(video)
        retrieved = await repository.get(video.id)

        assert retrieved is not None
        assert retrieved.id == video.id
        assert retrieved.path == video.path

    async def test_get_nonexistent_returns_none(self, repository: AsyncRepositoryType) -> None:
        """Getting a nonexistent video returns None."""
        result = await repository.get("nonexistent-id")
        assert result is None

    async def test_add_duplicate_id_raises(self, repository: AsyncRepositoryType) -> None:
        """Adding a video with duplicate ID raises ValueError."""
        video = make_test_video()
        await repository.add(video)

        duplicate = make_test_video(id=video.id, path="/videos/different.mp4")
        with pytest.raises(ValueError):
            await repository.add(duplicate)


@pytest.mark.contract
class TestAsyncGetByPath:
    """Tests for async get_by_path() method."""

    async def test_get_by_path(self, repository: AsyncRepositoryType) -> None:
        """Videos can be retrieved by path."""
        video = make_test_video(path="/videos/unique_path.mp4")
        await repository.add(video)

        retrieved = await repository.get_by_path("/videos/unique_path.mp4")
        assert retrieved is not None
        assert retrieved.id == video.id


@pytest.mark.contract
class TestAsyncListVideos:
    """Tests for async list_videos() method."""

    async def test_list_empty(self, repository: AsyncRepositoryType) -> None:
        """Listing empty repository returns empty list."""
        result = await repository.list_videos()
        assert result == []

    async def test_list_with_limit(self, repository: AsyncRepositoryType) -> None:
        """Limit restricts number of returned videos."""
        for _ in range(5):
            await repository.add(make_test_video())

        result = await repository.list_videos(limit=3)
        assert len(result) == 3


@pytest.mark.contract
class TestAsyncSearch:
    """Tests for async search() method."""

    async def test_search_by_filename(self, repository: AsyncRepositoryType) -> None:
        """Search finds videos matching filename."""
        video = make_test_video(filename="my_cool_video.mp4")
        await repository.add(video)

        results = await repository.search("cool")
        assert len(results) == 1
        assert results[0].id == video.id


@pytest.mark.contract
class TestAsyncUpdate:
    """Tests for async update() method."""

    async def test_update_nonexistent_raises(self, repository: AsyncRepositoryType) -> None:
        """Updating nonexistent video raises ValueError."""
        video = make_test_video()
        with pytest.raises(ValueError):
            await repository.update(video)


@pytest.mark.contract
class TestAsyncDelete:
    """Tests for async delete() method."""

    async def test_delete_existing(self, repository: AsyncRepositoryType) -> None:
        """Deleting existing video returns True."""
        video = make_test_video()
        await repository.add(video)
        
        result = await repository.delete(video.id)
        assert result is True
        assert await repository.get(video.id) is None

    async def test_delete_nonexistent(self, repository: AsyncRepositoryType) -> None:
        """Deleting nonexistent video returns False."""
        result = await repository.delete("nonexistent")
        assert result is False
```

## Verification
- `uv run pytest tests/test_async_repository_contract.py -v` passes
- `uv run pytest tests/test_repository_contract.py -v` still passes (sync unchanged)
- `uv run pytest -m contract` runs all contract tests