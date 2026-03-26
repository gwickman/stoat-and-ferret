"""Tests for structured logging events in the preview subsystem.

Verifies that preview session, proxy, cache, thumbnail, and waveform
operations emit correctly-named structured log events with required fields
(session_id, video_id, correlation_id, duration_ms).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus
from stoat_ferret.db.preview_repository import InMemoryPreviewRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_generator(*, output_dir: Path | None = None) -> AsyncMock:
    """Create a mock HLS generator."""
    gen = AsyncMock()
    ret = output_dir or Path("/tmp/previews/fake-session")
    gen.generate = AsyncMock(return_value=ret)
    return gen


def _make_mock_ws_manager() -> MagicMock:
    """Create a mock ConnectionManager."""
    mgr = MagicMock(spec=ConnectionManager)
    mgr.broadcast = AsyncMock()
    return mgr


def _make_preview_manager(
    *,
    output_base_dir: str = "/tmp/previews",
) -> tuple:
    """Create a PreviewManager with test dependencies."""
    from stoat_ferret.preview.manager import PreviewManager

    repo = InMemoryPreviewRepository()
    gen = _make_mock_generator(output_dir=Path(output_base_dir) / "fake-session")
    ws = _make_mock_ws_manager()

    mgr = PreviewManager(
        repository=repo,
        generator=gen,
        ws_manager=ws,
        max_sessions=5,
        session_ttl_seconds=3600,
        output_base_dir=output_base_dir,
    )
    return mgr, repo, gen, ws


def _find_log_calls(mock_logger: MagicMock, event_name: str) -> list:
    """Find all log calls matching an event name across all log levels."""
    calls = []
    for method_name in ("debug", "info", "warning", "error"):
        method = getattr(mock_logger, method_name, None)
        if method and method.call_args_list:
            for call in method.call_args_list:
                if call.args and call.args[0] == event_name:
                    calls.append(call)
    return calls


# ---------------------------------------------------------------------------
# Stage 1: Preview session logging (FR-001)
# ---------------------------------------------------------------------------


class TestPreviewSessionLogging:
    """Verify preview session lifecycle log events with session_id."""

    async def test_session_created_event(self) -> None:
        """preview_session_created emitted with session_id on start."""
        mgr, repo, gen, ws = _make_preview_manager()

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            session = await mgr.start(
                project_id="proj-1",
                input_path="/media/video.mp4",
            )

            calls = _find_log_calls(mock_logger, "preview_session_created")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == session.id
            assert kwargs["project_id"] == "proj-1"
            assert "correlation_id" in kwargs

    async def test_generation_started_event(self) -> None:
        """preview_generation_started emitted with session_id."""
        mgr, repo, gen, ws = _make_preview_manager()

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            session = await mgr.start(
                project_id="proj-1",
                input_path="/media/video.mp4",
            )

            calls = _find_log_calls(mock_logger, "preview_generation_started")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == session.id
            assert "correlation_id" in kwargs

    async def test_segment_generated_event(self, tmp_path: Path) -> None:
        """preview_segment_generated emitted with session_id after generation."""
        output_dir = tmp_path / "fake-session"
        output_dir.mkdir()
        # Create fake segment files
        (output_dir / "segment_000.ts").write_bytes(b"\x00" * 100)
        (output_dir / "segment_001.ts").write_bytes(b"\x00" * 100)
        (output_dir / "manifest.m3u8").write_text("#EXTM3U")

        mgr, repo, gen, ws = _make_preview_manager(output_base_dir=str(tmp_path))
        gen.generate = AsyncMock(return_value=output_dir)

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            session = await mgr.start(
                project_id="proj-1",
                input_path="/media/video.mp4",
            )
            # Wait for the background generation task
            task = list(mgr._generation_tasks.values())
            if task:
                await task[0]

            calls = _find_log_calls(mock_logger, "preview_segment_generated")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == session.id
            assert kwargs["segment_count"] == 2
            assert "correlation_id" in kwargs

    async def test_session_ready_event(self, tmp_path: Path) -> None:
        """preview_session_ready emitted with session_id."""
        output_dir = tmp_path / "fake-session"
        output_dir.mkdir()
        (output_dir / "manifest.m3u8").write_text("#EXTM3U")

        mgr, repo, gen, ws = _make_preview_manager(output_base_dir=str(tmp_path))
        gen.generate = AsyncMock(return_value=output_dir)

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            session = await mgr.start(
                project_id="proj-1",
                input_path="/media/video.mp4",
            )
            task = list(mgr._generation_tasks.values())
            if task:
                await task[0]

            calls = _find_log_calls(mock_logger, "preview_session_ready")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == session.id
            assert "correlation_id" in kwargs

    async def test_seek_requested_event(self, tmp_path: Path) -> None:
        """preview_seek_requested emitted with session_id."""
        output_dir = tmp_path / "fake-session"
        output_dir.mkdir()
        (output_dir / "manifest.m3u8").write_text("#EXTM3U")

        mgr, repo, gen, ws = _make_preview_manager(output_base_dir=str(tmp_path))
        gen.generate = AsyncMock(return_value=output_dir)

        session = await mgr.start(
            project_id="proj-1",
            input_path="/media/video.mp4",
        )
        # Wait for generation to complete
        task = list(mgr._generation_tasks.values())
        if task:
            await task[0]

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            await mgr.seek(
                session.id,
                input_path="/media/video.mp4",
            )

            calls = _find_log_calls(mock_logger, "preview_seek_requested")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == session.id
            assert "correlation_id" in kwargs

    async def test_generation_failed_event(self) -> None:
        """preview_generation_failed emitted with session_id on error."""
        mgr, repo, gen, ws = _make_preview_manager()
        gen.generate = AsyncMock(side_effect=RuntimeError("ffmpeg crashed"))

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            session = await mgr.start(
                project_id="proj-1",
                input_path="/media/video.mp4",
            )
            # Wait for the generation task to fail
            task = list(mgr._generation_tasks.values())
            if task:
                await task[0]

            calls = _find_log_calls(mock_logger, "preview_generation_failed")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == session.id
            assert "error" in kwargs
            assert "correlation_id" in kwargs

    async def test_session_expired_event(self) -> None:
        """preview_session_expired emitted with session_id."""
        mgr, repo, gen, ws = _make_preview_manager()

        session = await mgr.start(
            project_id="proj-1",
            input_path="/media/video.mp4",
        )
        # Wait for generation
        task = list(mgr._generation_tasks.values())
        if task:
            await task[0]

        # Force session to be expired
        stored = await repo.get(session.id)
        assert stored is not None
        stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await repo.update(stored)

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            cleaned = await mgr.cleanup_expired()
            assert cleaned == 1

            calls = _find_log_calls(mock_logger, "preview_session_expired")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == session.id


class TestPreviewSessionNamingConvention:
    """Verify all preview session events follow {subsystem}_{action} naming (NFR-001)."""

    async def test_all_event_names_follow_convention(self, tmp_path: Path) -> None:
        """All preview session log events match preview_{action} pattern."""
        output_dir = tmp_path / "fake-session"
        output_dir.mkdir()
        (output_dir / "manifest.m3u8").write_text("#EXTM3U")

        mgr, repo, gen, ws = _make_preview_manager(output_base_dir=str(tmp_path))
        gen.generate = AsyncMock(return_value=output_dir)

        expected_events = {
            "preview_session_created",
            "preview_generation_started",
            "preview_segment_generated",
            "preview_session_ready",
        }

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            await mgr.start(
                project_id="proj-1",
                input_path="/media/video.mp4",
            )
            task = list(mgr._generation_tasks.values())
            if task:
                await task[0]

            emitted = set()
            for method_name in ("debug", "info", "warning", "error"):
                method = getattr(mock_logger, method_name, None)
                if method and method.call_args_list:
                    for call in method.call_args_list:
                        if call.args:
                            emitted.add(call.args[0])

            assert expected_events.issubset(emitted)


# ---------------------------------------------------------------------------
# Stage 2: Proxy logging (FR-002)
# ---------------------------------------------------------------------------


class TestProxyLogging:
    """Verify proxy events with video_id field."""

    async def test_proxy_stale_detected_event(self) -> None:
        """proxy_stale_detected emitted with video_id."""
        mock_repo = AsyncMock()
        mock_executor = AsyncMock()

        proxy = ProxyFile(
            id="proxy-1",
            source_video_id="vid-1",
            quality=ProxyQuality.MEDIUM,
            file_path="/proxies/vid-1_medium.mp4",
            file_size_bytes=1000,
            status=ProxyStatus.READY,
            source_checksum="abc123",
            generated_at=None,
            last_accessed_at=datetime.now(timezone.utc),
        )
        mock_repo.get = AsyncMock(return_value=proxy)
        mock_repo.update_status = AsyncMock()

        from stoat_ferret.api.services.proxy_service import ProxyService

        svc = ProxyService(
            proxy_repository=mock_repo,
            async_executor=mock_executor,
        )

        with (
            patch("stoat_ferret.api.services.proxy_service.logger") as mock_logger,
            patch(
                "stoat_ferret.api.services.proxy_service._run_in_thread",
                return_value="different_checksum",
            ),
        ):
            is_stale = await svc.check_stale("proxy-1", "/media/video.mp4")

            assert is_stale is True
            calls = _find_log_calls(mock_logger, "proxy_stale_detected")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["video_id"] == "vid-1"

    async def test_proxy_cache_eviction_event(self) -> None:
        """proxy_cache_eviction emitted with video_id."""
        mock_repo = AsyncMock()
        mock_executor = AsyncMock()

        oldest = ProxyFile(
            id="proxy-old",
            source_video_id="vid-old",
            quality=ProxyQuality.MEDIUM,
            file_path="/proxies/vid-old_medium.mp4",
            file_size_bytes=5000,
            status=ProxyStatus.READY,
            source_checksum="abc",
            generated_at=None,
            last_accessed_at=datetime.now(timezone.utc),
        )
        # total_size_bytes returns over threshold, then under threshold
        mock_repo.total_size_bytes = AsyncMock(side_effect=[9_000_000_000, 0])
        mock_repo.get_oldest_accessed = AsyncMock(return_value=oldest)
        mock_repo.delete = AsyncMock()

        from stoat_ferret.api.services.proxy_service import ProxyService

        svc = ProxyService(
            proxy_repository=mock_repo,
            async_executor=mock_executor,
            max_storage_bytes=10_000_000_000,
        )

        with (
            patch("stoat_ferret.api.services.proxy_service.logger") as mock_logger,
            patch("stoat_ferret.api.services.proxy_service._remove_file_if_exists"),
        ):
            await svc._check_quota_and_evict()

            calls = _find_log_calls(mock_logger, "proxy_cache_eviction")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["video_id"] == "vid-old"


# ---------------------------------------------------------------------------
# Stage 2: Cache logging (FR-003)
# ---------------------------------------------------------------------------


class TestCacheLogging:
    """Verify cache events emitted with relevant fields."""

    async def test_preview_cache_eviction_event(self, tmp_path: Path) -> None:
        """preview_cache_eviction emitted with required fields."""
        from stoat_ferret.preview.cache import PreviewCache

        cache = PreviewCache(
            base_dir=str(tmp_path),
            max_bytes=300,
            session_ttl_seconds=3600,
        )
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        # Create a session dir
        victim_dir = tmp_path / "victim"
        victim_dir.mkdir()
        (victim_dir / "seg.ts").write_bytes(b"\x00" * 200)
        await cache.register("victim", expires)

        with patch("stoat_ferret.preview.cache.logger") as mock_logger:
            trigger_dir = tmp_path / "trigger"
            trigger_dir.mkdir()
            (trigger_dir / "seg.ts").write_bytes(b"\x00" * 200)
            await cache.register("trigger", expires)

            calls = _find_log_calls(mock_logger, "preview_cache_eviction")
            assert len(calls) >= 1
            kwargs = calls[0].kwargs
            assert kwargs["evicted_session_id"] == "victim"
            assert "freed_bytes" in kwargs

    async def test_preview_cache_full_event(self, tmp_path: Path) -> None:
        """preview_cache_full emitted when cache exceeds capacity."""
        from stoat_ferret.preview.cache import PreviewCache

        cache = PreviewCache(
            base_dir=str(tmp_path),
            max_bytes=300,
            session_ttl_seconds=3600,
        )
        expires = datetime.now(timezone.utc) + timedelta(hours=1)

        victim_dir = tmp_path / "victim"
        victim_dir.mkdir()
        (victim_dir / "seg.ts").write_bytes(b"\x00" * 200)
        await cache.register("victim", expires)

        with patch("stoat_ferret.preview.cache.logger") as mock_logger:
            trigger_dir = tmp_path / "trigger"
            trigger_dir.mkdir()
            (trigger_dir / "seg.ts").write_bytes(b"\x00" * 200)
            await cache.register("trigger", expires)

            calls = _find_log_calls(mock_logger, "preview_cache_full")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["used_bytes"] == 200
            assert kwargs["max_bytes"] == 300
            assert kwargs["needed_bytes"] == 200


# ---------------------------------------------------------------------------
# Stage 2: Thumbnail and waveform logging (FR-004)
# ---------------------------------------------------------------------------


class TestThumbnailLogging:
    """Verify thumbnail events with video_id and duration_ms."""

    def test_thumbnail_generated_has_duration_ms(self) -> None:
        """thumbnail_generated emitted with video_id and duration_ms."""
        from stoat_ferret.api.services.thumbnail import ThumbnailService

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.duration_seconds = 1.5

        executor = MagicMock()
        executor.run = MagicMock(return_value=mock_result)

        svc = ThumbnailService(executor, "/tmp/thumbs")

        with patch("stoat_ferret.api.services.thumbnail.logger") as mock_logger:
            svc.generate("/media/video.mp4", "vid-1")

            calls = _find_log_calls(mock_logger, "thumbnail_generated")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["video_id"] == "vid-1"
            assert kwargs["duration_ms"] == 1500.0


class TestWaveformLogging:
    """Verify waveform events with video_id and duration_ms."""

    async def test_waveform_generated_has_duration_ms(self) -> None:
        """waveform_generated emitted with video_id and duration_ms."""
        from stoat_ferret.api.services.waveform import WaveformService

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b'{"frames": []}'
        mock_result.stderr = b""
        mock_result.duration_seconds = 2.5

        mock_executor = AsyncMock()
        mock_executor.run = AsyncMock(return_value=mock_result)

        svc = WaveformService(
            mock_executor,
            "/tmp/waveforms",
        )

        with (
            patch("stoat_ferret.api.services.waveform.logger") as mock_logger,
            patch("stoat_ferret.api.services.waveform.Path.mkdir"),
        ):
            await svc.generate_png(
                video_id="vid-1",
                video_path="/media/video.mp4",
                duration_seconds=60.0,
            )

            calls = _find_log_calls(mock_logger, "waveform_generated")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["video_id"] == "vid-1"
            assert "duration_ms" in kwargs
            assert isinstance(kwargs["duration_ms"], float)


# ---------------------------------------------------------------------------
# FR-005: FFmpeg command logging
# ---------------------------------------------------------------------------


class TestFFmpegCommandLogging:
    """Verify FFmpeg command string included in generation_started events."""

    async def test_hls_generation_started_includes_ffmpeg_command(self) -> None:
        """hls_generation_started includes ffmpeg_command field."""
        from stoat_ferret.preview.hls_generator import HLSGenerator

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = b""
        mock_result.duration_seconds = 5.0

        mock_executor = AsyncMock()
        mock_executor.run = AsyncMock(return_value=mock_result)

        gen = HLSGenerator(
            async_executor=mock_executor,
            output_base_dir="/tmp/previews",
        )

        simplify_path = "stoat_ferret.preview.hls_generator.simplify_filter_for_preview"
        with (
            patch("stoat_ferret.preview.hls_generator.logger") as mock_logger,
            patch(simplify_path, return_value=None),
            patch.object(Path, "mkdir"),
            patch.object(Path, "iterdir", return_value=[]),
        ):
            await gen.generate(
                session_id="sess-1",
                input_path="/media/video.mp4",
            )

            calls = _find_log_calls(mock_logger, "hls_generation_started")
            assert len(calls) == 1
            kwargs = calls[0].kwargs
            assert kwargs["session_id"] == "sess-1"
            assert "ffmpeg_command" in kwargs
            assert "-i" in kwargs["ffmpeg_command"]
            assert "/media/video.mp4" in kwargs["ffmpeg_command"]


# ---------------------------------------------------------------------------
# Correlation ID propagation
# ---------------------------------------------------------------------------


class TestCorrelationIdPropagation:
    """Verify correlation IDs included in all preview log events."""

    async def test_correlation_id_in_session_events(self) -> None:
        """All preview session log events include correlation_id."""
        mgr, repo, gen, ws = _make_preview_manager()

        with (
            patch("stoat_ferret.preview.manager.logger") as mock_logger,
            patch(
                "stoat_ferret.preview.manager.get_correlation_id",
                return_value="test-corr-id",
            ),
        ):
            await mgr.start(
                project_id="proj-1",
                input_path="/media/video.mp4",
            )

            # Check that correlation_id is present in session creation events
            for event_name in ("preview_session_created", "preview_generation_started"):
                calls = _find_log_calls(mock_logger, event_name)
                assert len(calls) == 1, f"Expected 1 call for {event_name}"
                assert calls[0].kwargs["correlation_id"] == "test-corr-id"
