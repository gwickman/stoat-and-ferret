"""Preview cache with LRU eviction and TTL expiry.

Manages preview segment storage with configurable size limits, LRU eviction
(oldest-accessed first), TTL-based expiry, and a background cleanup task.
Cache metadata is in-memory only, rebuilt from filesystem on startup.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog

from stoat_ferret.api.settings import get_settings
from stoat_ferret.preview.metrics import (
    preview_cache_bytes,
    preview_cache_evictions_total,
    preview_cache_hit_ratio,
    preview_cache_max_bytes,
)

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    """In-memory metadata for a cached preview session."""

    session_id: str
    size_bytes: int
    last_accessed: datetime
    expires_at: datetime


@dataclass
class CacheStatus:
    """Snapshot of current cache state."""

    used_bytes: int
    max_bytes: int
    usage_percent: float
    active_sessions: list[str] = field(default_factory=list)


class PreviewCache:
    """LRU + TTL cache for preview session storage.

    Tracks session directories with in-memory metadata. Enforces a
    configurable size limit via LRU eviction and removes expired sessions
    via TTL. All state mutations are serialized with an asyncio.Lock.

    Args:
        base_dir: Base directory containing session subdirectories.
        max_bytes: Maximum cache size in bytes. Defaults to settings value.
        session_ttl_seconds: Session TTL in seconds. Defaults to settings value.
        cleanup_interval_seconds: Interval between background cleanup runs.
    """

    def __init__(
        self,
        *,
        base_dir: str | None = None,
        max_bytes: int | None = None,
        session_ttl_seconds: int | None = None,
        cleanup_interval_seconds: float = 60.0,
    ) -> None:
        settings = get_settings()
        self._base_dir = Path(base_dir if base_dir is not None else settings.preview_output_dir)
        self._max_bytes = max_bytes if max_bytes is not None else settings.preview_cache_max_bytes
        self._session_ttl_seconds = (
            session_ttl_seconds
            if session_ttl_seconds is not None
            else settings.preview_session_ttl_seconds
        )
        self._cleanup_interval = cleanup_interval_seconds
        self._lock = asyncio.Lock()
        self._entries: dict[str, CacheEntry] = {}
        self._cleanup_task: asyncio.Task[None] | None = None
        self._hits = 0
        self._misses = 0

        # Set max bytes gauge once at init
        preview_cache_max_bytes.set(self._max_bytes)

    @property
    def used_bytes(self) -> int:
        """Total bytes tracked by the cache."""
        return sum(e.size_bytes for e in self._entries.values())

    @property
    def max_bytes(self) -> int:
        """Maximum cache size in bytes."""
        return self._max_bytes

    async def register(self, session_id: str, expires_at: datetime) -> None:
        """Register a new session in the cache, evicting if needed.

        Calculates the session directory size and adds it to the cache.
        If the cache would exceed max_bytes, LRU eviction removes the
        oldest-accessed sessions until space is available.

        Args:
            session_id: Preview session identifier.
            expires_at: When this session expires.
        """
        session_dir = self._base_dir / session_id
        size = _calculate_dir_size(session_dir)

        async with self._lock:
            # Evict expired sessions first
            await self._evict_expired_unlocked()

            # LRU eviction to make room
            await self._evict_lru_unlocked(size)

            now = datetime.now(timezone.utc)
            self._entries[session_id] = CacheEntry(
                session_id=session_id,
                size_bytes=size,
                last_accessed=now,
                expires_at=expires_at,
            )

        preview_cache_bytes.set(self.used_bytes)

        logger.debug(
            "preview_cache_registered",
            session_id=session_id,
            size_bytes=size,
            cache_used=self.used_bytes,
        )

    async def touch(self, session_id: str) -> None:
        """Update last_accessed timestamp for a session.

        Also refreshes the size from disk and checks for TTL expiry.

        Args:
            session_id: Preview session identifier.
        """
        async with self._lock:
            entry = self._entries.get(session_id)
            if entry is None:
                self._misses += 1
                self._update_hit_ratio()
                return

            self._hits += 1
            self._update_hit_ratio()

            now = datetime.now(timezone.utc)
            if now >= entry.expires_at:
                await self._remove_entry_unlocked(entry, reason="ttl_expired")
                return

            entry.last_accessed = now
            # Refresh size from disk
            session_dir = self._base_dir / session_id
            entry.size_bytes = _calculate_dir_size(session_dir)
            preview_cache_bytes.set(self.used_bytes)

    async def remove(self, session_id: str) -> None:
        """Remove a session from the cache (metadata only, no disk cleanup).

        Args:
            session_id: Preview session identifier.
        """
        async with self._lock:
            self._entries.pop(session_id, None)
            preview_cache_bytes.set(self.used_bytes)

    async def status(self) -> CacheStatus:
        """Get current cache status.

        Returns:
            CacheStatus with used_bytes, max_bytes, usage_percent,
            and list of active session IDs.
        """
        async with self._lock:
            used = sum(e.size_bytes for e in self._entries.values())
            max_b = self._max_bytes
            pct = (used / max_b * 100.0) if max_b > 0 else 0.0
            sessions = list(self._entries.keys())

        return CacheStatus(
            used_bytes=used,
            max_bytes=max_b,
            usage_percent=round(pct, 2),
            active_sessions=sessions,
        )

    async def clear_all(self) -> tuple[int, int]:
        """Remove all cached sessions, freeing disk space.

        Returns:
            Tuple of (cleared_sessions count, freed_bytes).
        """
        async with self._lock:
            cleared = len(self._entries)
            freed = sum(e.size_bytes for e in self._entries.values())

            for entry in list(self._entries.values()):
                session_dir = self._base_dir / entry.session_id
                if session_dir.exists():
                    shutil.rmtree(session_dir, ignore_errors=True)

            self._entries.clear()

        preview_cache_bytes.set(0)

        logger.info(
            "preview_cache_cleared",
            cleared_sessions=cleared,
            freed_bytes=freed,
        )
        return cleared, freed

    async def rebuild_from_disk(self) -> None:
        """Rebuild cache metadata by scanning the base directory.

        Scans for existing session directories and registers them with
        their actual disk sizes. Used on startup to restore cache state.
        """
        if not self._base_dir.exists():
            return

        async with self._lock:
            self._entries.clear()
            now = datetime.now(timezone.utc)
            from datetime import timedelta

            for child in sorted(self._base_dir.iterdir()):
                if child.is_dir():
                    size = _calculate_dir_size(child)
                    self._entries[child.name] = CacheEntry(
                        session_id=child.name,
                        size_bytes=size,
                        last_accessed=now,
                        expires_at=now + timedelta(seconds=self._session_ttl_seconds),
                    )

        preview_cache_bytes.set(self.used_bytes)

        logger.info(
            "preview_cache_rebuilt",
            session_count=len(self._entries),
            total_bytes=self.used_bytes,
        )

    async def start_cleanup_task(self) -> None:
        """Start the background periodic cleanup task."""
        if self._cleanup_task is not None:
            return
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def stop_cleanup_task(self) -> None:
        """Stop the background periodic cleanup task."""
        if self._cleanup_task is None:
            return
        self._cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._cleanup_task
        self._cleanup_task = None

    async def _periodic_cleanup(self) -> None:
        """Run periodic TTL cleanup in the background."""
        while True:
            await asyncio.sleep(self._cleanup_interval)
            async with self._lock:
                await self._evict_expired_unlocked()

    async def _evict_expired_unlocked(self) -> None:
        """Remove all TTL-expired entries. Must be called with lock held."""
        now = datetime.now(timezone.utc)
        expired = [e for e in self._entries.values() if now >= e.expires_at]
        for entry in expired:
            await self._remove_entry_unlocked(entry, reason="ttl_expired")

    async def _evict_lru_unlocked(self, needed_bytes: int) -> None:
        """Evict oldest-accessed sessions until there is room. Must be called with lock held.

        Args:
            needed_bytes: Number of bytes needed for the new session.
        """
        while self._entries and (self.used_bytes + needed_bytes > self._max_bytes):
            # Find the oldest-accessed entry
            oldest = min(self._entries.values(), key=lambda e: e.last_accessed)
            await self._remove_entry_unlocked(oldest, reason="lru_eviction")

    async def _remove_entry_unlocked(self, entry: CacheEntry, *, reason: str) -> None:
        """Remove a cache entry, deleting its directory. Must be called with lock held.

        Args:
            entry: The cache entry to remove.
            reason: Reason for removal (for logging).
        """
        freed = entry.size_bytes
        session_dir = self._base_dir / entry.session_id
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

        self._entries.pop(entry.session_id, None)

        preview_cache_evictions_total.labels(reason=reason).inc()
        preview_cache_bytes.set(self.used_bytes)

        cache_used_after = self.used_bytes
        logger.info(
            "preview_cache_eviction",
            evicted_session_id=entry.session_id,
            reason=reason,
            freed_bytes=freed,
            cache_usage_after=cache_used_after,
        )

    def _update_hit_ratio(self) -> None:
        """Recalculate and set the cache hit ratio gauge."""
        total = self._hits + self._misses
        ratio = self._hits / total if total > 0 else 0.0
        preview_cache_hit_ratio.set(ratio)


def _calculate_dir_size(path: Path) -> int:
    """Calculate the total size of a directory recursively.

    Args:
        path: Directory path to calculate size for.

    Returns:
        Total size in bytes. Returns 0 if directory doesn't exist.
    """
    if not path.exists():
        return 0
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total
