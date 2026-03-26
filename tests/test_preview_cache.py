"""Tests for PreviewCache LRU eviction, TTL expiry, and size tracking.

Covers cache registration, LRU ordering, TTL cleanup, status reporting,
background cleanup task, directory size calculation, and structured logging.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from stoat_ferret.preview.cache import (
    PreviewCache,
    _calculate_dir_size,
)


def _create_session_dir(base: Path, session_id: str, size_bytes: int) -> Path:
    """Create a mock session directory with a file of the given size.

    Args:
        base: Base preview directory.
        session_id: Session identifier (subdirectory name).
        size_bytes: Size of the dummy file to create.

    Returns:
        Path to the created session directory.
    """
    session_dir = base / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    dummy = session_dir / "segment_000.ts"
    dummy.write_bytes(b"\x00" * size_bytes)
    return session_dir


def _make_cache(
    tmp_path: Path,
    *,
    max_bytes: int = 1000,
    session_ttl_seconds: int = 3600,
    cleanup_interval_seconds: float = 60.0,
) -> PreviewCache:
    """Create a PreviewCache with test defaults."""
    return PreviewCache(
        base_dir=str(tmp_path),
        max_bytes=max_bytes,
        session_ttl_seconds=session_ttl_seconds,
        cleanup_interval_seconds=cleanup_interval_seconds,
    )


# --- Directory size calculation ---


class TestCalculateDirSize:
    """Tests for _calculate_dir_size."""

    def test_nonexistent_dir_returns_zero(self, tmp_path: Path) -> None:
        assert _calculate_dir_size(tmp_path / "nonexistent") == 0

    def test_empty_dir_returns_zero(self, tmp_path: Path) -> None:
        d = tmp_path / "empty"
        d.mkdir()
        assert _calculate_dir_size(d) == 0

    def test_single_file(self, tmp_path: Path) -> None:
        d = tmp_path / "session"
        d.mkdir()
        (d / "file.ts").write_bytes(b"x" * 100)
        assert _calculate_dir_size(d) == 100

    def test_nested_files(self, tmp_path: Path) -> None:
        d = tmp_path / "session"
        d.mkdir()
        (d / "a.ts").write_bytes(b"x" * 50)
        sub = d / "sub"
        sub.mkdir()
        (sub / "b.ts").write_bytes(b"x" * 30)
        assert _calculate_dir_size(d) == 80


# --- Cache registration and status ---


class TestCacheRegistration:
    """Tests for adding sessions and querying status."""

    async def test_register_tracks_session(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000)
        _create_session_dir(tmp_path, "s1", 100)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        await cache.register("s1", expires)

        status = await cache.status()
        assert status.used_bytes == 100
        assert "s1" in status.active_sessions

    async def test_status_returns_correct_metrics(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=1000)
        _create_session_dir(tmp_path, "s1", 200)
        _create_session_dir(tmp_path, "s2", 300)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        await cache.register("s1", expires)
        await cache.register("s2", expires)

        status = await cache.status()
        assert status.used_bytes == 500
        assert status.max_bytes == 1000
        assert status.usage_percent == 50.0
        assert len(status.active_sessions) == 2

    async def test_empty_cache_status(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path)
        status = await cache.status()
        assert status.used_bytes == 0
        assert status.usage_percent == 0.0
        assert status.active_sessions == []

    async def test_remove_session(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000)
        _create_session_dir(tmp_path, "s1", 100)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await cache.register("s1", expires)

        await cache.remove("s1")

        status = await cache.status()
        assert status.used_bytes == 0
        assert "s1" not in status.active_sessions

    async def test_remove_nonexistent_session_is_noop(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path)
        await cache.remove("nonexistent")  # Should not raise


# --- LRU eviction ---


class TestLRUEviction:
    """Tests for LRU eviction behavior."""

    async def test_evicts_oldest_accessed_first(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=500)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        _create_session_dir(tmp_path, "old", 200)
        await cache.register("old", expires)
        # Touch 'old' to set its timestamp, then register 'new' after a brief moment
        _create_session_dir(tmp_path, "mid", 200)
        await cache.register("mid", expires)

        # Touch 'mid' to make it more recently accessed than 'old'
        await cache.touch("mid")

        # Adding 'new' (200 bytes) would exceed 500 limit (200+200+200=600)
        # Should evict 'old' (oldest accessed)
        _create_session_dir(tmp_path, "new", 200)
        await cache.register("new", expires)

        status = await cache.status()
        assert "old" not in status.active_sessions
        assert "mid" in status.active_sessions
        assert "new" in status.active_sessions

    async def test_multiple_evictions_to_make_room(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=500)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        _create_session_dir(tmp_path, "s1", 200)
        await cache.register("s1", expires)
        _create_session_dir(tmp_path, "s2", 200)
        await cache.register("s2", expires)

        # Adding 'big' (400 bytes) needs to evict both s1 and s2 (200+200=400)
        _create_session_dir(tmp_path, "big", 400)
        await cache.register("big", expires)

        status = await cache.status()
        assert "s1" not in status.active_sessions
        assert "s2" not in status.active_sessions
        assert "big" in status.active_sessions
        assert status.used_bytes == 400

    async def test_eviction_deletes_session_directory(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=300)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        _create_session_dir(tmp_path, "victim", 200)
        await cache.register("victim", expires)

        # Adding 'new' triggers eviction of 'victim'
        _create_session_dir(tmp_path, "new", 200)
        await cache.register("new", expires)

        assert not (tmp_path / "victim").exists()

    async def test_single_session_exceeds_max_still_stored(self, tmp_path: Path) -> None:
        """A session larger than max_bytes is stored (no existing entries to evict)."""
        cache = _make_cache(tmp_path, max_bytes=100)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        _create_session_dir(tmp_path, "huge", 500)
        await cache.register("huge", expires)

        status = await cache.status()
        assert "huge" in status.active_sessions
        assert status.used_bytes == 500


# --- TTL expiry ---


class TestTTLExpiry:
    """Tests for TTL-based session expiry."""

    async def test_expired_session_removed_on_register(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000)

        # Register with already-expired TTL
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        _create_session_dir(tmp_path, "expired", 100)
        await cache.register("expired", expired_at)

        # Register new session triggers expired cleanup
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        _create_session_dir(tmp_path, "fresh", 100)
        await cache.register("fresh", future)

        status = await cache.status()
        assert "expired" not in status.active_sessions
        assert "fresh" in status.active_sessions

    async def test_expired_session_removed_on_touch(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000)

        # Register with short TTL, then manually set expires_at to past
        _create_session_dir(tmp_path, "s1", 100)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await cache.register("s1", expires)

        # Force expiry
        cache._entries["s1"].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

        await cache.touch("s1")

        status = await cache.status()
        assert "s1" not in status.active_sessions

    async def test_touch_updates_last_accessed(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000)
        _create_session_dir(tmp_path, "s1", 100)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await cache.register("s1", expires)

        before = cache._entries["s1"].last_accessed
        await asyncio.sleep(0.01)
        await cache.touch("s1")
        after = cache._entries["s1"].last_accessed

        assert after > before

    async def test_touch_nonexistent_is_noop(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path)
        await cache.touch("nonexistent")  # Should not raise


# --- Structured logging ---


class TestEvictionLogging:
    """Tests for structured log events during eviction."""

    async def test_lru_eviction_logs_all_fields(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        cache = _make_cache(tmp_path, max_bytes=300)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        _create_session_dir(tmp_path, "victim", 200)
        await cache.register("victim", expires)

        with patch("stoat_ferret.preview.cache.logger") as mock_logger:
            _create_session_dir(tmp_path, "trigger", 200)
            await cache.register("trigger", expires)

            # Find the eviction log call
            eviction_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call.args and call.args[0] == "preview_cache_eviction"
            ]
            assert len(eviction_calls) >= 1
            kwargs = eviction_calls[0].kwargs
            assert kwargs["evicted_session_id"] == "victim"
            assert kwargs["reason"] == "lru_eviction"
            assert kwargs["freed_bytes"] == 200
            assert "cache_usage_after" in kwargs

    async def test_ttl_eviction_logs_reason(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000)
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        _create_session_dir(tmp_path, "expired", 100)
        await cache.register("expired", expired_at)

        with patch("stoat_ferret.preview.cache.logger") as mock_logger:
            future = datetime.now(timezone.utc) + timedelta(hours=1)
            _create_session_dir(tmp_path, "new", 100)
            await cache.register("new", future)

            eviction_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call.args and call.args[0] == "preview_cache_eviction"
            ]
            assert len(eviction_calls) >= 1
            kwargs = eviction_calls[0].kwargs
            assert kwargs["reason"] == "ttl_expired"


# --- Background cleanup ---


class TestBackgroundCleanup:
    """Tests for periodic background cleanup task."""

    async def test_cleanup_task_starts_and_stops(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, cleanup_interval_seconds=0.05)
        await cache.start_cleanup_task()
        assert cache._cleanup_task is not None
        assert not cache._cleanup_task.done()

        await cache.stop_cleanup_task()
        assert cache._cleanup_task is None

    async def test_cleanup_removes_expired_sessions(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000, cleanup_interval_seconds=0.05)

        _create_session_dir(tmp_path, "will_expire", 100)
        expires = datetime.now(timezone.utc) + timedelta(seconds=0.1)
        await cache.register("will_expire", expires)

        await cache.start_cleanup_task()
        # Wait for expiry + cleanup interval
        await asyncio.sleep(0.3)

        status = await cache.status()
        assert "will_expire" not in status.active_sessions

        await cache.stop_cleanup_task()

    async def test_start_cleanup_task_idempotent(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, cleanup_interval_seconds=0.1)
        await cache.start_cleanup_task()
        first_task = cache._cleanup_task

        await cache.start_cleanup_task()
        assert cache._cleanup_task is first_task  # Same task, not replaced

        await cache.stop_cleanup_task()


# --- Rebuild from disk ---


class TestRebuildFromDisk:
    """Tests for cache metadata rebuild from filesystem."""

    async def test_rebuild_discovers_existing_sessions(self, tmp_path: Path) -> None:
        _create_session_dir(tmp_path, "existing1", 100)
        _create_session_dir(tmp_path, "existing2", 200)

        cache = _make_cache(tmp_path, max_bytes=10000)
        await cache.rebuild_from_disk()

        status = await cache.status()
        assert status.used_bytes == 300
        assert len(status.active_sessions) == 2

    async def test_rebuild_on_empty_dir(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=10000)
        await cache.rebuild_from_disk()

        status = await cache.status()
        assert status.used_bytes == 0
        assert status.active_sessions == []

    async def test_rebuild_on_nonexistent_dir(self, tmp_path: Path) -> None:
        cache = PreviewCache(
            base_dir=str(tmp_path / "nonexistent"),
            max_bytes=10000,
            session_ttl_seconds=3600,
        )
        await cache.rebuild_from_disk()  # Should not raise

        status = await cache.status()
        assert status.used_bytes == 0


# --- Concurrency ---


class TestConcurrency:
    """Tests for concurrent access safety."""

    async def test_concurrent_register_and_status(self, tmp_path: Path) -> None:
        cache = _make_cache(tmp_path, max_bytes=100000)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        async def register_session(i: int) -> None:
            _create_session_dir(tmp_path, f"s{i}", 100)
            await cache.register(f"s{i}", expires)

        await asyncio.gather(*[register_session(i) for i in range(10)])

        status = await cache.status()
        assert status.used_bytes == 1000
        assert len(status.active_sessions) == 10

    async def test_concurrent_eviction_and_touch(self, tmp_path: Path) -> None:
        """Concurrent touch and eviction operations don't corrupt state."""
        cache = _make_cache(tmp_path, max_bytes=500)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        for i in range(3):
            _create_session_dir(tmp_path, f"s{i}", 100)
            await cache.register(f"s{i}", expires)

        async def touch_loop() -> None:
            for i in range(3):
                await cache.touch(f"s{i}")

        async def add_session() -> None:
            _create_session_dir(tmp_path, "new", 400)
            await cache.register("new", expires)

        await asyncio.gather(touch_loop(), add_session())

        status = await cache.status()
        # State should be consistent - total sessions should not be corrupted
        assert status.used_bytes == sum(e.size_bytes for e in cache._entries.values())
