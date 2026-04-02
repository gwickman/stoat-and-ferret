"""Tests for render Prometheus metrics.

Covers metric registration, counter increments on state transitions,
histogram duration observations, speed ratio gauge updates, queue depth
gauge, encoder active gauge, and disk usage gauge.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.metrics import (
    render_disk_usage_bytes,
    render_duration_seconds,
    render_encoder_active,
    render_jobs_total,
    render_queue_depth,
    render_speed_ratio,
)
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService

_PATCH_NO_RUST = patch("stoat_ferret.render.service._HAS_RUST_BINDINGS", False)
_PATCH_NO_RUST_EXECUTOR = patch("stoat_ferret.render.executor._HAS_RUST_BINDINGS", False)


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
    settings: Settings | None = None,
) -> tuple[RenderService, InMemoryRenderRepository, ConnectionManager, RenderExecutor]:
    repo = repo or InMemoryRenderRepository()
    ws = ConnectionManager()
    ws.broadcast = AsyncMock()  # type: ignore[method-assign]
    settings = settings or Settings(render_retry_count=2)
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


def _get_counter_value(counter, labels: dict[str, str]) -> float:
    """Get the current value of a labeled counter."""
    return counter.labels(**labels)._value.get()


def _get_gauge_value(gauge, labels: dict[str, str] | None = None) -> float:
    """Get the current value of a gauge (with optional labels)."""
    if labels:
        return gauge.labels(**labels)._value.get()
    return gauge._value.get()


# ---------------------------------------------------------------------------
# Metric Registration Tests
# ---------------------------------------------------------------------------


class TestMetricRegistration:
    """All 6 metric types are registered with correct names and labels."""

    def test_render_jobs_total_registered(self) -> None:
        """render_jobs_total Counter is registered."""
        # prometheus_client strips _total suffix from Counter._name
        assert render_jobs_total._name == "stoat_ferret_render_jobs"

    def test_render_duration_seconds_registered(self) -> None:
        """render_duration_seconds Histogram is registered."""
        assert render_duration_seconds._name == "stoat_ferret_render_duration_seconds"

    def test_render_speed_ratio_registered(self) -> None:
        """render_speed_ratio Gauge is registered."""
        assert render_speed_ratio._name == "stoat_ferret_render_speed_ratio"

    def test_render_queue_depth_registered(self) -> None:
        """render_queue_depth Gauge is registered."""
        assert render_queue_depth._name == "stoat_ferret_render_queue_depth"

    def test_render_encoder_active_registered(self) -> None:
        """render_encoder_active Gauge is registered with encoder_name label."""
        assert render_encoder_active._name == "stoat_ferret_render_encoder_active"
        assert "encoder_name" in render_encoder_active._labelnames

    def test_render_disk_usage_bytes_registered(self) -> None:
        """render_disk_usage_bytes Gauge is registered."""
        assert render_disk_usage_bytes._name == "stoat_ferret_render_disk_usage_bytes"

    def test_render_jobs_total_has_status_label(self) -> None:
        """render_jobs_total has a 'status' label."""
        assert "status" in render_jobs_total._labelnames

    def test_render_duration_seconds_has_correct_buckets(self) -> None:
        """render_duration_seconds has the specified bucket boundaries."""
        expected = [10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0, float("inf")]
        assert list(render_duration_seconds._upper_bounds) == expected


# ---------------------------------------------------------------------------
# Counter Tests — Job State Transitions
# ---------------------------------------------------------------------------


class TestJobCounters:
    """Counter increments on job state transitions."""

    async def test_counter_increments_on_completion(self) -> None:
        """render_jobs_total(status=completed) increments on successful completion."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            before = _get_counter_value(render_jobs_total, {"status": "completed"})

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

            after = _get_counter_value(render_jobs_total, {"status": "completed"})
            assert after == before + 1

    async def test_counter_increments_on_failure(self) -> None:
        """render_jobs_total(status=failed) increments on permanent failure."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service(
                settings=Settings(render_retry_count=0),
            )

            before = _get_counter_value(render_jobs_total, {"status": "failed"})

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

            after = _get_counter_value(render_jobs_total, {"status": "failed"})
            assert after == before + 1

    async def test_counter_increments_on_cancellation(self) -> None:
        """render_jobs_total(status=cancelled) increments on cancellation."""
        with _PATCH_NO_RUST:
            service, repo, ws, _ = _build_service()

            before = _get_counter_value(render_jobs_total, {"status": "cancelled"})

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await service.cancel_job(job.id)

            after = _get_counter_value(render_jobs_total, {"status": "cancelled"})
            assert after == before + 1


# ---------------------------------------------------------------------------
# Histogram Tests — Duration
# ---------------------------------------------------------------------------


class TestDurationHistogram:
    """Histogram observes render duration on completion."""

    async def test_duration_observed_on_completion(self) -> None:
        """render_duration_seconds observes elapsed time on successful completion."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()

            sample_before = REGISTRY.get_sample_value(
                "stoat_ferret_render_duration_seconds_count"
            ) or 0.0

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

            sample_after = REGISTRY.get_sample_value(
                "stoat_ferret_render_duration_seconds_count"
            ) or 0.0
            assert sample_after > sample_before


# ---------------------------------------------------------------------------
# Speed Ratio Tests
# ---------------------------------------------------------------------------


class TestSpeedRatio:
    """Speed ratio gauge updates during render progress."""

    def test_speed_ratio_updates(self) -> None:
        """render_speed_ratio updates based on progress and elapsed time."""
        executor = RenderExecutor()
        job_id = "test-job-1"
        # Simulate a 60s media file
        executor._job_start_times[job_id] = time.monotonic() - 2.0  # started 2s ago
        executor._job_durations_us[job_id] = 60_000_000  # 60s total

        # At 10% progress after 2s wall clock:
        # rendered = 60 * 0.1 = 6s, speed = 6/2 = 3.0x
        executor._update_speed_ratio(job_id, 0.1)
        value = _get_gauge_value(render_speed_ratio)
        assert value == pytest.approx(3.0, abs=0.5)

    def test_speed_ratio_no_update_at_zero_progress(self) -> None:
        """Speed ratio does not update when progress is 0."""
        executor = RenderExecutor()
        job_id = "test-job-2"
        executor._job_start_times[job_id] = time.monotonic() - 1.0
        executor._job_durations_us[job_id] = 60_000_000

        render_speed_ratio.set(0.0)
        executor._update_speed_ratio(job_id, 0.0)
        assert _get_gauge_value(render_speed_ratio) == 0.0


# ---------------------------------------------------------------------------
# Queue Depth Tests
# ---------------------------------------------------------------------------


class TestQueueDepth:
    """Queue depth gauge reflects enqueue/dequeue operations."""

    async def test_queue_depth_increases_on_enqueue(self) -> None:
        """render_queue_depth increases when a job is enqueued."""
        repo = InMemoryRenderRepository()
        queue = RenderQueue(repo, max_concurrent=4, max_depth=50)

        render_queue_depth.set(0)

        job = RenderJob.create(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan=_make_plan_json(),
        )
        await queue.enqueue(job)
        assert _get_gauge_value(render_queue_depth) == 1.0

    async def test_queue_depth_decreases_on_dequeue(self) -> None:
        """render_queue_depth decreases when a job is dequeued."""
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

        dequeued = await queue.dequeue()
        assert dequeued is not None
        assert _get_gauge_value(render_queue_depth) == 0.0


# ---------------------------------------------------------------------------
# Encoder Active Tests
# ---------------------------------------------------------------------------


class TestEncoderActive:
    """Encoder active gauge tracks in-use encoders."""

    def test_extract_encoder_name(self) -> None:
        """Extracts codec from render plan JSON."""
        job = RenderJob.create(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan=_make_plan_json(codec="h264_nvenc"),
        )
        name = RenderExecutor._extract_encoder_name(job)
        assert name == "h264_nvenc"

    def test_extract_encoder_name_invalid_json(self) -> None:
        """Returns 'unknown' for invalid render plan JSON."""
        job = RenderJob.create(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan="not json",
        )
        name = RenderExecutor._extract_encoder_name(job)
        assert name == "unknown"

    def test_extract_encoder_name_missing_codec(self) -> None:
        """Returns 'unknown' when codec is missing from settings."""
        job = RenderJob.create(
            project_id="proj-1",
            output_path="/tmp/out.mp4",
            output_format=OutputFormat.MP4,
            quality_preset=QualityPreset.STANDARD,
            render_plan=json.dumps({"settings": {}}),
        )
        name = RenderExecutor._extract_encoder_name(job)
        assert name == "unknown"


# ---------------------------------------------------------------------------
# Disk Usage Tests
# ---------------------------------------------------------------------------


class TestDiskUsage:
    """Disk usage gauge reports correct values."""

    async def test_disk_usage_updated_on_completion(self) -> None:
        """render_disk_usage_bytes updates on job completion."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            render_disk_usage_bytes.set(0)

            mock_usage = MagicMock()
            mock_usage.used = 1_000_000_000  # 1GB used

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/tmp/renders/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]

            with (
                patch("stoat_ferret.render.service.shutil.disk_usage", return_value=mock_usage),
                patch("stoat_ferret.render.service.Path.exists", return_value=True),
            ):
                await service.run_job(job, ["ffmpeg"])

            assert _get_gauge_value(render_disk_usage_bytes) == 1_000_000_000

    async def test_disk_usage_handles_missing_dir(self) -> None:
        """Disk usage silently skips when output dir doesn't exist."""
        with _PATCH_NO_RUST:
            service, repo, ws, executor = _build_service()
            render_disk_usage_bytes.set(0)

            job = await service.submit_job(
                project_id="proj-1",
                output_path="/nonexistent/dir/out.mp4",
                output_format=OutputFormat.MP4,
                quality_preset=QualityPreset.STANDARD,
                render_plan_json=_make_plan_json(),
            )
            await repo.update_status(job.id, RenderStatus.RUNNING)
            executor.execute = AsyncMock(return_value=True)  # type: ignore[method-assign]

            # Should not raise — just skips
            await service.run_job(job, ["ffmpeg"])
            assert _get_gauge_value(render_disk_usage_bytes) == 0
