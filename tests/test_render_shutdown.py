"""Tests for render graceful shutdown and FFmpeg degradation (BL-227).

Covers:
- Shutdown flag and request rejection
- Graceful shutdown sequence (cancel via stdin 'q', SIGKILL escalation)
- Temp file cleanup during shutdown
- FFmpeg-unavailable degradation (503 responses)
- System tests for full shutdown and FFmpeg-missing scenarios
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService, RenderUnavailableError

# Disable Rust bindings — tests exercise Python orchestration logic.
_PATCH_NO_RUST = patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan_json() -> str:
    """Build a minimal render plan JSON for testing."""
    return json.dumps(
        {
            "total_duration": 60.0,
            "segments": [],
            "settings": {
                "output_format": "mp4",
                "width": 1920,
                "height": 1080,
                "codec": "libx264",
                "quality_preset": "medium",
                "fps": 30.0,
            },
        }
    )


def _make_checkpoint_manager() -> MagicMock:
    """Create a mock checkpoint manager."""
    mgr = MagicMock()
    mgr.recover = AsyncMock(return_value=[])
    mgr.cleanup_stale = AsyncMock(return_value=0)
    return mgr


def _make_settings() -> Settings:
    """Create a Settings instance with defaults."""
    return Settings(render_cancel_grace_seconds=10)


def _build_service(
    *,
    ffmpeg_available: bool = True,
) -> tuple[RenderService, InMemoryRenderRepository, ConnectionManager, RenderExecutor]:
    """Build a RenderService with sensible test defaults.

    Args:
        ffmpeg_available: Whether to simulate FFmpeg being available.

    Returns:
        Tuple of (service, repo, ws_manager, executor).
    """
    repo = InMemoryRenderRepository()
    ws = ConnectionManager()
    ws.broadcast = AsyncMock()  # type: ignore[method-assign]
    settings = _make_settings()
    executor = RenderExecutor()
    checkpoint_mgr = _make_checkpoint_manager()
    queue = RenderQueue(repo, max_concurrent=4, max_depth=50)

    which_result = "/usr/bin/ffmpeg" if ffmpeg_available else None
    with patch(
        "stoat_ferret.render.service.shutil.which",
        return_value=which_result,
    ):
        service = RenderService(
            repository=repo,
            queue=queue,
            executor=executor,
            checkpoint_manager=checkpoint_mgr,
            connection_manager=ws,
            settings=settings,
        )
    return service, repo, ws, executor


def _make_job(project_id: str = "proj-1") -> RenderJob:
    """Create a test render job."""
    return RenderJob.create(
        project_id=project_id,
        output_path=f"/tmp/{project_id}/output.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_plan_json(),
    )


# ---------------------------------------------------------------------------
# Stage 1: Shutdown flag and request rejection
# ---------------------------------------------------------------------------


class TestShutdownFlag:
    """Shutdown flag prevents new render requests."""

    async def test_reject_during_shutdown(self) -> None:
        """FR-005: New render requests rejected during shutdown with 503-level error."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()
            service.initiate_shutdown()

            with pytest.raises(RenderUnavailableError, match="shutting down"):
                await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )

    async def test_is_shutting_down_property(self) -> None:
        """is_shutting_down reflects shutdown state."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()
            assert service.is_shutting_down is False
            service.initiate_shutdown()
            assert service.is_shutting_down is True

    async def test_submit_works_before_shutdown(self) -> None:
        """Jobs can be submitted normally before shutdown is initiated."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            assert job.status == RenderStatus.QUEUED


# ---------------------------------------------------------------------------
# Stage 2: Graceful shutdown sequence
# ---------------------------------------------------------------------------


class TestGracefulShutdown:
    """Graceful shutdown cancels via stdin 'q' then escalates to kill."""

    async def test_cancel_all_sends_stdin_q(self) -> None:
        """FR-002: On shutdown, stdin 'q' sent to all active FFmpeg processes."""
        executor = RenderExecutor()

        # Mock two active processes
        proc1 = MagicMock()
        proc1.stdin = MagicMock()
        proc1.stdin.write = MagicMock()
        proc1.stdin.drain = AsyncMock()
        proc1.stdin.close = MagicMock()
        proc1.returncode = None

        proc2 = MagicMock()
        proc2.stdin = MagicMock()
        proc2.stdin.write = MagicMock()
        proc2.stdin.drain = AsyncMock()
        proc2.stdin.close = MagicMock()
        proc2.returncode = None

        executor._active_processes = {"job-1": proc1, "job-2": proc2}

        cancelled = await executor.cancel_all()

        assert set(cancelled) == {"job-1", "job-2"}
        proc1.stdin.write.assert_called_once_with(b"q")
        proc2.stdin.write.assert_called_once_with(b"q")

    async def test_kill_remaining_after_grace(self) -> None:
        """FR-003: After grace period, remaining processes killed."""
        executor = RenderExecutor()

        # Process that didn't exit after cancel
        proc = MagicMock()
        proc.returncode = None
        proc.pid = 12345
        proc.kill = MagicMock()
        proc.wait = AsyncMock()

        executor._active_processes = {"job-1": proc}

        killed = await executor.kill_remaining()

        assert killed == ["job-1"]
        proc.kill.assert_called_once()

    async def test_kill_remaining_skips_exited_processes(self) -> None:
        """Processes that exited gracefully are not killed."""
        executor = RenderExecutor()

        proc = MagicMock()
        proc.returncode = 0  # Already exited

        executor._active_processes = {"job-1": proc}

        killed = await executor.kill_remaining()

        assert killed == []
        proc.kill.assert_not_called()

    async def test_cleanup_all_temp_files(self) -> None:
        """FR-004: Temp files cleaned up during shutdown for all jobs."""
        executor = RenderExecutor()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create temp files for two jobs
            file1 = Path(tmpdir) / "job1_temp.dat"
            file2 = Path(tmpdir) / "job2_temp.dat"
            file1.touch()
            file2.touch()

            executor.register_temp_file("job-1", file1)
            executor.register_temp_file("job-2", file2)

            cleaned = executor.cleanup_all_temp_files()

            assert set(cleaned) == {"job-1", "job-2"}
            assert not file1.exists()
            assert not file2.exists()

    async def test_cancel_all_handles_broken_pipe(self) -> None:
        """cancel_all handles BrokenPipeError gracefully."""
        executor = RenderExecutor()

        proc = MagicMock()
        proc.stdin = MagicMock()
        proc.stdin.write = MagicMock(side_effect=BrokenPipeError)

        executor._active_processes = {"job-1": proc}

        cancelled = await executor.cancel_all()
        assert cancelled == ["job-1"]


# ---------------------------------------------------------------------------
# Stage 3: FFmpeg degradation
# ---------------------------------------------------------------------------


class TestFFmpegDegradation:
    """Application healthy when FFmpeg not installed; render endpoints 503."""

    async def test_ffmpeg_missing_submit_returns_unavailable(self) -> None:
        """FR-001: When FFmpeg not installed, submit raises RenderUnavailableError."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service(ffmpeg_available=False)

            with pytest.raises(RenderUnavailableError, match="FFmpeg is not installed"):
                await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )

    async def test_ffmpeg_available_property(self) -> None:
        """ffmpeg_available property reflects detection result."""
        with _PATCH_NO_RUST:
            service_with, _, _, _ = _build_service(ffmpeg_available=True)
            assert service_with.ffmpeg_available is True

            service_without, _, _, _ = _build_service(ffmpeg_available=False)
            assert service_without.ffmpeg_available is False


# ---------------------------------------------------------------------------
# Endpoint-level tests
# ---------------------------------------------------------------------------


@pytest.fixture
def render_repo() -> InMemoryRenderRepository:
    """Create isolated render repository."""
    return InMemoryRenderRepository()


@pytest.fixture
def shutting_down_service(render_repo: InMemoryRenderRepository) -> RenderService:
    """Create a RenderService in shutdown mode."""
    ws = ConnectionManager()
    ws.broadcast = AsyncMock()  # type: ignore[method-assign]
    settings = _make_settings()
    executor = RenderExecutor()
    checkpoint_mgr = _make_checkpoint_manager()
    queue = RenderQueue(render_repo, max_concurrent=4, max_depth=50)

    with (
        _PATCH_NO_RUST,
        patch(
            "stoat_ferret.render.service.shutil.which",
            return_value="/usr/bin/ffmpeg",
        ),
    ):
        service = RenderService(
            repository=render_repo,
            queue=queue,
            executor=executor,
            checkpoint_manager=checkpoint_mgr,
            connection_manager=ws,
            settings=settings,
        )
    service.initiate_shutdown()
    return service


@pytest.fixture
def shutdown_client(
    render_repo: InMemoryRenderRepository,
    shutting_down_service: RenderService,
) -> Generator[TestClient, None, None]:
    """Create test client with a service in shutdown mode."""
    app = create_app(
        render_repository=render_repo,
        render_service=shutting_down_service,
    )
    with TestClient(app) as c:
        yield c


@pytest.fixture
def ffmpeg_missing_service(render_repo: InMemoryRenderRepository) -> RenderService:
    """Create a RenderService where FFmpeg is not available."""
    ws = ConnectionManager()
    ws.broadcast = AsyncMock()  # type: ignore[method-assign]
    settings = _make_settings()
    executor = RenderExecutor()
    checkpoint_mgr = _make_checkpoint_manager()
    queue = RenderQueue(render_repo, max_concurrent=4, max_depth=50)

    with _PATCH_NO_RUST, patch("stoat_ferret.render.service.shutil.which", return_value=None):
        service = RenderService(
            repository=render_repo,
            queue=queue,
            executor=executor,
            checkpoint_manager=checkpoint_mgr,
            connection_manager=ws,
            settings=settings,
        )
    return service


@pytest.fixture
def ffmpeg_missing_client(
    render_repo: InMemoryRenderRepository,
    ffmpeg_missing_service: RenderService,
) -> Generator[TestClient, None, None]:
    """Create test client with FFmpeg unavailable."""
    app = create_app(
        render_repository=render_repo,
        render_service=ffmpeg_missing_service,
    )
    with TestClient(app) as c:
        yield c


class TestEndpointShutdownRejection:
    """POST /render returns 503 during shutdown."""

    def test_render_post_503_during_shutdown(self, shutdown_client: TestClient) -> None:
        """FR-005: POST /render during shutdown returns 503 with shutting down message."""
        resp = shutdown_client.post(
            "/api/v1/render",
            json={
                "project_id": "proj-1",
                "output_format": "mp4",
                "quality_preset": "standard",
                "render_plan": _make_plan_json(),
            },
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["code"] == "RENDER_UNAVAILABLE"
        assert "shutting down" in body["detail"]["message"].lower()


class TestEndpointFFmpegMissing:
    """POST /render returns 503 when FFmpeg not installed."""

    def test_render_post_503_ffmpeg_missing(self, ffmpeg_missing_client: TestClient) -> None:
        """FR-001: POST /render returns 503 when FFmpeg is not installed."""
        resp = ffmpeg_missing_client.post(
            "/api/v1/render",
            json={
                "project_id": "proj-1",
                "output_format": "mp4",
                "quality_preset": "standard",
                "render_plan": _make_plan_json(),
            },
        )
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["code"] == "RENDER_UNAVAILABLE"
        assert "ffmpeg" in body["detail"]["message"].lower()

    def test_non_render_endpoints_work(self, ffmpeg_missing_client: TestClient) -> None:
        """FR-001: Non-render endpoints work normally when FFmpeg missing."""
        resp = ffmpeg_missing_client.get("/health/live")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# System tests: full shutdown sequence
# ---------------------------------------------------------------------------


class TestGracefulShutdownSystem:
    """System test: start render → initiate shutdown → verify sequence."""

    async def test_graceful_shutdown_sequence(self) -> None:
        """System: shutdown sets flag, cancels via stdin 'q', cleans temp files."""
        with _PATCH_NO_RUST:
            service, repo, _, executor = _build_service()

            # Submit a job
            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            # Simulate an active process
            proc = MagicMock()
            proc.stdin = MagicMock()
            proc.stdin.write = MagicMock()
            proc.stdin.drain = AsyncMock()
            proc.stdin.close = MagicMock()
            proc.returncode = None
            proc.pid = 9999
            proc.kill = MagicMock()
            proc.wait = AsyncMock()
            executor._active_processes[job.id] = proc

            # Register a temp file
            with tempfile.TemporaryDirectory() as tmpdir:
                temp_file = Path(tmpdir) / "render_temp.dat"
                temp_file.touch()
                executor.register_temp_file(job.id, temp_file)

                # Step 1: Initiate shutdown
                service.initiate_shutdown()
                assert service.is_shutting_down is True

                # Step 2: Cancel all
                cancelled = await executor.cancel_all()
                assert job.id in cancelled
                proc.stdin.write.assert_called_with(b"q")

                # Step 3: Simulate grace period elapsed, process didn't exit
                # Step 4: Kill remaining
                killed = await executor.kill_remaining()
                assert job.id in killed
                proc.kill.assert_called_once()

                # Step 5: Clean temp files
                cleaned = executor.cleanup_all_temp_files()
                assert job.id in cleaned
                assert not temp_file.exists()

                # Verify new requests are rejected
                with pytest.raises(RenderUnavailableError, match="shutting down"):
                    await service.submit_job(
                        project_id="proj-2",
                        output_path="/tmp/out2.mp4",
                        output_format=OutputFormat.MP4,
                        quality_preset=QualityPreset.STANDARD,
                        render_plan_json=_make_plan_json(),
                    )

    async def test_ffmpeg_missing_system(self) -> None:
        """System: startup succeeds → render POST returns unavailable → non-render works."""
        with _PATCH_NO_RUST:
            # Application starts successfully without FFmpeg
            service, _, _, _ = _build_service(ffmpeg_available=False)

            # Service is created and functional
            assert service.ffmpeg_available is False
            assert service.is_shutting_down is False

            # Render requests are rejected
            with pytest.raises(RenderUnavailableError, match="FFmpeg is not installed"):
                await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )

            # Recovery still works (non-render functionality)
            resume_points = await service.recover()
            assert resume_points == []
