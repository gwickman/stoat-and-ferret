"""Encoder cache repository implementations.

Provides Protocol, SQLite, and InMemory implementations following the
established repository triple pattern. Caches FFmpeg encoder detection
results in SQLite so re-detection is only needed on explicit refresh.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

import aiosqlite
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EncoderCacheEntry:
    """A cached encoder detection result.

    Attributes:
        id: Database row ID (None before persistence).
        name: Encoder name as reported by FFmpeg (e.g., "h264_nvenc").
        codec: Codec identifier (e.g., "h264", "hevc").
        is_hardware: Whether this is a hardware-accelerated encoder.
        encoder_type: Type string (e.g., "Software", "Nvenc", "Qsv").
        description: Encoder description from FFmpeg output.
        detected_at: When the encoder was detected.
    """

    id: int | None
    name: str
    codec: str
    is_hardware: bool
    encoder_type: str
    description: str
    detected_at: datetime


@runtime_checkable
class AsyncEncoderCacheRepository(Protocol):
    """Protocol for async encoder cache repository operations.

    Implementations provide methods to query, populate, and refresh
    the encoder detection cache.
    """

    async def get_all(self) -> list[EncoderCacheEntry]:
        """Get all cached encoder entries.

        Returns:
            List of cached encoder entries, empty if cache is unpopulated.
        """
        ...

    async def create_many(self, entries: list[EncoderCacheEntry]) -> list[EncoderCacheEntry]:
        """Insert multiple encoder cache entries.

        Args:
            entries: Encoder entries to persist.

        Returns:
            The persisted entries (with IDs assigned).
        """
        ...

    async def clear(self) -> None:
        """Remove all cached encoder entries (truncate)."""
        ...


class AsyncSQLiteEncoderCacheRepository:
    """Async SQLite implementation of the encoder cache repository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def get_all(self) -> list[EncoderCacheEntry]:
        """Get all cached encoder entries from SQLite."""
        cursor = await self._conn.execute(
            "SELECT id, name, codec, is_hardware, encoder_type, description, detected_at "
            "FROM encoder_cache ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    async def create_many(self, entries: list[EncoderCacheEntry]) -> list[EncoderCacheEntry]:
        """Insert multiple encoder cache entries into SQLite."""
        result: list[EncoderCacheEntry] = []
        for entry in entries:
            cursor = await self._conn.execute(
                "INSERT INTO encoder_cache (name, codec, is_hardware, encoder_type, "
                "description, detected_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    entry.name,
                    entry.codec,
                    1 if entry.is_hardware else 0,
                    entry.encoder_type,
                    entry.description,
                    entry.detected_at.isoformat(),
                ),
            )
            result.append(
                EncoderCacheEntry(
                    id=cursor.lastrowid,
                    name=entry.name,
                    codec=entry.codec,
                    is_hardware=entry.is_hardware,
                    encoder_type=entry.encoder_type,
                    description=entry.description,
                    detected_at=entry.detected_at,
                )
            )
        await self._conn.commit()
        return result

    async def clear(self) -> None:
        """Remove all cached encoder entries from SQLite."""
        await self._conn.execute("DELETE FROM encoder_cache")
        await self._conn.commit()

    def _row_to_entry(self, row: aiosqlite.Row) -> EncoderCacheEntry:
        """Convert a database row to an EncoderCacheEntry.

        Args:
            row: Database row.

        Returns:
            EncoderCacheEntry instance.
        """
        return EncoderCacheEntry(
            id=row["id"],
            name=row["name"],
            codec=row["codec"],
            is_hardware=bool(row["is_hardware"]),
            encoder_type=row["encoder_type"],
            description=row["description"],
            detected_at=datetime.fromisoformat(row["detected_at"]),
        )


class InMemoryEncoderCacheRepository:
    """In-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._entries: list[EncoderCacheEntry] = []
        self._next_id = 1

    async def get_all(self) -> list[EncoderCacheEntry]:
        """Get all cached encoder entries from memory."""
        return [copy.deepcopy(e) for e in sorted(self._entries, key=lambda e: e.name)]

    async def create_many(self, entries: list[EncoderCacheEntry]) -> list[EncoderCacheEntry]:
        """Insert multiple encoder cache entries into memory."""
        result: list[EncoderCacheEntry] = []
        for entry in entries:
            stored = EncoderCacheEntry(
                id=self._next_id,
                name=entry.name,
                codec=entry.codec,
                is_hardware=entry.is_hardware,
                encoder_type=entry.encoder_type,
                description=entry.description,
                detected_at=entry.detected_at,
            )
            self._next_id += 1
            self._entries.append(stored)
            result.append(copy.deepcopy(stored))
        return result

    async def clear(self) -> None:
        """Remove all cached encoder entries from memory."""
        self._entries.clear()
