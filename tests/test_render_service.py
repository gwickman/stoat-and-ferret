"""Tests for RenderService lifecycle orchestration.

Covers pre-flight checks, full job lifecycle, retry logic,
cancel lifecycle, WebSocket event emission, and DI wiring.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.events import EventType
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import PreflightError, RenderService

# Disable Rust bindings by default — tests exercise Python orchestration
# logic. Specific preflight tests override this to test Rust integration.
_PATCH_NO_RUST = patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan_json(
    *,
    total_duration: float = 60.0,
    codec: str = "libx264",
    quality_preset: str = "medium",
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
                "quality_preset": quality_preset,
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


def _make_settings(retry_count: int = 2) -> Settings:
    """Create a Settings instance with the given retry count."""
    return Settings(render_retry_count=retry_count)


def _build_service(
    repo: InMemoryRenderRepository | None = None,
    queue: RenderQueue | None = None,
    executor: RenderExecutor | None = None,
    checkpoint_manager: MagicMock | None = None,
    ws: ConnectionManager | None = None,
    settings: Settings | None = None,
) -> tuple[RenderService, InMemoryRenderRepository, ConnectionManager, RenderExecutor]:
    """Build a RenderService with sensible test defaults.

    Returns:
        Tuple of (service, repo, ws_manager, executor).
    """
    repo = repo or InMemoryRenderRepository()
    ws = ws or ConnectionManager()
    ws.broadcast = AsyncMock()  # type: ignore[method-assign]
    settings = settings or _make_settings()
    executor = executor or RenderExecutor()
    checkpoint_mgr = checkpoint_manager or _make_checkpoint_manager()
    queue = queue or RenderQueue(repo, max_concurrent=4, max_depth=50)

    service = RenderService(
        repository=repo,
        queue=queue,
        executor=executor,
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=settings,
    )
    return service, repo, ws, executor


# ---------------------------------------------------------------------------
# Pre-flight check tests
# ---------------------------------------------------------------------------


class TestPreflightChecks:
    """Pre-flight validation tests."""

    async def test_queue_at_capacity_rejected(self) -> None:
        """Pre-flight rejects when queue is at capacity."""
        repo = InMemoryRenderRepository()
        queue = RenderQueue(repo, max_concurrent=1, max_depth=1)
        with _PATCH_NO_RUST:
            service, _, _, _ = _build_service(repo=repo, queue=queue)

            # Fill the queue
            plan_json = _make_plan_json()
            job = RenderJob.create(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan=plan_json,
            )
            await queue.enqueue(job)

            with pytest.raises(PreflightError, match="capacity"):
                await service.submit_job(
                    project_id="proj-2",
                    output_path="/tmp/out2.mp4",
                    output_format=OutputFormat.MP4,
                    quality_preset=QualityPreset.STANDARD,
                    render_plan_json=plan_json,
                )

    @patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", True)
    @patch("stoat_ferret.render.service.validate_render_settings")
    @patch("stoat_ferret.render.service.estimate_output_size", return_value=10_000_000_000)
    async def test_insufficient_disk_space_rejected(
        self, mock_estimate: MagicMock, mock_validate: MagicMock
    ) -> None:
        """Pre-flight rejects when disk space is insufficient."""
        service, _, _, _ = _build_service()

        # Mock disk_usage to return low free space
        mock_usage = MagicMock()
        mock_usage.free = 100  # Only 100 bytes free
        with (
            patch("stoat_ferret.render.service.shutil.disk_usage", return_value=mock_usage),
            patch("stoat_ferret.render.service.Path.exists", return_value=True),
            pytest.raises(PreflightError, match="Insufficient disk space"),
        ):
            await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

    @patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", True)
    @patch("stoat_ferret.render.service.validate_render_settings")
    async def test_invalid_settings_rejected(self, mock_validate: MagicMock) -> None:
        """Pre-flight rejects when render settings are invalid."""
        mock_validate.side_effect = ValueError("Invalid codec")
        service, _, _, _ = _build_service()

        with pytest.raises(PreflightError, match="Invalid render settings"):
            await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )


# ---------------------------------------------------------------------------
# Job lifecycle tests
# ---------------------------------------------------------------------------


class TestJobLifecycle:
    """Job lifecycle coordination tests."""

    async def test_submit_creates_and_enqueues(self) -> None:
        """submit_job creates a job and enqueues it."""
        with _PATCH_NO_RUST:
            service, repo, ws, _ = _build_service()
            plan_json = _make_plan_json()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )

            assert job.status == RenderStatus.QUEUED
            assert job.project_id == "proj-1"
            persisted = await repo.get(job.id)
            assert persisted is not None

    async def test_submit_broadcasts_render_started(self) -> None:
        """submit_job broadcasts RENDER_STARTED event (among others)."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            broadcast_calls = ws.broadcast.call_args_list
            event_types = [c[0][0]["type"] for c in broadcast_calls]
            assert EventType.RENDER_STARTED.value in event_types

    async def test_run_job_success_completes(self) -> None:
        """Successful execution completes the job and broadcasts RENDER_COMPLETED."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )
            ws.broadcast.reset_mock()

            # Need to transition to running first (simulating dequeue)
            await repo.update_status(job.id, RenderStatus.RUNNING)

            # Mock executor to succeed
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg", "-i", "input.mp4"])

            completed = await repo.get(job.id)
            assert completed is not None
            assert completed.status == RenderStatus.COMPLETED

            # Should have broadcast RENDER_COMPLETED
            broadcast_calls = ws.broadcast.call_args_list
            event_types = [c[0][0]["type"] for c in broadcast_calls]
            assert EventType.RENDER_COMPLETED.value in event_types

    async def test_full_lifecycle_submit_to_completion(self) -> None:
        """Full lifecycle: submit -> dequeue -> execute -> complete."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json()

            # Submit
            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )

            # Dequeue (simulates queue processing)
            dequeued = await service._queue.dequeue()
            assert dequeued is not None
            assert dequeued.status == RenderStatus.RUNNING

            ws.broadcast.reset_mock()

            # Execute successfully
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(dequeued, ["ffmpeg", "-i", "input.mp4"])

            # Verify completed
            completed = await repo.get(job.id)
            assert completed is not None
            assert completed.status == RenderStatus.COMPLETED


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Retry on transient failure tests."""

    async def test_retry_on_failure_requeues(self) -> None:
        """On transient failure, job is retried by resetting to queued."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=_make_settings(retry_count=2),
            )
            plan_json = _make_plan_json()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )

            # Transition to running
            await repo.update_status(job.id, RenderStatus.RUNNING)

            ws.broadcast.reset_mock()

            # Execute and fail
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg", "-i", "input.mp4"])

            # Should be requeued for retry
            requeued = await repo.get(job.id)
            assert requeued is not None
            assert requeued.status == RenderStatus.QUEUED
            assert requeued.retry_count == 1

    async def test_no_retry_after_max_attempts(self) -> None:
        """No retry after max attempts — job stays failed."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=_make_settings(retry_count=2),
            )
            plan_json = _make_plan_json()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )

            # Simulate 2 retries already occurred
            await repo.update_status(job.id, RenderStatus.RUNNING)
            await repo.update_status(job.id, RenderStatus.FAILED, error_message="fail 1")
            await repo.update_status(job.id, RenderStatus.QUEUED)  # retry 1
            await repo.update_status(job.id, RenderStatus.RUNNING)
            await repo.update_status(job.id, RenderStatus.FAILED, error_message="fail 2")
            await repo.update_status(job.id, RenderStatus.QUEUED)  # retry 2
            await repo.update_status(job.id, RenderStatus.RUNNING)

            ws.broadcast.reset_mock()

            # Execute and fail again — should NOT retry (retry_count=2 == max_retries)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg", "-i", "input.mp4"])

            # Should be permanently failed
            failed = await repo.get(job.id)
            assert failed is not None
            assert failed.status == RenderStatus.FAILED

            # Should have broadcast RENDER_FAILED
            broadcast_calls = ws.broadcast.call_args_list
            event_types = [c[0][0]["type"] for c in broadcast_calls]
            assert EventType.RENDER_FAILED.value in event_types

    async def test_retry_increments_count(self) -> None:
        """Each retry increments retry_count."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=_make_settings(retry_count=3),
            )
            plan_json = _make_plan_json()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )

            # First failure
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            requeued = await repo.get(job.id)
            assert requeued is not None
            assert requeued.retry_count == 1
            assert requeued.status == RenderStatus.QUEUED


# ---------------------------------------------------------------------------
# Cancel lifecycle tests
# ---------------------------------------------------------------------------


class TestCancelLifecycle:
    """Cancel lifecycle tests."""

    async def test_cancel_queued_job(self) -> None:
        """Cancelling a queued job sets status to cancelled."""
        with _PATCH_NO_RUST:
            service, repo, ws, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            ws.broadcast.reset_mock()

            result = await service.cancel_job(job.id)
            assert result is True

            cancelled = await repo.get(job.id)
            assert cancelled is not None
            assert cancelled.status == RenderStatus.CANCELLED

    async def test_cancel_broadcasts_event(self) -> None:
        """Cancelling a job broadcasts RENDER_CANCELLED."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            ws.broadcast.reset_mock()

            await service.cancel_job(job.id)

            broadcast_calls = ws.broadcast.call_args_list
            event_types = [c[0][0]["type"] for c in broadcast_calls]
            assert EventType.RENDER_CANCELLED.value in event_types

    async def test_cancel_nonexistent_returns_false(self) -> None:
        """Cancelling a nonexistent job returns False."""
        service, _, _, _ = _build_service()
        result = await service.cancel_job("nonexistent-id")
        assert result is False

    async def test_cancel_completed_returns_false(self) -> None:
        """Cancelling an already completed job returns False."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            await repo.update_status(job.id, RenderStatus.RUNNING)
            await repo.update_status(job.id, RenderStatus.COMPLETED)

            result = await service.cancel_job(job.id)
            assert result is False


# ---------------------------------------------------------------------------
# WebSocket event emission tests
# ---------------------------------------------------------------------------


class TestWebSocketEvents:
    """WebSocket event emission tests."""

    async def test_render_started_on_submit(self) -> None:
        """RENDER_STARTED event is emitted on job submission."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            broadcast_calls = ws.broadcast.call_args_list
            started_events = [
                c[0][0]
                for c in broadcast_calls
                if c[0][0]["type"] == EventType.RENDER_STARTED.value
            ]
            assert len(started_events) == 1
            assert started_events[0]["payload"]["job_id"] == job.id

    async def test_render_completed_on_success(self) -> None:
        """RENDER_COMPLETED event is emitted on successful completion."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            broadcast_calls = ws.broadcast.call_args_list
            event_types = [c[0][0]["type"] for c in broadcast_calls]
            assert EventType.RENDER_COMPLETED.value in event_types

    async def test_render_failed_on_permanent_failure(self) -> None:
        """RENDER_FAILED event is emitted when job fails permanently."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=_make_settings(retry_count=0),
            )

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            broadcast_calls = ws.broadcast.call_args_list
            event_types = [c[0][0]["type"] for c in broadcast_calls]
            assert EventType.RENDER_FAILED.value in event_types

    async def test_render_cancelled_on_cancel(self) -> None:
        """RENDER_CANCELLED event is emitted on cancellation."""
        with _PATCH_NO_RUST:
            service, _, ws, _ = _build_service()

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            ws.broadcast.reset_mock()

            await service.cancel_job(job.id)

            broadcast_calls = ws.broadcast.call_args_list
            event_types = [c[0][0]["type"] for c in broadcast_calls]
            assert EventType.RENDER_CANCELLED.value in event_types


# ---------------------------------------------------------------------------
# Recovery tests
# ---------------------------------------------------------------------------


class TestRecovery:
    """Recovery tests."""

    async def test_recover_delegates_to_queue_and_checkpoints(self) -> None:
        """recover() calls queue.recover() and checkpoint_manager.recover()."""
        repo = InMemoryRenderRepository()
        queue = RenderQueue(repo, max_concurrent=4, max_depth=50)
        checkpoint_mgr = _make_checkpoint_manager()
        checkpoint_mgr.recover.return_value = [("job-1", 3)]

        service, _, _, _ = _build_service(
            repo=repo,
            queue=queue,
            checkpoint_manager=checkpoint_mgr,
        )

        result = await service.recover()
        assert result == [("job-1", 3)]
        checkpoint_mgr.recover.assert_awaited_once()


# ---------------------------------------------------------------------------
# Cleanup tests
# ---------------------------------------------------------------------------


class TestCleanup:
    """Cleanup tests."""

    async def test_cleanup_on_completion(self) -> None:
        """Cleanup runs on successful completion."""
        with _PATCH_NO_RUST:
            checkpoint_mgr = _make_checkpoint_manager()
            service, repo, ws, executor = _build_service(
                checkpoint_manager=checkpoint_mgr,
            )

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            checkpoint_mgr.cleanup_stale.assert_awaited_once_with([job.id])

    async def test_cleanup_on_permanent_failure(self) -> None:
        """Cleanup runs on permanent failure (no more retries)."""
        with _PATCH_NO_RUST:
            checkpoint_mgr = _make_checkpoint_manager()
            service, repo, ws, executor = _build_service(
                checkpoint_manager=checkpoint_mgr,
                settings=_make_settings(retry_count=0),
            )

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )

            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=False)  # type: ignore[method-assign]
            await service.run_job(job, ["ffmpeg"])

            checkpoint_mgr.cleanup_stale.assert_awaited_once_with([job.id])


# ---------------------------------------------------------------------------
# Duration extraction tests
# ---------------------------------------------------------------------------


class TestExtractDuration:
    """Duration extraction from render plan JSON."""

    def test_valid_plan(self) -> None:
        """Extracts duration in microseconds from valid plan."""
        plan = _make_plan_json(total_duration=120.5)
        result = RenderService._extract_duration_us(plan)
        assert result == 120_500_000

    def test_missing_duration(self) -> None:
        """Returns 0 when duration is missing."""
        plan = json.dumps({"segments": []})
        result = RenderService._extract_duration_us(plan)
        assert result == 0

    def test_invalid_json(self) -> None:
        """Returns 0 for invalid JSON."""
        result = RenderService._extract_duration_us("not json")
        assert result == 0


# ---------------------------------------------------------------------------
# ETA and speed ratio computation tests
# ---------------------------------------------------------------------------


class TestETAAndSpeedRatio:
    """Tests for ETA and speed ratio computation in progress callback."""

    async def test_progress_callback_computes_eta(self) -> None:
        """Progress callback calls estimate_eta and includes result in broadcast."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json(total_duration=60.0)

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            # Mock executor to invoke the progress callback with elapsed_seconds
            async def fake_execute(
                job_obj: RenderJob,
                cmd: list[str],
                *,
                total_duration_us: int = 0,
            ) -> bool:
                cb = executor._progress_callback
                if cb is not None:
                    await cb(job_obj.id, 0.5, 10.0, None, None)  # 50% at 10s elapsed
                return True

            executor.execute = fake_execute  # type: ignore[assignment]

            # Patch estimate_eta to return a known value
            with (
                patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", True),
                patch("stoat_ferret.render.service.estimate_eta", return_value=10.0),
            ):
                await service.run_job(job, ["ffmpeg"])

            events = [c[0][0] for c in ws.broadcast.call_args_list]
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) >= 1
            payload = progress_events[0]["payload"]
            assert payload["eta_seconds"] == 10.0

    async def test_progress_callback_computes_speed_ratio(self) -> None:
        """Speed ratio = (total_duration_s * progress) / elapsed_seconds."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json(total_duration=60.0)

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            async def fake_execute(
                job_obj: RenderJob,
                cmd: list[str],
                *,
                total_duration_us: int = 0,
            ) -> bool:
                cb = executor._progress_callback
                if cb is not None:
                    # 50% progress, 10s elapsed → speed = (60*0.5)/10 = 3.0
                    await cb(job_obj.id, 0.5, 10.0, None, None)
                return True

            executor.execute = fake_execute  # type: ignore[assignment]

            await service.run_job(job, ["ffmpeg"])

            events = [c[0][0] for c in ws.broadcast.call_args_list]
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            assert len(progress_events) >= 1
            payload = progress_events[0]["payload"]
            assert payload["speed_ratio"] == pytest.approx(3.0)

    async def test_eta_null_at_zero_progress(self) -> None:
        """ETA is null when progress is 0."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json(total_duration=60.0)

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            async def fake_execute(
                job_obj: RenderJob,
                cmd: list[str],
                *,
                total_duration_us: int = 0,
            ) -> bool:
                cb = executor._progress_callback
                if cb is not None:
                    await cb(job_obj.id, 0.0, 1.0, None, None)
                return True

            executor.execute = fake_execute  # type: ignore[assignment]

            with (
                patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", True),
                patch("stoat_ferret.render.service.estimate_eta", return_value=None),
            ):
                await service.run_job(job, ["ffmpeg"])

            events = [c[0][0] for c in ws.broadcast.call_args_list]
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            # Progress at 0.0 may be throttled (delta < 5%), check completed event instead
            # But eta_seconds=None in any progress event that made it through
            for pe in progress_events:
                assert pe["payload"]["eta_seconds"] is None

    async def test_eta_null_at_full_progress(self) -> None:
        """ETA is null when progress is 1.0 (complete)."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json(total_duration=60.0)

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            async def fake_execute(
                job_obj: RenderJob,
                cmd: list[str],
                *,
                total_duration_us: int = 0,
            ) -> bool:
                cb = executor._progress_callback
                if cb is not None:
                    await cb(job_obj.id, 1.0, 60.0, None, None)
                return True

            executor.execute = fake_execute  # type: ignore[assignment]

            with (
                patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", True),
                patch("stoat_ferret.render.service.estimate_eta", return_value=None),
            ):
                await service.run_job(job, ["ffmpeg"])

            events = [c[0][0] for c in ws.broadcast.call_args_list]
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            # Final progress (1.0) always sent
            final_events = [e for e in progress_events if e["payload"]["progress"] == 1.0]
            assert len(final_events) >= 1
            assert final_events[0]["payload"]["eta_seconds"] is None

    async def test_speed_ratio_null_when_elapsed_zero(self) -> None:
        """Speed ratio is null when elapsed_seconds is 0."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json(total_duration=60.0)

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            async def fake_execute(
                job_obj: RenderJob,
                cmd: list[str],
                *,
                total_duration_us: int = 0,
            ) -> bool:
                cb = executor._progress_callback
                if cb is not None:
                    await cb(job_obj.id, 0.5, 0.0, None, None)  # 0 elapsed
                return True

            executor.execute = fake_execute  # type: ignore[assignment]

            await service.run_job(job, ["ffmpeg"])

            events = [c[0][0] for c in ws.broadcast.call_args_list]
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            for pe in progress_events:
                assert pe["payload"]["speed_ratio"] is None

    async def test_speed_ratio_null_when_total_duration_zero(self) -> None:
        """Speed ratio is null when total_duration_us is 0."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            plan_json = _make_plan_json(total_duration=0.0)

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=plan_json,
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            ws.broadcast.reset_mock()

            async def fake_execute(
                job_obj: RenderJob,
                cmd: list[str],
                *,
                total_duration_us: int = 0,
            ) -> bool:
                cb = executor._progress_callback
                if cb is not None:
                    await cb(job_obj.id, 0.5, 10.0, None, None)
                return True

            executor.execute = fake_execute  # type: ignore[assignment]

            await service.run_job(job, ["ffmpeg"])

            events = [c[0][0] for c in ws.broadcast.call_args_list]
            progress_events = [e for e in events if e["type"] == EventType.RENDER_PROGRESS.value]
            for pe in progress_events:
                assert pe["payload"]["speed_ratio"] is None
