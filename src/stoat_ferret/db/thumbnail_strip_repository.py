"""Thumbnail strip repository implementations for strip persistence.

Provides Protocol, SQLite, and InMemory implementations following the
established repository triple pattern used by other domain entities.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Protocol, runtime_checkable

import aiosqlite
import structlog

from stoat_ferret.db.models import ThumbnailStrip, ThumbnailStripStatus

logger = structlog.get_logger(__name__)

# Valid status transitions: from -> set of allowed targets
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"generating"},
    "generating": {"ready", "error"},
}


def _validate_status_transition(current: str, new: str) -> None:
    """Validate that a status transition is allowed.

    Args:
        current: Current status value.
        new: Proposed new status value.

    Raises:
        ValueError: If the transition is not allowed.
    """
    allowed = _VALID_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValueError(
            f"Invalid status transition: {current!r} -> {new!r}. "
            f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
        )


@runtime_checkable
class AsyncThumbnailStripRepository(Protocol):
    """Protocol for async thumbnail strip repository operations.

    Implementations must provide async methods for CRUD operations
    on thumbnail strip records.
    """

    async def add(self, strip: ThumbnailStrip) -> ThumbnailStrip:
        """Add a new thumbnail strip record.

        Args:
            strip: The thumbnail strip to add.

        Returns:
            The added thumbnail strip record.

        Raises:
            ValueError: If a strip with the same ID already exists.
        """
        ...

    async def get(self, strip_id: str) -> ThumbnailStrip | None:
        """Get a thumbnail strip by ID.

        Args:
            strip_id: The thumbnail strip UUID.

        Returns:
            The thumbnail strip if found, None otherwise.
        """
        ...

    async def get_by_video(self, video_id: str) -> ThumbnailStrip | None:
        """Get a thumbnail strip by video ID.

        Args:
            video_id: The source video UUID.

        Returns:
            The thumbnail strip if found, None otherwise.
        """
        ...

    async def update_status(
        self,
        strip_id: str,
        status: ThumbnailStripStatus,
        *,
        file_path: str | None = None,
        frame_count: int | None = None,
        rows: int | None = None,
    ) -> None:
        """Update the status of a thumbnail strip.

        Validates state transitions.

        Args:
            strip_id: The thumbnail strip UUID.
            status: New status value.
            file_path: Updated file path (optional, typically set on ready).
            frame_count: Updated frame count (optional, typically set on ready).
            rows: Updated row count (optional, typically set on ready).

        Raises:
            ValueError: If the strip is not found or transition is invalid.
        """
        ...

    async def delete(self, strip_id: str) -> bool:
        """Delete a thumbnail strip record.

        Args:
            strip_id: The thumbnail strip UUID.

        Returns:
            True if deleted, False if not found.
        """
        ...


class SQLiteThumbnailStripRepository:
    """Async SQLite implementation of the thumbnail strip repository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, strip: ThumbnailStrip) -> ThumbnailStrip:
        """Add a new thumbnail strip record to SQLite."""
        try:
            await self._conn.execute(
                """
                INSERT INTO thumbnail_strips
                    (id, video_id, status, file_path, frame_count,
                     frame_width, frame_height, interval_seconds, columns, rows, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strip.id,
                    strip.video_id,
                    strip.status.value,
                    strip.file_path,
                    strip.frame_count,
                    strip.frame_width,
                    strip.frame_height,
                    strip.interval_seconds,
                    strip.columns,
                    strip.rows,
                    strip.created_at.isoformat(),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Thumbnail strip already exists with id {strip.id}") from e
        return strip

    async def get(self, strip_id: str) -> ThumbnailStrip | None:
        """Get a thumbnail strip by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM thumbnail_strips WHERE id = ?",
            (strip_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_strip(row) if row else None

    async def get_by_video(self, video_id: str) -> ThumbnailStrip | None:
        """Get a thumbnail strip by source video ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM thumbnail_strips WHERE video_id = ? ORDER BY created_at DESC LIMIT 1",
            (video_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_strip(row) if row else None

    async def update_status(
        self,
        strip_id: str,
        status: ThumbnailStripStatus,
        *,
        file_path: str | None = None,
        frame_count: int | None = None,
        rows: int | None = None,
    ) -> None:
        """Update the status of a thumbnail strip with transition validation."""
        current = await self.get(strip_id)
        if current is None:
            raise ValueError(f"Thumbnail strip {strip_id} not found")

        _validate_status_transition(current.status.value, status.value)

        new_file_path = file_path if file_path is not None else current.file_path
        new_frame_count = frame_count if frame_count is not None else current.frame_count
        new_rows = rows if rows is not None else current.rows

        await self._conn.execute(
            """
            UPDATE thumbnail_strips
            SET status = ?, file_path = ?, frame_count = ?, rows = ?
            WHERE id = ?
            """,
            (
                status.value,
                new_file_path,
                new_frame_count,
                new_rows,
                strip_id,
            ),
        )
        await self._conn.commit()

    async def delete(self, strip_id: str) -> bool:
        """Delete a thumbnail strip record."""
        cursor = await self._conn.execute(
            "DELETE FROM thumbnail_strips WHERE id = ?",
            (strip_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_strip(self, row: aiosqlite.Row) -> ThumbnailStrip:
        """Convert a database row to a ThumbnailStrip.

        Args:
            row: Database row.

        Returns:
            ThumbnailStrip instance.
        """
        return ThumbnailStrip(
            id=row["id"],
            video_id=row["video_id"],
            status=ThumbnailStripStatus(row["status"]),
            file_path=row["file_path"],
            frame_count=row["frame_count"],
            frame_width=row["frame_width"],
            frame_height=row["frame_height"],
            interval_seconds=row["interval_seconds"],
            columns=row["columns"],
            rows=row["rows"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class InMemoryThumbnailStripRepository:
    """In-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._strips: dict[str, ThumbnailStrip] = {}

    async def add(self, strip: ThumbnailStrip) -> ThumbnailStrip:
        """Add a new thumbnail strip record in memory."""
        if strip.id in self._strips:
            raise ValueError(f"Thumbnail strip already exists with id {strip.id}")
        self._strips[strip.id] = copy.deepcopy(strip)
        return copy.deepcopy(strip)

    async def get(self, strip_id: str) -> ThumbnailStrip | None:
        """Get a thumbnail strip by ID."""
        strip = self._strips.get(strip_id)
        return copy.deepcopy(strip) if strip else None

    async def get_by_video(self, video_id: str) -> ThumbnailStrip | None:
        """Get a thumbnail strip by source video ID (most recent)."""
        matching = [s for s in self._strips.values() if s.video_id == video_id]
        if not matching:
            return None
        most_recent = max(matching, key=lambda s: s.created_at)
        return copy.deepcopy(most_recent)

    async def update_status(
        self,
        strip_id: str,
        status: ThumbnailStripStatus,
        *,
        file_path: str | None = None,
        frame_count: int | None = None,
        rows: int | None = None,
    ) -> None:
        """Update the status of a thumbnail strip with transition validation."""
        strip = self._strips.get(strip_id)
        if strip is None:
            raise ValueError(f"Thumbnail strip {strip_id} not found")

        _validate_status_transition(strip.status.value, status.value)

        strip.status = status
        if file_path is not None:
            strip.file_path = file_path
        if frame_count is not None:
            strip.frame_count = frame_count
        if rows is not None:
            strip.rows = rows

    async def delete(self, strip_id: str) -> bool:
        """Delete a thumbnail strip record."""
        if strip_id in self._strips:
            del self._strips[strip_id]
            return True
        return False
