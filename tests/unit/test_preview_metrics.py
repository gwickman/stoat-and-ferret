"""Tests for preview, proxy, and cache Prometheus metrics.

Verifies metric definitions (names, labels, buckets) and that service
instrumentation correctly updates counters, gauges, and histograms.
Uses the before/after delta pattern for Prometheus metrics.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from stoat_ferret.preview.metrics import (
    preview_cache_bytes,
    preview_cache_evictions_total,
    preview_cache_hit_ratio,
    preview_cache_max_bytes,
    preview_errors_total,
    preview_generation_seconds,
    preview_seek_latency_seconds,
    preview_segment_seconds,
    preview_sessions_active,
    preview_sessions_total,
    proxy_evictions_total,
    proxy_files_total,
    proxy_generation_seconds,
    proxy_storage_bytes,
)


def _sample(name: str, labels: dict[str, str] | None = None) -> float:
    """Get current value of a Prometheus metric from the default registry."""
    val = REGISTRY.get_sample_value(name, labels or {})
    return val if val is not None else 0.0


# ---------------------------------------------------------------------------
# Stage 1: Metric definition tests
# ---------------------------------------------------------------------------


class TestPreviewMetricDefinitions:
    """Verify metric names, types, and histogram buckets match design spec."""

    def test_sessions_total_is_counter_with_quality_label(self) -> None:
        """preview_sessions_total accepts quality label."""
        before = _sample("video_editor_preview_sessions_total", {"quality": "test_def"})
        preview_sessions_total.labels(quality="test_def").inc()
        after = _sample("video_editor_preview_sessions_total", {"quality": "test_def"})
        assert after == before + 1

    def test_sessions_active_is_gauge(self) -> None:
        """preview_sessions_active can inc/dec."""
        before = _sample("video_editor_preview_sessions_active")
        preview_sessions_active.inc()
        after = _sample("video_editor_preview_sessions_active")
        assert after == before + 1
        preview_sessions_active.dec()  # restore

    def test_generation_seconds_buckets(self) -> None:
        """preview_generation_seconds has correct bucket boundaries."""
        expected = [1, 2, 5, 10, 20, 30, 60, 120]
        # _upper_bounds includes +Inf
        bounds = list(preview_generation_seconds._kwargs.get("buckets", []))
        assert bounds == expected

    def test_segment_seconds_buckets(self) -> None:
        """preview_segment_seconds has correct bucket boundaries."""
        expected = [0.1, 0.5, 1, 2, 5, 10]
        bounds = list(preview_segment_seconds._kwargs.get("buckets", []))
        assert bounds == expected

    def test_seek_latency_buckets(self) -> None:
        """preview_seek_latency_seconds has correct bucket boundaries."""
        expected = [0.1, 0.5, 1, 2, 5]
        bounds = list(preview_seek_latency_seconds._kwargs.get("buckets", []))
        assert bounds == expected

    def test_errors_total_accepts_error_type_label(self) -> None:
        """preview_errors_total accepts error_type label."""
        before = _sample("video_editor_preview_errors_total", {"error_type": "test_error"})
        preview_errors_total.labels(error_type="test_error").inc()
        after = _sample("video_editor_preview_errors_total", {"error_type": "test_error"})
        assert after == before + 1


class TestProxyMetricDefinitions:
    """Verify proxy metric names, types, and histogram buckets."""

    def test_proxy_generation_seconds_buckets(self) -> None:
        """proxy_generation_seconds has correct bucket boundaries."""
        expected = [5, 10, 30, 60, 120, 300]
        bounds = list(proxy_generation_seconds._kwargs.get("buckets", []))
        assert bounds == expected

    def test_proxy_files_total_accepts_status_label(self) -> None:
        """proxy_files_total accepts status label."""
        before = _sample("video_editor_proxy_files_total", {"status": "test_status"})
        proxy_files_total.labels(status="test_status").inc()
        after = _sample("video_editor_proxy_files_total", {"status": "test_status"})
        assert after == before + 1
        proxy_files_total.labels(status="test_status").dec()  # restore

    def test_proxy_storage_bytes_is_gauge(self) -> None:
        """proxy_storage_bytes can be set."""
        proxy_storage_bytes.set(12345)
        val = _sample("video_editor_proxy_storage_bytes")
        assert val == 12345
        proxy_storage_bytes.set(0)  # restore

    def test_proxy_evictions_total_accepts_reason_label(self) -> None:
        """proxy_evictions_total accepts reason label."""
        before = _sample("video_editor_proxy_evictions_total", {"reason": "test_reason"})
        proxy_evictions_total.labels(reason="test_reason").inc()
        after = _sample("video_editor_proxy_evictions_total", {"reason": "test_reason"})
        assert after == before + 1


class TestCacheMetricDefinitions:
    """Verify cache metric names and types."""

    def test_cache_bytes_is_gauge(self) -> None:
        """preview_cache_bytes can be set."""
        preview_cache_bytes.set(99999)
        val = _sample("video_editor_preview_cache_bytes")
        assert val == 99999
        preview_cache_bytes.set(0)

    def test_cache_max_bytes_is_gauge(self) -> None:
        """preview_cache_max_bytes can be set."""
        preview_cache_max_bytes.set(500000)
        val = _sample("video_editor_preview_cache_max_bytes")
        assert val == 500000

    def test_cache_evictions_total_accepts_reason_label(self) -> None:
        """preview_cache_evictions_total accepts reason label."""
        before = _sample(
            "video_editor_preview_cache_evictions_total",
            {"reason": "test_reason"},
        )
        preview_cache_evictions_total.labels(reason="test_reason").inc()
        after = _sample(
            "video_editor_preview_cache_evictions_total",
            {"reason": "test_reason"},
        )
        assert after == before + 1

    def test_cache_hit_ratio_is_gauge(self) -> None:
        """preview_cache_hit_ratio can be set."""
        preview_cache_hit_ratio.set(0.75)
        val = _sample("video_editor_preview_cache_hit_ratio")
        assert val == 0.75
        preview_cache_hit_ratio.set(0)


# ---------------------------------------------------------------------------
# Stage 2: Service instrumentation tests
# ---------------------------------------------------------------------------


class TestPreviewManagerMetrics:
    """Verify PreviewManager instruments metrics on session lifecycle."""

    @pytest.fixture()
    def _mock_settings(self) -> None:
        """Patch settings for manager tests."""
        mock_settings = MagicMock()
        mock_settings.preview_cache_max_sessions = 10
        mock_settings.preview_session_ttl_seconds = 300
        mock_settings.preview_output_dir = "/tmp/preview_test"
        mock_settings.preview_segment_duration = 2.0
        with patch("stoat_ferret.preview.manager.get_settings", return_value=mock_settings):
            yield

    @pytest.mark.usefixtures("_mock_settings")
    async def test_start_increments_sessions_total_and_active(self) -> None:
        """start() increments sessions_total and sessions_active."""
        from stoat_ferret.db.models import PreviewQuality
        from stoat_ferret.preview.manager import PreviewManager

        repo = AsyncMock()
        repo.count = AsyncMock(return_value=0)
        repo.add = AsyncMock()
        repo.update = AsyncMock()

        generator = AsyncMock()
        ws_manager = AsyncMock()

        manager = PreviewManager(
            repository=repo,
            generator=generator,
            ws_manager=ws_manager,
        )

        before_total = _sample("video_editor_preview_sessions_total", {"quality": "medium"})
        before_active = _sample("video_editor_preview_sessions_active")

        session = await manager.start(
            project_id="proj-1",
            input_path="/input.mp4",
            quality_level=PreviewQuality.MEDIUM,
        )

        after_total = _sample("video_editor_preview_sessions_total", {"quality": "medium"})
        after_active = _sample("video_editor_preview_sessions_active")

        assert after_total == before_total + 1
        assert after_active == before_active + 1

        # Cleanup: cancel the task and dec active
        task = manager._generation_tasks.get(session.id)
        if task:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        preview_sessions_active.dec()  # restore gauge

    @pytest.mark.usefixtures("_mock_settings")
    async def test_cleanup_decrements_sessions_active(self) -> None:
        """_cleanup_session() decrements sessions_active."""
        from stoat_ferret.db.models import PreviewStatus
        from stoat_ferret.preview.manager import PreviewManager

        repo = AsyncMock()
        repo.update = AsyncMock()
        generator = AsyncMock()
        ws_manager = AsyncMock()

        manager = PreviewManager(
            repository=repo,
            generator=generator,
            ws_manager=ws_manager,
        )

        preview_sessions_active.inc()  # simulate active session
        before = _sample("video_editor_preview_sessions_active")

        session = MagicMock()
        session.id = "test-session-cleanup"
        session.status = PreviewStatus.READY

        with patch.object(Path, "exists", return_value=False):
            await manager._cleanup_session(session)

        after = _sample("video_editor_preview_sessions_active")
        assert after == before - 1

    @pytest.mark.usefixtures("_mock_settings")
    async def test_generation_error_increments_errors_total(self) -> None:
        """_run_generation() increments errors_total on failure."""
        from stoat_ferret.db.models import PreviewQuality, PreviewStatus
        from stoat_ferret.preview.manager import PreviewManager

        repo = AsyncMock()
        session_mock = MagicMock()
        session_mock.id = "err-session"
        session_mock.quality_level = PreviewQuality.HIGH
        session_mock.status = PreviewStatus.GENERATING
        repo.get = AsyncMock(return_value=session_mock)
        repo.update = AsyncMock()

        generator = AsyncMock()
        generator.generate = AsyncMock(side_effect=RuntimeError("ffmpeg boom"))
        ws_manager = AsyncMock()

        manager = PreviewManager(
            repository=repo,
            generator=generator,
            ws_manager=ws_manager,
        )

        cancel_event = asyncio.Event()
        before = _sample("video_editor_preview_errors_total", {"error_type": "ffmpeg_error"})

        await manager._run_generation(
            session_id="err-session",
            input_path="/input.mp4",
            filter_graph=None,
            duration_us=None,
            cancel_event=cancel_event,
        )

        after = _sample("video_editor_preview_errors_total", {"error_type": "ffmpeg_error"})
        assert after == before + 1

    @pytest.mark.usefixtures("_mock_settings")
    async def test_generation_success_observes_duration(self) -> None:
        """_run_generation() observes generation duration on success."""
        from stoat_ferret.db.models import PreviewQuality, PreviewStatus
        from stoat_ferret.preview.manager import PreviewManager

        repo = AsyncMock()
        session_mock = MagicMock()
        session_mock.id = "gen-session"
        session_mock.quality_level = PreviewQuality.LOW
        session_mock.status = PreviewStatus.GENERATING
        repo.get = AsyncMock(return_value=session_mock)
        repo.update = AsyncMock()

        generator = AsyncMock()
        generator.generate = AsyncMock(return_value=Path("/tmp/out"))
        ws_manager = AsyncMock()

        manager = PreviewManager(
            repository=repo,
            generator=generator,
            ws_manager=ws_manager,
        )

        cancel_event = asyncio.Event()
        before_count = _sample("video_editor_preview_generation_seconds_count", {"quality": "low"})

        await manager._run_generation(
            session_id="gen-session",
            input_path="/input.mp4",
            filter_graph=None,
            duration_us=None,
            cancel_event=cancel_event,
        )

        after_count = _sample("video_editor_preview_generation_seconds_count", {"quality": "low"})
        assert after_count == before_count + 1

    @pytest.mark.usefixtures("_mock_settings")
    async def test_seek_generation_observes_latency(self) -> None:
        """_run_seek_generation() observes seek latency on success."""
        from stoat_ferret.db.models import PreviewQuality, PreviewStatus
        from stoat_ferret.preview.manager import PreviewManager

        repo = AsyncMock()
        session_mock = MagicMock()
        session_mock.id = "seek-session"
        session_mock.quality_level = PreviewQuality.MEDIUM
        session_mock.status = PreviewStatus.SEEKING
        repo.get = AsyncMock(return_value=session_mock)
        repo.update = AsyncMock()

        generator = AsyncMock()
        generator.generate = AsyncMock(return_value=Path("/tmp/out"))
        ws_manager = AsyncMock()

        manager = PreviewManager(
            repository=repo,
            generator=generator,
            ws_manager=ws_manager,
        )

        cancel_event = asyncio.Event()
        before_count = _sample("video_editor_preview_seek_latency_seconds_count")

        await manager._run_seek_generation(
            session_id="seek-session",
            input_path="/input.mp4",
            filter_graph=None,
            duration_us=None,
            cancel_event=cancel_event,
        )

        after_count = _sample("video_editor_preview_seek_latency_seconds_count")
        assert after_count == before_count + 1


class TestCacheMetricsInstrumentation:
    """Verify PreviewCache instruments cache metrics."""

    @pytest.fixture()
    def _mock_settings(self, tmp_path: Path) -> None:
        """Patch settings for cache tests."""
        mock_settings = MagicMock()
        mock_settings.preview_output_dir = str(tmp_path)
        mock_settings.preview_cache_max_bytes = 1_000_000
        mock_settings.preview_session_ttl_seconds = 300
        with patch("stoat_ferret.preview.cache.get_settings", return_value=mock_settings):
            yield

    @pytest.mark.usefixtures("_mock_settings")
    async def test_register_updates_cache_bytes(self, tmp_path: Path) -> None:
        """register() sets preview_cache_bytes gauge."""
        from stoat_ferret.preview.cache import PreviewCache

        cache = PreviewCache(base_dir=str(tmp_path))

        # Create a session dir with a file
        session_dir = tmp_path / "sess-1"
        session_dir.mkdir()
        (session_dir / "data.ts").write_bytes(b"x" * 100)

        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await cache.register("sess-1", expires)

        val = _sample("video_editor_preview_cache_bytes")
        assert val >= 100

    @pytest.mark.usefixtures("_mock_settings")
    async def test_max_bytes_set_on_init(self, tmp_path: Path) -> None:
        """__init__() sets preview_cache_max_bytes gauge."""
        from stoat_ferret.preview.cache import PreviewCache

        PreviewCache(base_dir=str(tmp_path), max_bytes=2_000_000)

        val = _sample("video_editor_preview_cache_max_bytes")
        assert val == 2_000_000

    @pytest.mark.usefixtures("_mock_settings")
    async def test_eviction_increments_evictions_total(self, tmp_path: Path) -> None:
        """LRU eviction increments preview_cache_evictions_total."""
        from stoat_ferret.preview.cache import PreviewCache

        cache = PreviewCache(base_dir=str(tmp_path), max_bytes=150)

        # Create first session dir
        s1_dir = tmp_path / "sess-lru-1"
        s1_dir.mkdir()
        (s1_dir / "data.ts").write_bytes(b"x" * 100)

        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await cache.register("sess-lru-1", expires)

        before = _sample(
            "video_editor_preview_cache_evictions_total",
            {"reason": "lru_eviction"},
        )

        # Create second session that triggers LRU eviction
        s2_dir = tmp_path / "sess-lru-2"
        s2_dir.mkdir()
        (s2_dir / "data.ts").write_bytes(b"y" * 100)
        await cache.register("sess-lru-2", expires)

        after = _sample(
            "video_editor_preview_cache_evictions_total",
            {"reason": "lru_eviction"},
        )
        assert after > before

    @pytest.mark.usefixtures("_mock_settings")
    async def test_touch_miss_updates_hit_ratio(self, tmp_path: Path) -> None:
        """touch() on missing session updates cache_hit_ratio."""
        from stoat_ferret.preview.cache import PreviewCache

        cache = PreviewCache(base_dir=str(tmp_path))

        await cache.touch("nonexistent-session")

        val = _sample("video_editor_preview_cache_hit_ratio")
        # After a miss with no prior hits, ratio should be 0
        assert val == 0.0

    @pytest.mark.usefixtures("_mock_settings")
    async def test_touch_hit_updates_hit_ratio(self, tmp_path: Path) -> None:
        """touch() on existing session updates cache_hit_ratio positively."""
        from stoat_ferret.preview.cache import PreviewCache

        cache = PreviewCache(base_dir=str(tmp_path))

        # Register a session
        session_dir = tmp_path / "sess-hit"
        session_dir.mkdir()
        (session_dir / "data.ts").write_bytes(b"z" * 50)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await cache.register("sess-hit", expires)

        # Reset hit/miss counters
        cache._hits = 0
        cache._misses = 0

        await cache.touch("sess-hit")
        val = _sample("video_editor_preview_cache_hit_ratio")
        assert val == 1.0

    @pytest.mark.usefixtures("_mock_settings")
    async def test_clear_all_resets_cache_bytes(self, tmp_path: Path) -> None:
        """clear_all() sets preview_cache_bytes to 0."""
        from stoat_ferret.preview.cache import PreviewCache

        cache = PreviewCache(base_dir=str(tmp_path))

        session_dir = tmp_path / "sess-clear"
        session_dir.mkdir()
        (session_dir / "data.ts").write_bytes(b"a" * 200)
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await cache.register("sess-clear", expires)

        await cache.clear_all()

        val = _sample("video_editor_preview_cache_bytes")
        assert val == 0


class TestProxyServiceMetrics:
    """Verify ProxyService instruments proxy metrics."""

    async def test_successful_generation_records_metrics(self) -> None:
        """generate_proxy() records generation_seconds, files_total, storage_bytes."""
        from stoat_ferret.api.services.proxy_service import ProxyService
        from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus
        from stoat_ferret.ffmpeg.async_executor import ExecutionResult

        repo = AsyncMock()
        repo.add = AsyncMock()
        repo.update_status = AsyncMock()
        repo.total_size_bytes = AsyncMock(return_value=0)
        repo.get = AsyncMock(
            return_value=ProxyFile(
                id="proxy-1",
                source_video_id="vid-1",
                quality=ProxyQuality.HIGH,
                file_path="/tmp/proxy.mp4",
                file_size_bytes=5000,
                status=ProxyStatus.READY,
                source_checksum="abc123",
                generated_at=None,
                last_accessed_at=datetime.now(timezone.utc),
            )
        )

        mock_result = MagicMock(spec=ExecutionResult)
        mock_result.returncode = 0
        mock_result.stderr = b""

        executor = AsyncMock()
        executor.run = AsyncMock(return_value=mock_result)

        service = ProxyService(
            proxy_repository=repo,
            async_executor=executor,
            proxy_dir="/tmp/proxy_test",
        )

        before_pending = _sample("video_editor_proxy_files_total", {"status": "pending"})
        before_ready = _sample("video_editor_proxy_files_total", {"status": "ready"})

        with (
            patch(
                "stoat_ferret.api.services.proxy_service._run_in_thread",
                new=AsyncMock(return_value="checksum123"),
            ),
            patch(
                "stoat_ferret.api.services.proxy_service.os.path.getsize",
                return_value=5000,
            ),
            patch(
                "stoat_ferret.api.services.proxy_service.os.path.exists",
                return_value=True,
            ),
            patch("stoat_ferret.api.services.proxy_service.Path.mkdir"),
        ):
            await service.generate_proxy(
                video_id="vid-1",
                source_path="/src.mp4",
                source_width=1920,
                source_height=1080,
                duration_us=10_000_000,
            )

        after_pending = _sample("video_editor_proxy_files_total", {"status": "pending"})
        after_ready = _sample("video_editor_proxy_files_total", {"status": "ready"})

        # pending should net zero (inc then dec), ready should inc by 1
        assert after_pending == before_pending
        assert after_ready == before_ready + 1

    async def test_eviction_increments_proxy_evictions(self) -> None:
        """_check_quota_and_evict() increments proxy_evictions_total."""
        from stoat_ferret.api.services.proxy_service import ProxyService
        from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus

        oldest_proxy = ProxyFile(
            id="old-proxy",
            source_video_id="vid-old",
            quality=ProxyQuality.LOW,
            file_path="/tmp/old.mp4",
            file_size_bytes=1000,
            status=ProxyStatus.READY,
            source_checksum="abc",
            generated_at=None,
            last_accessed_at=datetime.now(timezone.utc),
        )

        repo = AsyncMock()
        # First call returns over threshold, second returns under
        repo.total_size_bytes = AsyncMock(side_effect=[9_000_000_000, 0])
        repo.get_oldest_accessed = AsyncMock(return_value=oldest_proxy)
        repo.delete = AsyncMock()

        executor = AsyncMock()

        service = ProxyService(
            proxy_repository=repo,
            async_executor=executor,
            max_storage_bytes=10_000_000_000,
        )

        before = _sample("video_editor_proxy_evictions_total", {"reason": "lru_quota"})

        with patch("stoat_ferret.api.services.proxy_service._remove_file_if_exists"):
            await service._check_quota_and_evict()

        after = _sample("video_editor_proxy_evictions_total", {"reason": "lru_quota"})
        assert after == before + 1
