"""Proxy file repository implementations for proxy persistence.

Provides Protocol, SQLite, and InMemory implementations following the
established repository triple pattern used by other domain entities.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

import aiosqlite
import structlog

from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus

logger = structlog.get_logger(__name__)

# Valid status transitions: from -> set of allowed targets
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"generating"},
    "generating": {"ready", "failed"},
    "ready": {"stale"},
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
class AsyncProxyRepository(Protocol):
    """Protocol for async proxy file repository operations.

    Implementations must provide async methods for CRUD operations
    on proxy file records.
    """

    async def add(self, proxy: ProxyFile) -> ProxyFile:
        """Add a new proxy file record.

        Args:
            proxy: The proxy file to add.

        Returns:
            The added proxy file record.

        Raises:
            ValueError: If a proxy with the same (source_video_id, quality) exists.
        """
        ...

    async def get(self, proxy_id: str) -> ProxyFile | None:
        """Get a proxy file by ID.

        Args:
            proxy_id: The proxy file UUID.

        Returns:
            The proxy file if found, None otherwise.
        """
        ...

    async def get_by_video_and_quality(
        self, source_video_id: str, quality: ProxyQuality
    ) -> ProxyFile | None:
        """Get a proxy file by source video ID and quality level.

        Args:
            source_video_id: The source video UUID.
            quality: The quality level.

        Returns:
            The proxy file if found, None otherwise.
        """
        ...

    async def list_by_video(self, source_video_id: str) -> list[ProxyFile]:
        """List all proxy files for a source video.

        Args:
            source_video_id: The source video UUID.

        Returns:
            List of proxy files for the video.
        """
        ...

    async def update_status(
        self,
        proxy_id: str,
        status: ProxyStatus,
        *,
        file_size_bytes: int | None = None,
    ) -> None:
        """Update the status of a proxy file.

        Validates state transitions. When transitioning to 'ready',
        sets generated_at to now. Updates last_accessed_at on every call.

        Args:
            proxy_id: The proxy file UUID.
            status: New status value.
            file_size_bytes: Updated file size (optional, typically set on ready).

        Raises:
            ValueError: If the proxy is not found or transition is invalid.
        """
        ...

    async def delete(self, proxy_id: str) -> bool:
        """Delete a proxy file record.

        Args:
            proxy_id: The proxy file UUID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    async def count(self) -> int:
        """Count all proxy file records.

        Returns:
            Total number of proxy files.
        """
        ...

    async def total_size_bytes(self) -> int:
        """Get the total size of all proxy files in bytes.

        Returns:
            Sum of file_size_bytes across all proxy records.
        """
        ...

    async def count_by_status(self, status: ProxyStatus) -> int:
        """Count proxy file records with a given status.

        Args:
            status: The proxy status to filter by.

        Returns:
            Number of proxy files matching the status.
        """
        ...

    async def get_oldest_accessed(self) -> ProxyFile | None:
        """Get the proxy file with the oldest last_accessed_at timestamp.

        Only considers proxies with status 'ready'.

        Returns:
            The oldest-accessed ready proxy, or None if no ready proxies exist.
        """
        ...


class SQLiteProxyRepository:
    """Async SQLite implementation of the proxy repository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialize the repository with an async database connection.

        Args:
            conn: Async SQLite database connection.
        """
        self._conn = conn
        self._conn.row_factory = aiosqlite.Row

    async def add(self, proxy: ProxyFile) -> ProxyFile:
        """Add a new proxy file record to SQLite."""
        try:
            await self._conn.execute(
                """
                INSERT INTO proxy_files
                    (id, source_video_id, quality, file_path, file_size_bytes,
                     status, source_checksum, generated_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proxy.id,
                    proxy.source_video_id,
                    proxy.quality.value,
                    proxy.file_path,
                    proxy.file_size_bytes,
                    proxy.status.value,
                    proxy.source_checksum,
                    proxy.generated_at.isoformat() if proxy.generated_at else None,
                    proxy.last_accessed_at.isoformat(),
                ),
            )
            await self._conn.commit()
        except aiosqlite.IntegrityError as e:
            raise ValueError(
                f"Proxy already exists for video {proxy.source_video_id} "
                f"at quality {proxy.quality.value}"
            ) from e
        return proxy

    async def get(self, proxy_id: str) -> ProxyFile | None:
        """Get a proxy file by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM proxy_files WHERE id = ?",
            (proxy_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_proxy(row) if row else None

    async def get_by_video_and_quality(
        self, source_video_id: str, quality: ProxyQuality
    ) -> ProxyFile | None:
        """Get a proxy file by source video and quality."""
        cursor = await self._conn.execute(
            "SELECT * FROM proxy_files WHERE source_video_id = ? AND quality = ?",
            (source_video_id, quality.value),
        )
        row = await cursor.fetchone()
        return self._row_to_proxy(row) if row else None

    async def list_by_video(self, source_video_id: str) -> list[ProxyFile]:
        """List all proxy files for a source video."""
        cursor = await self._conn.execute(
            "SELECT * FROM proxy_files WHERE source_video_id = ? ORDER BY quality",
            (source_video_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_proxy(row) for row in rows]

    async def update_status(
        self,
        proxy_id: str,
        status: ProxyStatus,
        *,
        file_size_bytes: int | None = None,
    ) -> None:
        """Update the status of a proxy file with transition validation."""
        current = await self.get(proxy_id)
        if current is None:
            raise ValueError(f"Proxy file {proxy_id} not found")

        _validate_status_transition(current.status.value, status.value)

        now = datetime.now(timezone.utc)
        generated_at = now if status == ProxyStatus.READY else current.generated_at
        size = file_size_bytes if file_size_bytes is not None else current.file_size_bytes

        await self._conn.execute(
            """
            UPDATE proxy_files
            SET status = ?, file_size_bytes = ?, generated_at = ?, last_accessed_at = ?
            WHERE id = ?
            """,
            (
                status.value,
                size,
                generated_at.isoformat() if generated_at else None,
                now.isoformat(),
                proxy_id,
            ),
        )
        await self._conn.commit()

    async def delete(self, proxy_id: str) -> bool:
        """Delete a proxy file record."""
        cursor = await self._conn.execute(
            "DELETE FROM proxy_files WHERE id = ?",
            (proxy_id,),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def count(self) -> int:
        """Count all proxy file records."""
        cursor = await self._conn.execute("SELECT COUNT(*) FROM proxy_files")
        row = await cursor.fetchone()
        assert row is not None
        result: int = row[0]
        return result

    async def total_size_bytes(self) -> int:
        """Get the total size of all proxy files in bytes."""
        cursor = await self._conn.execute(
            "SELECT COALESCE(SUM(file_size_bytes), 0) FROM proxy_files"
        )
        row = await cursor.fetchone()
        assert row is not None
        result: int = row[0]
        return result

    async def count_by_status(self, status: ProxyStatus) -> int:
        """Count proxy file records with a given status."""
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM proxy_files WHERE status = ?",
            (status.value,),
        )
        row = await cursor.fetchone()
        assert row is not None
        result: int = row[0]
        return result

    async def get_oldest_accessed(self) -> ProxyFile | None:
        """Get the oldest-accessed ready proxy file."""
        cursor = await self._conn.execute(
            "SELECT * FROM proxy_files WHERE status = ? ORDER BY last_accessed_at ASC LIMIT 1",
            (ProxyStatus.READY.value,),
        )
        row = await cursor.fetchone()
        return self._row_to_proxy(row) if row else None

    def _row_to_proxy(self, row: aiosqlite.Row) -> ProxyFile:
        """Convert a database row to a ProxyFile.

        Args:
            row: Database row.

        Returns:
            ProxyFile instance.
        """
        return ProxyFile(
            id=row["id"],
            source_video_id=row["source_video_id"],
            quality=ProxyQuality(row["quality"]),
            file_path=row["file_path"],
            file_size_bytes=row["file_size_bytes"],
            status=ProxyStatus(row["status"]),
            source_checksum=row["source_checksum"],
            generated_at=(
                datetime.fromisoformat(row["generated_at"]) if row["generated_at"] else None
            ),
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]),
        )


class InMemoryProxyRepository:
    """In-memory implementation for testing.

    Stores deepcopy-isolated objects so callers cannot mutate internal state.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._proxies: dict[str, ProxyFile] = {}

    async def add(self, proxy: ProxyFile) -> ProxyFile:
        """Add a new proxy file record in memory."""
        # Check unique constraint
        for existing in self._proxies.values():
            if (
                existing.source_video_id == proxy.source_video_id
                and existing.quality == proxy.quality
            ):
                raise ValueError(
                    f"Proxy already exists for video {proxy.source_video_id} "
                    f"at quality {proxy.quality.value}"
                )
        self._proxies[proxy.id] = copy.deepcopy(proxy)
        return copy.deepcopy(proxy)

    async def get(self, proxy_id: str) -> ProxyFile | None:
        """Get a proxy file by ID."""
        proxy = self._proxies.get(proxy_id)
        return copy.deepcopy(proxy) if proxy else None

    async def get_by_video_and_quality(
        self, source_video_id: str, quality: ProxyQuality
    ) -> ProxyFile | None:
        """Get a proxy file by source video and quality."""
        for proxy in self._proxies.values():
            if proxy.source_video_id == source_video_id and proxy.quality == quality:
                return copy.deepcopy(proxy)
        return None

    async def list_by_video(self, source_video_id: str) -> list[ProxyFile]:
        """List all proxy files for a source video."""
        results = [
            copy.deepcopy(p) for p in self._proxies.values() if p.source_video_id == source_video_id
        ]
        return sorted(results, key=lambda p: p.quality.value)

    async def update_status(
        self,
        proxy_id: str,
        status: ProxyStatus,
        *,
        file_size_bytes: int | None = None,
    ) -> None:
        """Update the status of a proxy file with transition validation."""
        proxy = self._proxies.get(proxy_id)
        if proxy is None:
            raise ValueError(f"Proxy file {proxy_id} not found")

        _validate_status_transition(proxy.status.value, status.value)

        now = datetime.now(timezone.utc)
        proxy.status = status
        proxy.last_accessed_at = now
        if status == ProxyStatus.READY:
            proxy.generated_at = now
        if file_size_bytes is not None:
            proxy.file_size_bytes = file_size_bytes

    async def delete(self, proxy_id: str) -> bool:
        """Delete a proxy file record."""
        if proxy_id in self._proxies:
            del self._proxies[proxy_id]
            return True
        return False

    async def count(self) -> int:
        """Count all proxy file records."""
        return len(self._proxies)

    async def total_size_bytes(self) -> int:
        """Get the total size of all proxy files in bytes."""
        return sum(p.file_size_bytes for p in self._proxies.values())

    async def count_by_status(self, status: ProxyStatus) -> int:
        """Count proxy file records with a given status."""
        return sum(1 for p in self._proxies.values() if p.status == status)

    async def get_oldest_accessed(self) -> ProxyFile | None:
        """Get the oldest-accessed ready proxy file."""
        ready = [p for p in self._proxies.values() if p.status == ProxyStatus.READY]
        if not ready:
            return None
        oldest = min(ready, key=lambda p: p.last_accessed_at)
        return copy.deepcopy(oldest)
