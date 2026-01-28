# AsyncVideoRepository Pattern

## Overview

This document shows how to create an async version of VideoRepository that mirrors the existing sync protocol while maintaining protocol compatibility for type checking.

## Protocol Design

### Option 1: Separate Async Protocol (Recommended)

```python
"""Async repository protocol for video metadata storage."""

from __future__ import annotations

from typing import Protocol

from stoat_ferret.db.models import Video


class AsyncVideoRepository(Protocol):
    """Protocol defining async video repository operations.

    Mirrors VideoRepository with async methods.
    """

    async def add(self, video: Video) -> Video:
        """Add a video to the repository."""
        ...

    async def get(self, id: str) -> Video | None:
        """Get a video by its ID."""
        ...

    async def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path."""
        ...

    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination."""
        ...

    async def search(self, query: str, limit: int = 100) -> list[Video]:
        """Search videos by filename or path."""
        ...

    async def update(self, video: Video) -> Video:
        """Update an existing video."""
        ...

    async def delete(self, id: str) -> bool:
        """Delete a video by its ID."""
        ...
```

### Option 2: Generic Protocol with TypeVar

```python
from typing import Protocol, TypeVar, Generic, Awaitable

T = TypeVar('T')

class VideoRepositoryBase(Protocol, Generic[T]):
    def add(self, video: Video) -> T: ...
    def get(self, id: str) -> T: ...

# Usage:
# VideoRepository = VideoRepositoryBase[Video | None]
# AsyncVideoRepository = VideoRepositoryBase[Awaitable[Video | None]]
```

**Not Recommended**: Overly complex, harder to read, doesn't provide real benefits.

## AsyncSQLiteVideoRepository Implementation

```python
"""Async SQLite repository implementation."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING

import aiosqlite

from stoat_ferret.db.models import Video

if TYPE_CHECKING:
    from stoat_ferret.db.audit import AuditLogger


class AsyncSQLiteVideoRepository:
    """Async SQLite implementation of the AsyncVideoRepository protocol."""

    def __init__(
        self,
        conn: aiosqlite.Connection,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        """Initialize the repository with an aiosqlite connection.

        Args:
            conn: aiosqlite database connection.
            audit_logger: Optional audit logger for tracking changes.
        """
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
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
                    video.id,
                    video.path,
                    video.filename,
                    video.duration_frames,
                    video.frame_rate_numerator,
                    video.frame_rate_denominator,
                    video.width,
                    video.height,
                    video.video_codec,
                    video.audio_codec,
                    video.file_size,
                    video.thumbnail_path,
                    video.created_at.isoformat(),
                    video.updated_at.isoformat(),
                ),
            )
            await self._conn.commit()
            if self._audit:
                self._audit.log_change("INSERT", "video", video.id)
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Video already exists: {e}") from e
        return video

    async def get(self, id: str) -> Video | None:
        """Get a video by its ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM videos WHERE id = ?", (id,)
        )
        row = await cursor.fetchone()
        return self._row_to_video(row) if row else None

    async def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path."""
        cursor = await self._conn.execute(
            "SELECT * FROM videos WHERE path = ?", (path,)
        )
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
        """Search videos using FTS5 full-text search."""
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
        old = await self.get(video.id) if self._audit else None
        cursor = await self._conn.execute(
            """
            UPDATE videos SET
                path = ?,
                filename = ?,
                duration_frames = ?,
                frame_rate_numerator = ?,
                frame_rate_denominator = ?,
                width = ?,
                height = ?,
                video_codec = ?,
                audio_codec = ?,
                file_size = ?,
                thumbnail_path = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                video.path,
                video.filename,
                video.duration_frames,
                video.frame_rate_numerator,
                video.frame_rate_denominator,
                video.width,
                video.height,
                video.video_codec,
                video.audio_codec,
                video.file_size,
                video.thumbnail_path,
                video.updated_at.isoformat(),
                video.id,
            ),
        )
        await self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Video {video.id} does not exist")
        if self._audit and old:
            changes = self._compute_diff(old, video)
            self._audit.log_change("UPDATE", "video", video.id, changes)
        return video

    async def delete(self, id: str) -> bool:
        """Delete a video by its ID."""
        cursor = await self._conn.execute(
            "DELETE FROM videos WHERE id = ?", (id,)
        )
        await self._conn.commit()
        deleted = cursor.rowcount > 0
        if deleted and self._audit:
            self._audit.log_change("DELETE", "video", id)
        return deleted

    def _row_to_video(self, row: sqlite3.Row) -> Video:
        """Convert a database row to a Video object.

        Note: This is sync because row_factory already parsed the row.
        """
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

    def _compute_diff(self, old: Video, new: Video) -> dict[str, object]:
        """Compute differences between old and new video states."""
        changes: dict[str, object] = {}
        fields = [
            "path", "filename", "duration_frames", "frame_rate_numerator",
            "frame_rate_denominator", "width", "height", "video_codec",
            "audio_codec", "file_size", "thumbnail_path",
        ]
        for field in fields:
            old_val = getattr(old, field)
            new_val = getattr(new, field)
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}
        return changes
```

## AsyncInMemoryVideoRepository Implementation

```python
"""Async in-memory repository for testing."""

from __future__ import annotations

from stoat_ferret.db.models import Video


class AsyncInMemoryVideoRepository:
    """Async in-memory implementation of AsyncVideoRepository.

    Useful for testing without a database.
    Note: All methods are async even though operations are sync.
    This maintains protocol compatibility.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._videos: dict[str, Video] = {}
        self._by_path: dict[str, str] = {}

    async def add(self, video: Video) -> Video:
        """Add a video to the repository."""
        if video.id in self._videos:
            raise ValueError(f"Video {video.id} already exists")
        if video.path in self._by_path:
            raise ValueError(f"Video with path {video.path} already exists")
        self._videos[video.id] = video
        self._by_path[video.path] = video.id
        return video

    async def get(self, id: str) -> Video | None:
        """Get a video by its ID."""
        return self._videos.get(id)

    async def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path."""
        video_id = self._by_path.get(path)
        return self._videos.get(video_id) if video_id else None

    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination."""
        sorted_videos = sorted(
            self._videos.values(),
            key=lambda v: v.created_at,
            reverse=True,
        )
        return sorted_videos[offset : offset + limit]

    async def search(self, query: str, limit: int = 100) -> list[Video]:
        """Search videos by filename or path."""
        query_lower = query.lower()
        results = [
            v for v in self._videos.values()
            if query_lower in v.filename.lower() or query_lower in v.path.lower()
        ]
        return results[:limit]

    async def update(self, video: Video) -> Video:
        """Update an existing video."""
        if video.id not in self._videos:
            raise ValueError(f"Video {video.id} does not exist")
        old_video = self._videos[video.id]
        if old_video.path != video.path:
            del self._by_path[old_video.path]
            self._by_path[video.path] = video.id
        self._videos[video.id] = video
        return video

    async def delete(self, id: str) -> bool:
        """Delete a video by its ID."""
        video = self._videos.get(id)
        if video is None:
            return False
        del self._by_path[video.path]
        del self._videos[id]
        return True
```

## FastAPI Connection Management

### Lifespan Pattern (Recommended)

```python
"""FastAPI application with async database connection."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite
from fastapi import Depends, FastAPI

from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage database connection lifecycle."""
    # Startup
    app.state.db = await aiosqlite.connect("stoat_ferret.db")
    app.state.db.row_factory = aiosqlite.Row

    yield

    # Shutdown
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)


async def get_repository() -> AsyncIterator[AsyncSQLiteVideoRepository]:
    """Dependency that provides a repository instance."""
    yield AsyncSQLiteVideoRepository(app.state.db)


@app.get("/videos/{video_id}")
async def get_video(
    video_id: str,
    repo: AsyncSQLiteVideoRepository = Depends(get_repository),
):
    video = await repo.get(video_id)
    if not video:
        raise HTTPException(404)
    return video
```

### Connection Pooling (Optional)

For higher traffic, consider [aiosqlitepool](https://github.com/slaily/aiosqlitepool):

```python
from aiosqlitepool import Pool

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.pool = await Pool.create(
        database="stoat_ferret.db",
        min_size=2,
        max_size=10,
    )
    yield
    await app.state.pool.close()


async def get_repository() -> AsyncIterator[AsyncSQLiteVideoRepository]:
    async with app.state.pool.acquire() as conn:
        yield AsyncSQLiteVideoRepository(conn)
```

## File Organization Recommendation

```
src/stoat_ferret/db/
├── models.py              # Video dataclass (unchanged)
├── schema.py              # Table creation (unchanged)
├── audit.py               # Audit logger (unchanged)
├── repository.py          # Sync protocols and implementations
└── async_repository.py    # Async protocols and implementations
```

Or, if preferring protocol separation:

```
src/stoat_ferret/db/
├── protocols.py           # VideoRepository protocol
├── async_protocols.py     # AsyncVideoRepository protocol
├── sqlite_repository.py   # SQLiteVideoRepository
├── async_sqlite_repository.py  # AsyncSQLiteVideoRepository
├── memory_repository.py   # InMemoryVideoRepository
└── async_memory_repository.py  # AsyncInMemoryVideoRepository
```

## Recommendation

Use **Option 1 (Separate Async Protocol)** with `async_repository.py` containing:
- `AsyncVideoRepository` protocol
- `AsyncSQLiteVideoRepository` implementation
- `AsyncInMemoryVideoRepository` implementation

This keeps async concerns isolated while maintaining the existing sync implementations for CLI/batch operations.
