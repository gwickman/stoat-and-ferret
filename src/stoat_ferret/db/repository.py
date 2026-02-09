"""Repository pattern implementations for video metadata storage."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from stoat_ferret.db.models import Video

if TYPE_CHECKING:
    from stoat_ferret.db.audit import AuditLogger


class VideoRepository(Protocol):
    """Protocol defining video repository operations.

    Implementations must provide methods for CRUD operations
    and search functionality on video metadata.
    """

    def add(self, video: Video) -> Video:
        """Add a video to the repository.

        Args:
            video: The video to add.

        Returns:
            The added video.

        Raises:
            ValueError: If a video with the same ID or path already exists.
        """
        ...

    def get(self, id: str) -> Video | None:
        """Get a video by its ID.

        Args:
            id: The video ID.

        Returns:
            The video if found, None otherwise.
        """
        ...

    def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path.

        Args:
            path: The file path.

        Returns:
            The video if found, None otherwise.
        """
        ...

    def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination.

        Args:
            limit: Maximum number of videos to return.
            offset: Number of videos to skip.

        Returns:
            List of videos.
        """
        ...

    def search(self, query: str, limit: int = 100) -> list[Video]:
        """Search videos by filename or path.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of matching videos.
        """
        ...

    def update(self, video: Video) -> Video:
        """Update an existing video.

        Args:
            video: The video with updated fields.

        Returns:
            The updated video.

        Raises:
            ValueError: If the video does not exist.
        """
        ...

    def delete(self, id: str) -> bool:
        """Delete a video by its ID.

        Args:
            id: The video ID.

        Returns:
            True if the video was deleted, False if it didn't exist.
        """
        ...


class SQLiteVideoRepository:
    """SQLite implementation of the VideoRepository protocol."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        """Initialize the repository with a database connection.

        Args:
            conn: SQLite database connection.
            audit_logger: Optional audit logger for tracking changes.
        """
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._audit = audit_logger

    def add(self, video: Video) -> Video:
        """Add a video to the repository."""
        try:
            self._conn.execute(
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
            self._conn.commit()
            if self._audit:
                self._audit.log_change("INSERT", "video", video.id)
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Video already exists: {e}") from e
        return video

    def get(self, id: str) -> Video | None:
        """Get a video by its ID."""
        cursor = self._conn.execute("SELECT * FROM videos WHERE id = ?", (id,))
        row = cursor.fetchone()
        return self._row_to_video(row) if row else None

    def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path."""
        cursor = self._conn.execute("SELECT * FROM videos WHERE path = ?", (path,))
        row = cursor.fetchone()
        return self._row_to_video(row) if row else None

    def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination."""
        cursor = self._conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [self._row_to_video(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 100) -> list[Video]:
        """Search videos using FTS5 full-text search."""
        # Use FTS5 MATCH for efficient search
        cursor = self._conn.execute(
            """
            SELECT v.* FROM videos v
            JOIN videos_fts fts ON v.rowid = fts.rowid
            WHERE videos_fts MATCH ?
            LIMIT ?
            """,
            (f'"{query}"*', limit),
        )
        return [self._row_to_video(row) for row in cursor.fetchall()]

    def update(self, video: Video) -> Video:
        """Update an existing video."""
        old = self.get(video.id) if self._audit else None
        cursor = self._conn.execute(
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
        self._conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Video {video.id} does not exist")
        if self._audit and old:
            changes = self._compute_diff(old, video)
            self._audit.log_change("UPDATE", "video", video.id, changes)
        return video

    def _compute_diff(self, old: Video, new: Video) -> dict[str, object]:
        """Compute differences between old and new video states."""
        changes: dict[str, object] = {}
        fields = [
            "path",
            "filename",
            "duration_frames",
            "frame_rate_numerator",
            "frame_rate_denominator",
            "width",
            "height",
            "video_codec",
            "audio_codec",
            "file_size",
            "thumbnail_path",
        ]
        for field in fields:
            old_val = getattr(old, field)
            new_val = getattr(new, field)
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}
        return changes

    def delete(self, id: str) -> bool:
        """Delete a video by its ID."""
        cursor = self._conn.execute("DELETE FROM videos WHERE id = ?", (id,))
        self._conn.commit()
        deleted = cursor.rowcount > 0
        if deleted and self._audit:
            self._audit.log_change("DELETE", "video", id)
        return deleted

    def _row_to_video(self, row: sqlite3.Row) -> Video:
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


class InMemoryVideoRepository:
    """In-memory implementation of the VideoRepository protocol.

    Useful for testing without a database.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._videos: dict[str, Video] = {}
        self._by_path: dict[str, str] = {}  # path -> id for fast lookup

    def add(self, video: Video) -> Video:
        """Add a video to the repository."""
        if video.id in self._videos:
            raise ValueError(f"Video {video.id} already exists")
        if video.path in self._by_path:
            raise ValueError(f"Video with path {video.path} already exists")
        self._videos[video.id] = video
        self._by_path[video.path] = video.id
        return video

    def get(self, id: str) -> Video | None:
        """Get a video by its ID."""
        return self._videos.get(id)

    def get_by_path(self, path: str) -> Video | None:
        """Get a video by its file path."""
        video_id = self._by_path.get(path)
        return self._videos.get(video_id) if video_id else None

    def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]:
        """List videos with pagination."""
        # Sort by created_at descending to match SQLite behavior
        sorted_videos = sorted(self._videos.values(), key=lambda v: v.created_at, reverse=True)
        return sorted_videos[offset : offset + limit]

    def search(self, query: str, limit: int = 100) -> list[Video]:
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
        return results[:limit]

    def update(self, video: Video) -> Video:
        """Update an existing video."""
        if video.id not in self._videos:
            raise ValueError(f"Video {video.id} does not exist")
        old_video = self._videos[video.id]
        # Update path index if path changed
        if old_video.path != video.path:
            del self._by_path[old_video.path]
            self._by_path[video.path] = video.id
        self._videos[video.id] = video
        return video

    def delete(self, id: str) -> bool:
        """Delete a video by its ID."""
        video = self._videos.get(id)
        if video is None:
            return False
        del self._by_path[video.path]
        del self._videos[id]
        return True
