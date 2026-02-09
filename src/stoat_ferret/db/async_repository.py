"""Async repository implementations for FastAPI."""

from __future__ import annotations

import copy
import re
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

import aiosqlite

from stoat_ferret.db.models import Video

if TYPE_CHECKING:
    from stoat_ferret.db.audit import AuditLogger


class AsyncVideoRepository(Protocol):
    """Protocol defining async video repository operations.

    Implementations must provide async methods for CRUD operations
    and search functionality on video metadata.
    """

    async def add(self, video: Video) -> Video:
        """Add a video to the repository.

        Args:
            video: The video to add.

        Returns:
            The added video.

        Raises:
            ValueError: If a video with the same ID or path already exists.
        """
        ...

    async def get(self, id: str) -> Video | None:
        """Get a video by its ID.

        Args:
            id: The video ID.

        Returns:
            The video if found, None otherwise.
        """
        ...

    async def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path.

        Args:
            path: The file path.

        Returns:
            The video if found, None otherwise.
        """
        ...

    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination.

        Args:
            limit: Maximum number of videos to return.
            offset: Number of videos to skip.

        Returns:
            List of videos.
        """
        ...

    async def search(self, query: str, limit: int = 100) -> list[Video]:
        """Search videos by filename or path.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of matching videos.
        """
        ...

    async def update(self, video: Video) -> Video:
        """Update an existing video.

        Args:
            video: The video with updated fields.

        Returns:
            The updated video.

        Raises:
            ValueError: If the video does not exist.
        """
        ...

    async def delete(self, id: str) -> bool:
        """Delete a video by its ID.

        Args:
            id: The video ID.

        Returns:
            True if the video was deleted, False if it didn't exist.
        """
        ...


class AsyncSQLiteVideoRepository:
    """Async SQLite implementation of the VideoRepository protocol."""

    def __init__(
        self,
        conn: aiosqlite.Connection,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
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
        cursor = await self._conn.execute("SELECT * FROM videos WHERE id = ?", (id,))
        row = await cursor.fetchone()
        return self._row_to_video(row) if row else None

    async def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path."""
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
        return video

    async def delete(self, id: str) -> bool:
        """Delete a video by its ID."""
        cursor = await self._conn.execute("DELETE FROM videos WHERE id = ?", (id,))
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_video(self, row: Any) -> Video:
        """Convert a database row to a Video object."""
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


def _any_token_startswith(text: str, prefix: str) -> bool:
    """Check if any token in text starts with the given prefix.

    Tokenizes text by splitting on non-alphanumeric characters,
    then checks if any resulting token starts with the prefix.
    Both text and prefix are compared case-insensitively.

    Args:
        text: The text to tokenize and search.
        prefix: The prefix to match against tokens (must be lowercase).

    Returns:
        True if any token starts with the prefix.
    """
    tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return any(token.startswith(prefix) for token in tokens if token)


class AsyncInMemoryVideoRepository:
    """Async in-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._videos: dict[str, Video] = {}
        self._by_path: dict[str, str] = {}  # path -> id for fast lookup

    async def add(self, video: Video) -> Video:
        """Add a video to the repository."""
        if video.id in self._videos:
            raise ValueError(f"Video {video.id} already exists")
        if video.path in self._by_path:
            raise ValueError(f"Video with path {video.path} already exists")
        self._videos[video.id] = copy.deepcopy(video)
        self._by_path[video.path] = video.id
        return copy.deepcopy(video)

    async def get(self, id: str) -> Video | None:
        """Get a video by its ID."""
        video = self._videos.get(id)
        return copy.deepcopy(video) if video is not None else None

    async def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path."""
        video_id = self._by_path.get(path)
        if video_id is None:
            return None
        video = self._videos.get(video_id)
        return copy.deepcopy(video) if video is not None else None

    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination."""
        sorted_videos = sorted(self._videos.values(), key=lambda v: v.created_at, reverse=True)
        return [copy.deepcopy(v) for v in sorted_videos[offset : offset + limit]]

    async def search(self, query: str, limit: int = 100) -> list[Video]:
        """Search videos by filename or path using per-token prefix matching.

        Tokenizes filenames and paths by non-alphanumeric characters, then
        checks if any token starts with the query. This approximates FTS5
        prefix-match semantics used by the SQLite implementation.

        Known differences from FTS5:
            (a) Multi-word phrase handling — FTS5 supports adjacent-token
                phrase queries; this implementation treats the query as a
                single token prefix.
            (b) Field scope — FTS5 indexes filename and path together;
                this implementation checks them separately.
            (c) Tokenization rules — FTS5 uses the unicode61 tokenizer;
                this implementation splits on non-alphanumeric characters.
        """
        query_lower = query.lower()
        results = [
            v
            for v in self._videos.values()
            if _any_token_startswith(v.filename, query_lower)
            or _any_token_startswith(v.path, query_lower)
        ]
        return [copy.deepcopy(v) for v in results[:limit]]

    async def update(self, video: Video) -> Video:
        """Update an existing video."""
        if video.id not in self._videos:
            raise ValueError(f"Video {video.id} does not exist")
        old_video = self._videos[video.id]
        # Update path index if path changed
        if old_video.path != video.path:
            del self._by_path[old_video.path]
            self._by_path[video.path] = video.id
        self._videos[video.id] = copy.deepcopy(video)
        return copy.deepcopy(video)

    async def delete(self, id: str) -> bool:
        """Delete a video by its ID."""
        video = self._videos.get(id)
        if video is None:
            return False
        del self._by_path[video.path]
        del self._videos[id]
        return True

    def seed(self, videos: list[Video]) -> None:
        """Populate the repository with initial test data.

        Args:
            videos: List of videos to seed. Stored as deepcopies.
        """
        for video in videos:
            self._videos[video.id] = copy.deepcopy(video)
            self._by_path[video.path] = video.id
