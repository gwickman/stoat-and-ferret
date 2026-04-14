"""Waveform repository implementations for waveform persistence.

Provides Protocol, SQLite, and InMemory implementations following the
established repository triple pattern used by other domain entities.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Protocol, runtime_checkable

import aiosqlite
import structlog

from stoat_ferret.db.models import Waveform, WaveformFormat, WaveformStatus

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
class AsyncWaveformRepository(Protocol):
    """Protocol for async waveform repository operations.

    Implementations must provide async methods for CRUD operations
    on waveform records.
    """

    async def add(self, waveform: Waveform) -> Waveform:
        """Add a new waveform record.

        Args:
            waveform: The waveform to add.

        Returns:
            The added waveform record.

        Raises:
            ValueError: If a waveform with the same ID already exists.
        """
        ...

    async def get(self, waveform_id: str) -> Waveform | None:
        """Get a waveform by ID.

        Args:
            waveform_id: The waveform UUID.

        Returns:
            The waveform if found, None otherwise.
        """
        ...

    async def get_by_video_and_format(self, video_id: str, fmt: WaveformFormat) -> Waveform | None:
        """Get a waveform by video ID and format.

        Args:
            video_id: The source video UUID.
            fmt: The waveform format (png or json).

        Returns:
            The waveform if found, None otherwise.
        """
        ...

    async def update_status(
        self,
        waveform_id: str,
        status: WaveformStatus,
        *,
        file_path: str | None = None,
    ) -> None:
        """Update the status of a waveform.

        Validates state transitions.

        Args:
            waveform_id: The waveform UUID.
            status: New status value.
            file_path: Updated file path (optional, typically set on ready).

        Raises:
            ValueError: If the waveform is not found or transition is invalid.
        """
        ...

    async def delete(self, waveform_id: str) -> bool:
        """Delete a waveform record.

        Args:
            waveform_id: The waveform UUID.

        Returns:
            True if deleted, False if not found.
        """
        ...


class SQLiteWaveformRepository:
    """Async SQLite implementation of the waveform repository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, waveform: Waveform) -> Waveform:
        """Add a new waveform record to SQLite."""
        try:
            await self._conn.execute(
                """
                INSERT INTO waveforms
                    (id, video_id, format, status, file_path, duration, channels, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    waveform.id,
                    waveform.video_id,
                    waveform.format.value,
                    waveform.status.value,
                    waveform.file_path,
                    waveform.duration,
                    waveform.channels,
                    waveform.created_at.isoformat(),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(f"Waveform already exists with id {waveform.id}") from e
        return waveform

    async def get(self, waveform_id: str) -> Waveform | None:
        """Get a waveform by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM waveforms WHERE id = ?",
            (waveform_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_waveform(row) if row else None

    async def get_by_video_and_format(self, video_id: str, fmt: WaveformFormat) -> Waveform | None:
        """Get a waveform by video ID and format."""
        cursor = await self._conn.execute(
            "SELECT * FROM waveforms WHERE video_id = ? AND format = ?"
            " ORDER BY created_at DESC LIMIT 1",
            (video_id, fmt.value),
        )
        row = await cursor.fetchone()
        return self._row_to_waveform(row) if row else None

    async def update_status(
        self,
        waveform_id: str,
        status: WaveformStatus,
        *,
        file_path: str | None = None,
    ) -> None:
        """Update the status of a waveform with transition validation."""
        current = await self.get(waveform_id)
        if current is None:
            raise ValueError(f"Waveform {waveform_id} not found")

        _validate_status_transition(current.status.value, status.value)

        new_file_path = file_path if file_path is not None else current.file_path

        await self._conn.execute(
            """
            UPDATE waveforms
            SET status = ?, file_path = ?
            WHERE id = ?
            """,
            (
                status.value,
                new_file_path,
                waveform_id,
            ),
        )
        await self._conn.commit()

    async def delete(self, waveform_id: str) -> bool:
        """Delete a waveform record."""
        cursor = await self._conn.execute(
            "DELETE FROM waveforms WHERE id = ?",
            (waveform_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_waveform(self, row: aiosqlite.Row) -> Waveform:
        """Convert a database row to a Waveform.

        Args:
            row: Database row.

        Returns:
            Waveform instance.
        """
        return Waveform(
            id=row["id"],
            video_id=row["video_id"],
            format=WaveformFormat(row["format"]),
            status=WaveformStatus(row["status"]),
            file_path=row["file_path"],
            duration=row["duration"],
            channels=row["channels"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


class InMemoryWaveformRepository:
    """In-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._waveforms: dict[str, Waveform] = {}

    async def add(self, waveform: Waveform) -> Waveform:
        """Add a new waveform record in memory."""
        if waveform.id in self._waveforms:
            raise ValueError(f"Waveform already exists with id {waveform.id}")
        self._waveforms[waveform.id] = copy.deepcopy(waveform)
        return copy.deepcopy(waveform)

    async def get(self, waveform_id: str) -> Waveform | None:
        """Get a waveform by ID."""
        waveform = self._waveforms.get(waveform_id)
        return copy.deepcopy(waveform) if waveform else None

    async def get_by_video_and_format(self, video_id: str, fmt: WaveformFormat) -> Waveform | None:
        """Get a waveform by video ID and format (most recent)."""
        matching = [
            w for w in self._waveforms.values() if w.video_id == video_id and w.format == fmt
        ]
        if not matching:
            return None
        most_recent = max(matching, key=lambda w: w.created_at)
        return copy.deepcopy(most_recent)

    async def update_status(
        self,
        waveform_id: str,
        status: WaveformStatus,
        *,
        file_path: str | None = None,
    ) -> None:
        """Update the status of a waveform with transition validation."""
        waveform = self._waveforms.get(waveform_id)
        if waveform is None:
            raise ValueError(f"Waveform {waveform_id} not found")

        _validate_status_transition(waveform.status.value, status.value)

        waveform.status = status
        if file_path is not None:
            waveform.file_path = file_path

    async def delete(self, waveform_id: str) -> bool:
        """Delete a waveform record."""
        if waveform_id in self._waveforms:
            del self._waveforms[waveform_id]
            return True
        return False
