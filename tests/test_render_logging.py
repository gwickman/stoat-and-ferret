"""Tests for render structured logging events.

Covers all 7 lifecycle events with correct event names,
job_id correlation on all entries, FFmpeg command logging at DEBUG,
FFmpeg stderr on failure, hardware detection logging, and
complete lifecycle log sequence.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog
from structlog.testing import capture_logs

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import QueueFullError, RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService

_PATCH_NO_RUST = patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", False)
_PATCH_NO_RUST_EXECUTOR = patch("stoat_ferret.render.executor._HAS_RUST_BINDINGS", False)


@pytest.fixture(autouse=True)
def _reset_structlog() -> None:
    """Reset structlog so capture_logs() works after configure_logging()."""
    structlog.reset_defaults()


def _make_plan_json(
    *,
    total_duration: float = 60.0,
    codec: str = "libx264",
) -> str:
    """Build a minimal render plan JSON for testing."""
    return json.dumps(
        {
            "total_duration": total_duration,
            "segments": [],
            "settings": {
                "output_format": "mp4",
                "width": 1920,
                "height": 1080,
                "codec": codec,
                "quality_preset": "medium",
                "fps": 30.0,
            },
        }
    )


def _make_checkpoint_manager() -> MagicMock:
    mgr = MagicMock()
    mgr.recover = AsyncMock(return_value=[])
    mgr.cleanup_stale = AsyncMock(return_value=0)
    return mgr


def _build_service(
    repo: InMemoryRenderRepository | None = None,
) -> tuple[RenderService, InMemoryRenderRepository, ConnectionManager, RenderExecutor]:
    """Build a RenderService with sensible test defaults."""
    repo = repo or InMemoryRenderRepository()
    ws = ConnectionManager()
    ws.broadcast = AsyncMock()  # type: ignore[method-assign]
    settings = Settings(render_retry_count=2)
    executor = RenderExecutor()
    queue = RenderQueue(repo, max_concurrent=4, max_depth=50)

    service = RenderService(
        repository=repo,
        queue=queue,
        executor=executor,
        checkpoint_manager=_make_checkpoint_manager(),
        connection_manager=ws,
        settings=settings,
    )
    return service, repo, ws, executor


# ---------------------------------------------------------------------------
# Service lifecycle event tests (Stage 1)
# ---------------------------------------------------------------------------


class TestServiceLifecycleEvents:
    """Tests that all 7 lifecycle events are logged with correct names."""

    async def test_render_job_created_logged(self) -> None:
        """render_job.created is logged when a job is created."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()
            with capture_logs() as cap:
                await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )
            events = [e["event"] for e in cap]
            assert "render_job.created" in events

    async def test_render_job_queued_logged(self) -> None:
        """render_job.queued is logged when a job is enqueued."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()
            with capture_logs() as cap:
                await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )
            events = [e["event"] for e in cap]
            assert "render_job.queued" in events

    async def test_render_job_started_logged(self) -> None:
        """render_job.started is logged when a job begins execution."""
        with _PATCH_NO_RUST, _PATCH_NO_RUST_EXECUTOR:
            service, repo, _, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]

            with capture_logs() as cap:
                await service.run_job(job, ["ffmpeg", "-i", "input.mp4", "output.mp4"])

            events = [e["event"] for e in cap]
            assert "render_job.started" in events

    async def test_render_job_completed_logged(self) -> None:
        """render_job.completed is logged when a job finishes successfully."""
        with _PATCH_NO_RUST, _PATCH_NO_RUST_EXECUTOR:
            service, repo, _, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]

            with capture_logs() as cap:
                await service.run_job(job, ["ffmpeg", "-i", "input.mp4", "output.mp4"])

            events = [e["event"] for e in cap]
            assert "render_job.completed" in events

    async def test_render_job_completed_includes_elapsed(self) -> None:
        """render_job.completed includes elapsed_seconds."""
        with _PATCH_NO_RUST, _PATCH_NO_RUST_EXECUTOR:
            service, repo, _, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]

            with capture_logs() as cap:
                await service.run_job(job, ["ffmpeg", "-i", "in.mp4", "out.mp4"])

            completed = [e for e in cap if e["event"] == "render_job.completed"]
            assert len(completed) == 1
            assert "elapsed_seconds" in completed[0]

    async def test_render_job_failed_logged(self) -> None:
        """render_job.failed is logged when a job fails permanently."""
        with _PATCH_NO_RUST, _PATCH_NO_RUST_EXECUTOR:
            service, repo, _, executor = _build_service()
            # Set retry count to 0 so failure is immediate
            service._max_retries = 0

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]

            with capture_logs() as cap:
                await service.run_job(job, ["ffmpeg", "-i", "input.mp4", "output.mp4"])

            events = [e["event"] for e in cap]
            assert "render_job.failed" in events

    async def test_render_job_failed_includes_error(self) -> None:
        """render_job.failed includes error context."""
        with _PATCH_NO_RUST, _PATCH_NO_RUST_EXECUTOR:
            service, repo, _, executor = _build_service()
            service._max_retries = 0

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]

            with capture_logs() as cap:
                await service.run_job(job, ["ffmpeg", "-i", "in.mp4", "out.mp4"])

            failed = [e for e in cap if e["event"] == "render_job.failed"]
            assert len(failed) == 1
            assert "error" in failed[0]

    async def test_render_job_cancelled_logged(self) -> None:
        """render_job.cancelled is logged when a job is cancelled."""
        with _PATCH_NO_RUST:
            service, repo, _, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            with capture_logs() as cap:
                result = await service.cancel_job(job.id)

            assert result is True
            events = [e["event"] for e in cap]
            assert "render_job.cancelled" in events

    async def test_render_job_progress_milestone_logged(self) -> None:
        """render_job.progress_milestone is logged at 25/50/75/100%."""
        with _PATCH_NO_RUST, _PATCH_NO_RUST_EXECUTOR:
            service, repo, _, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)

            # Simulate progress callbacks during execute
            progress_values = [0.25, 0.50, 0.75, 1.0]

            async def fake_execute(
                j: RenderJob,
                cmd: list[str],
                *,
                total_duration_us: int = 0,
            ) -> bool:
                cb = executor._progress_callback
                if cb:
                    for pv in progress_values:
                        await cb(j.id, pv)
                return True

            executor.execute = fake_execute  # type: ignore[assignment]

            with capture_logs() as cap:
                await service.run_job(job, ["ffmpeg", "-i", "in.mp4", "out.mp4"])

            milestones = [e for e in cap if e["event"] == "render_job.progress_milestone"]
            milestone_pcts = [e["milestone_pct"] for e in milestones]
            assert 25 in milestone_pcts
            assert 50 in milestone_pcts
            assert 75 in milestone_pcts
            assert 100 in milestone_pcts


class TestCorrelationIds:
    """Tests that job_id is present on all render log entries."""

    async def test_job_id_on_created_event(self) -> None:
        """render_job.created includes job_id."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()
            with capture_logs() as cap:
                job = await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )
            created = [e for e in cap if e["event"] == "render_job.created"]
            assert len(created) == 1
            assert created[0]["job_id"] == job.id

    async def test_job_id_on_queued_event(self) -> None:
        """render_job.queued includes job_id."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()
            with capture_logs() as cap:
                job = await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )
            queued = [e for e in cap if e["event"] == "render_job.queued"]
            assert len(queued) == 1
            assert queued[0]["job_id"] == job.id

    async def test_job_id_on_cancelled_event(self) -> None:
        """render_job.cancelled includes job_id."""
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service()
            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            with capture_logs() as cap:
                await service.cancel_job(job.id)
            cancelled = [e for e in cap if e["event"] == "render_job.cancelled"]
            assert len(cancelled) == 1
            assert cancelled[0]["job_id"] == job.id


# ---------------------------------------------------------------------------
# Executor logging tests (Stage 2)
# ---------------------------------------------------------------------------


class TestExecutorLogging:
    """Tests for FFmpeg command logging and stderr capture."""

    async def test_ffmpeg_command_logged_at_debug(self) -> None:
        """FFmpeg command is logged at DEBUG level."""
        with _PATCH_NO_RUST_EXECUTOR:
            executor = RenderExecutor()
            job = RenderJob.create(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan=_make_plan_json(),
            )
            command = ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"]

            mock_process = MagicMock()
            mock_process.stdout = None
            mock_process.stderr = None
            mock_process.stdin = None
            mock_process.returncode = 0
            mock_process.pid = 12345
            mock_process.wait = AsyncMock(return_value=0)

            with (
                patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)),
                capture_logs() as cap,
            ):
                await executor.execute(job, command)

            ffmpeg_cmd_logs = [e for e in cap if e["event"] == "render_executor.ffmpeg_command"]
            assert len(ffmpeg_cmd_logs) == 1
            assert ffmpeg_cmd_logs[0]["log_level"] == "debug"
            assert "ffmpeg" in ffmpeg_cmd_logs[0]["command"]

    async def test_ffmpeg_stderr_logged_on_failure(self) -> None:
        """FFmpeg stderr is logged at ERROR level on failure."""
        with _PATCH_NO_RUST_EXECUTOR:
            executor = RenderExecutor()
            job = RenderJob.create(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan=_make_plan_json(),
            )

            stderr_mock = AsyncMock()
            stderr_mock.read = AsyncMock(return_value=b"Error: codec not found\nFailed to encode")

            mock_process = MagicMock()
            mock_process.stdout = None
            mock_process.stderr = stderr_mock
            mock_process.stdin = None
            mock_process.returncode = 1
            mock_process.pid = 12345
            mock_process.wait = AsyncMock(return_value=1)

            with (
                patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)),
                capture_logs() as cap,
            ):
                result = await executor.execute(job, ["ffmpeg", "-i", "in.mp4", "out.mp4"])

            assert result is False
            stderr_logs = [e for e in cap if e["event"] == "render_executor.ffmpeg_stderr"]
            assert len(stderr_logs) == 1
            assert stderr_logs[0]["log_level"] == "error"
            assert "codec not found" in stderr_logs[0]["stderr"]
            assert stderr_logs[0]["job_id"] == job.id

    async def test_hardware_detection_logged(self) -> None:
        """Hardware detection results are logged with encoder name."""
        with _PATCH_NO_RUST_EXECUTOR:
            executor = RenderExecutor()
            job = RenderJob.create(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan=_make_plan_json(codec="h264_nvenc"),
            )

            mock_process = MagicMock()
            mock_process.stdout = None
            mock_process.stderr = None
            mock_process.stdin = None
            mock_process.returncode = 0
            mock_process.pid = 12345
            mock_process.wait = AsyncMock(return_value=0)

            with (
                patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)),
                capture_logs() as cap,
            ):
                await executor.execute(
                    job, ["ffmpeg", "-i", "in.mp4", "-c:v", "h264_nvenc", "out.mp4"]
                )

            hw_logs = [e for e in cap if e["event"] == "render_executor.hardware_detection"]
            assert len(hw_logs) == 1
            assert hw_logs[0]["encoder_name"] == "h264_nvenc"
            assert hw_logs[0]["encoder_type"] == "hardware"

    async def test_software_encoder_classified(self) -> None:
        """Software encoder is correctly classified."""
        with _PATCH_NO_RUST_EXECUTOR:
            executor = RenderExecutor()
            job = RenderJob.create(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan=_make_plan_json(codec="libx264"),
            )

            mock_process = MagicMock()
            mock_process.stdout = None
            mock_process.stderr = None
            mock_process.stdin = None
            mock_process.returncode = 0
            mock_process.pid = 12345
            mock_process.wait = AsyncMock(return_value=0)

            with (
                patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)),
                capture_logs() as cap,
            ):
                await executor.execute(job, ["ffmpeg", "-i", "in.mp4", "out.mp4"])

            hw_logs = [e for e in cap if e["event"] == "render_executor.hardware_detection"]
            assert len(hw_logs) == 1
            assert hw_logs[0]["encoder_name"] == "libx264"
            assert hw_logs[0]["encoder_type"] == "software"


# ---------------------------------------------------------------------------
# Queue logging tests (Stage 3)
# ---------------------------------------------------------------------------


class TestQueueLogging:
    """Tests for queue enqueue/dequeue event logging."""

    async def test_enqueue_logged_with_job_id(self) -> None:
        """Queue enqueue is logged with job_id."""
        repo = InMemoryRenderRepository()
        queue = RenderQueue(repo, max_concurrent=4, max_depth=50)
        job = RenderJob.create(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan=_make_plan_json(),
        )

        with capture_logs() as cap:
            await queue.enqueue(job)

        enqueue_logs = [e for e in cap if e["event"] == "render_queue.enqueue"]
        assert len(enqueue_logs) == 1
        assert enqueue_logs[0]["job_id"] == job.id

    async def test_dequeue_logged_with_job_id(self) -> None:
        """Queue dequeue is logged with job_id."""
        repo = InMemoryRenderRepository()
        queue = RenderQueue(repo, max_concurrent=4, max_depth=50)
        job = RenderJob.create(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan=_make_plan_json(),
        )
        await queue.enqueue(job)

        with capture_logs() as cap:
            dequeued = await queue.dequeue()

        assert dequeued is not None
        dequeue_logs = [e for e in cap if e["event"] == "render_queue.dequeue"]
        assert len(dequeue_logs) == 1
        assert dequeue_logs[0]["job_id"] == job.id

    async def test_queue_full_rejection_logged(self) -> None:
        """Queue full rejection is logged with job_id."""
        repo = InMemoryRenderRepository()
        queue = RenderQueue(repo, max_concurrent=1, max_depth=1)

        # Fill the queue
        job1 = RenderJob.create(
            project_id="proj-1",
            output_path="/tmp/out1.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan=_make_plan_json(),
        )
        await queue.enqueue(job1)

        job2 = RenderJob.create(
            project_id="proj-2",
            output_path="/tmp/out2.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan=_make_plan_json(),
        )

        with capture_logs() as cap, pytest.raises(QueueFullError):
            await queue.enqueue(job2)

        capacity_logs = [e for e in cap if e["event"] == "render_queue.capacity_reached"]
        assert len(capacity_logs) == 1
        assert capacity_logs[0]["job_id"] == job2.id


# ---------------------------------------------------------------------------
# Complete lifecycle sequence test
# ---------------------------------------------------------------------------


class TestLifecycleSequence:
    """Tests that a complete lifecycle produces the expected log sequence."""

    async def test_full_lifecycle_sequence(self) -> None:
        """Created -> queued -> started -> completed produces correct log order."""
        with _PATCH_NO_RUST, _PATCH_NO_RUST_EXECUTOR:
            service, repo, _, executor = _build_service()

            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]

            with capture_logs() as cap:
                job = await service.submit_job(
                    project_id="proj-1",
                    output_path="/tmp/out.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=_make_plan_json(),
                )
                await repo.update_status(job.id, RenderStatus.RUNNING)
                await service.run_job(job, ["ffmpeg", "-i", "in.mp4", "out.mp4"])

            lifecycle_events = [e["event"] for e in cap if e["event"].startswith("render_job.")]
            # Verify order: created before queued before started before completed
            assert lifecycle_events.index("render_job.created") < lifecycle_events.index(
                "render_job.queued"
            )
            assert lifecycle_events.index("render_job.queued") < lifecycle_events.index(
                "render_job.started"
            )
            assert lifecycle_events.index("render_job.started") < lifecycle_events.index(
                "render_job.completed"
            )
