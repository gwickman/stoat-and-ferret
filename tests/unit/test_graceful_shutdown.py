"""Tests for graceful degradation and shutdown of the preview subsystem.

Covers:
- FFmpeg unavailable degradation (503 FFMPEG_UNAVAILABLE from preview endpoints)
- Proxy auto-generation skipped when FFmpeg unavailable
- App health when FFmpeg unavailable (non-preview endpoints still work)
- Shutdown cancels active FFmpeg processes via cancel_all()
- Shutdown cleans up temporary segment files
- Shutdown logs lifecycle events
- FFmpeg subprocess created with stdin=PIPE
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.models import PreviewQuality
from stoat_ferret.db.preview_repository import InMemoryPreviewRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.preview.manager import PreviewManager

# ---------- Helpers ----------


def _make_mock_generator(output_dir: Path | None = None) -> AsyncMock:
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


def _make_manager(
    *,
    output_base_dir: str = "/tmp/test-previews",
    max_sessions: int = 5,
) -> tuple[PreviewManager, InMemoryPreviewRepository, AsyncMock, MagicMock]:
    """Create a PreviewManager with test dependencies."""
    repo = InMemoryPreviewRepository()
    gen = _make_mock_generator(output_dir=Path(output_base_dir) / "fake-session")
    ws = _make_mock_ws_manager()

    mgr = PreviewManager(
        repository=repo,
        generator=gen,
        ws_manager=ws,
        max_sessions=max_sessions,
        session_ttl_seconds=3600,
        output_base_dir=output_base_dir,
    )
    return mgr, repo, gen, ws


def _make_app_client() -> TestClient:
    """Create a test client with minimal DI (no FFmpeg needed)."""
    app = create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        job_queue=InMemoryJobQueue(),
    )
    return TestClient(app)


# ---------- Stage 1: stdin=PIPE ----------


class TestStdinPipe:
    """FR-007: FFmpeg subprocess created with stdin=PIPE."""

    async def test_real_executor_uses_stdin_pipe(self) -> None:
        """RealAsyncFFmpegExecutor passes stdin=PIPE to create_subprocess_exec."""
        from stoat_ferret.ffmpeg.async_executor import RealAsyncFFmpegExecutor

        executor = RealAsyncFFmpegExecutor(ffmpeg_path="echo")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            mock_proc.stderr = AsyncMock()
            mock_proc.stderr.readline = AsyncMock(return_value=b"")
            mock_proc.pid = 12345
            mock_exec.return_value = mock_proc

            await executor.run(["-version"])

            mock_exec.assert_called_once()
            call_kwargs = mock_exec.call_args
            # stdin=PIPE should be passed
            assert call_kwargs.kwargs.get("stdin") == asyncio.subprocess.PIPE


# ---------- Stage 2: Degradation ----------


class TestDegradation:
    """Tests for FFmpeg-unavailable degradation paths."""

    def test_app_starts_without_ffmpeg(self) -> None:
        """FR-001: App starts and serves non-preview endpoints without FFmpeg."""
        client = _make_app_client()
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @patch("stoat_ferret.api.routers.preview.shutil.which", return_value=None)
    def test_start_preview_returns_503_without_ffmpeg(self, _mock_which: MagicMock) -> None:
        """FR-002: Preview start returns 503 FFMPEG_UNAVAILABLE."""
        client = _make_app_client()
        resp = client.post(
            "/api/v1/projects/test-proj/preview/start",
            json={"quality": "medium"},
        )
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["code"] == "FFMPEG_UNAVAILABLE"

    @patch("stoat_ferret.api.routers.preview.shutil.which", return_value=None)
    def test_seek_preview_returns_503_without_ffmpeg(self, _mock_which: MagicMock) -> None:
        """FR-002: Preview seek returns 503 FFMPEG_UNAVAILABLE."""
        client = _make_app_client()
        resp = client.post(
            "/api/v1/preview/test-session/seek",
            json={"position": 0.5},
        )
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["code"] == "FFMPEG_UNAVAILABLE"

    @patch("stoat_ferret.api.routers.preview.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_preview_endpoints_work_when_ffmpeg_available(self, _mock_which: MagicMock) -> None:
        """Non-regression: preview endpoints proceed normally with FFmpeg present.

        The 503 check should not fire; the endpoint proceeds to normal
        validation (404 for missing project).
        """
        client = _make_app_client()
        resp = client.post(
            "/api/v1/projects/nonexistent/preview/start",
            json={"quality": "medium"},
        )
        # Should get past FFmpeg check and hit 503 (no preview manager) or 404
        assert resp.status_code in (404, 503)
        detail = resp.json()["detail"]
        assert detail["code"] != "FFMPEG_UNAVAILABLE"

    async def test_proxy_auto_queue_skipped_without_ffmpeg(self) -> None:
        """FR-003: Scan completes with warning, no proxy generation when FFmpeg unavailable."""
        from stoat_ferret.api.schemas.video import ScanResponse
        from stoat_ferret.api.services.scan import _auto_queue_proxies

        mock_repo = AsyncMock()
        mock_proxy_service = MagicMock()
        mock_queue = MagicMock()

        result = ScanResponse(scanned=1, new=1, updated=0, skipped=0, errors=[])

        with patch("stoat_ferret.api.services.scan.shutil.which", return_value=None):
            await _auto_queue_proxies(
                result=result,
                repository=mock_repo,
                proxy_service=mock_proxy_service,
                queue=mock_queue,
                scan_path="/test/path",
            )

        # No proxy jobs should have been submitted
        mock_queue.submit.assert_not_called()

    @patch("stoat_ferret.api.routers.preview.shutil.which", return_value=None)
    def test_non_preview_endpoints_unaffected(self, _mock_which: MagicMock) -> None:
        """FR-001: Non-preview endpoints remain available without FFmpeg.

        GET/DELETE on preview status/cache don't need FFmpeg.
        """
        client = _make_app_client()
        # Health endpoint works
        resp = client.get("/health/live")
        assert resp.status_code == 200

        # GET preview status returns 503 because no preview manager, not FFMPEG_UNAVAILABLE
        resp = client.get("/api/v1/preview/test-session")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["code"] == "SERVICE_UNAVAILABLE"


# ---------- Stage 3: Graceful Shutdown ----------


class TestGracefulShutdown:
    """Tests for preview subsystem shutdown."""

    async def test_cancel_all_no_active_sessions(self) -> None:
        """cancel_all() works when no sessions are active."""
        manager, _repo, _gen, _ws = _make_manager()
        count = await manager.cancel_all()
        assert count == 0

    async def test_cancel_all_cancels_active_tasks(self) -> None:
        """FR-004: Active FFmpeg processes terminated on shutdown."""
        manager, repo, gen, _ws = _make_manager()

        # Make generate() block indefinitely until cancelled
        cancel_signal = asyncio.Event()

        async def slow_generate(**kwargs: object) -> Path:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                cancel_signal.set()
                raise
            return Path("/tmp/test-previews/fake-session")

        gen.generate = slow_generate

        await manager.start(
            project_id="proj1",
            input_path="/test/video.mp4",
            quality_level=PreviewQuality.MEDIUM,
        )

        # Verify there's an active task
        assert len(manager._generation_tasks) == 1

        # Cancel all
        count = await manager.cancel_all()
        assert count == 1

        # Tracking state should be cleared
        assert len(manager._generation_tasks) == 0
        assert len(manager._cancel_events) == 0

    async def test_cancel_all_cleans_up_temp_files(self, tmp_path: Path) -> None:
        """FR-005: Temporary preview segment files cleaned up on shutdown."""
        output_dir = tmp_path / "previews"
        output_dir.mkdir()

        # Create some fake session directories with segment files
        session_dir = output_dir / "session-123"
        session_dir.mkdir()
        (session_dir / "segment_000.ts").write_bytes(b"\x00" * 100)
        (session_dir / "segment_001.ts").write_bytes(b"\x00" * 100)
        (session_dir / "manifest.m3u8").write_text("#EXTM3U\n")

        manager, _repo, _gen, _ws = _make_manager(output_base_dir=str(output_dir))

        await manager.cancel_all()

        # Session directory should be removed
        assert not session_dir.exists()

    async def test_cancel_all_logs_lifecycle_events(self, tmp_path: Path) -> None:
        """FR-006: preview_shutdown_started and preview_shutdown_complete events logged."""
        manager, _repo, _gen, _ws = _make_manager(
            output_base_dir=str(tmp_path / "previews"),
        )

        with patch("stoat_ferret.preview.manager.logger") as mock_logger:
            await manager.cancel_all()

        # Extract all info() call event names
        call_args_list = mock_logger.info.call_args_list
        events = [
            call.args[0] if call.args else call.kwargs.get("event") for call in call_args_list
        ]
        assert "preview_shutdown_started" in events
        assert "preview_shutdown_complete" in events

        # Verify timing is in the completion call
        complete_call = next(
            c for c in call_args_list if c.args and c.args[0] == "preview_shutdown_complete"
        )
        assert "duration_seconds" in complete_call.kwargs

    async def test_cancel_all_completes_within_timeout(self) -> None:
        """NFR-001: Shutdown completes within 10 seconds.

        Verifies cancel_all with stuck tasks still returns promptly
        (within the 5-second per-process timeout).
        """
        import time

        manager, _repo, gen, _ws = _make_manager()

        # Make generate block but respond to cancellation
        async def stuck_generate(**kwargs: object) -> Path:
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                raise
            return Path("/tmp/test-previews/fake")

        gen.generate = stuck_generate

        await manager.start(
            project_id="proj1",
            input_path="/test/video.mp4",
        )

        start = time.monotonic()
        await manager.cancel_all()
        elapsed = time.monotonic() - start

        assert elapsed < 10.0, f"Shutdown took {elapsed:.1f}s, must be < 10s"
