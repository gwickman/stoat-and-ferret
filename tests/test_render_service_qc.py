"""Unit tests for RenderService worker-path QC integration (BL-477, BL-488).

Tests that _complete_job() invokes QCService when delivery_profile_id is
present in render_plan settings, handles exceptions gracefully, and
transitions to QC_FAILED on a fail verdict.

BL-488 tests verify that delivery-profile assertions (loudness/true-peak
targets) are built from the profile and passed to run_checks so that
target and pass values are computed.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.service import RenderService

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

_JOB_ID = "job-qc-001"
_OUTPUT_PATH = "/renders/output.mp4"
_PROFILE_ID = "profile-uuid-abc"


def _make_render_plan(*, with_profile: bool = True) -> str:
    settings: dict = {
        "output_format": "mp4",
        "width": 1920,
        "height": 1080,
        "codec": "libx264",
        "quality_preset": "medium",
        "fps": 30.0,
    }
    if with_profile:
        settings["delivery_profile_id"] = _PROFILE_ID
    return json.dumps({"total_duration": 60.0, "settings": settings})


def _make_job(*, with_profile: bool = True) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id=_JOB_ID,
        project_id="proj-001",
        status=RenderStatus.RUNNING,
        output_path=_OUTPUT_PATH,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_render_plan(with_profile=with_profile),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_qc_report(*, verdict: str = "pass") -> MagicMock:
    report = MagicMock()
    report.overall_verdict = verdict
    return report


def _make_profile(
    *,
    loudness_target_lufs: float = -16.0,
    true_peak_ceiling_dbtp: float = -1.0,
) -> MagicMock:
    """Create a mock DeliveryProfile with the given targets."""
    profile = MagicMock()
    profile.loudness_target_lufs = loudness_target_lufs
    profile.true_peak_ceiling_dbtp = true_peak_ceiling_dbtp
    return profile


def _make_service(
    *, qc_service: object | None = None, dp_repo: object | None = None
) -> RenderService:
    """Build a RenderService with all dependencies mocked."""
    repo = AsyncMock()
    repo.update_status = AsyncMock()

    queue = MagicMock()
    queue.get_active_count = AsyncMock(return_value=0)
    queue.get_queue_depth = AsyncMock(return_value=0)
    queue._max_concurrent = 2
    queue._max_depth = 10

    executor = MagicMock()
    executor._cleanup_temp_files = MagicMock()

    checkpoint_manager = AsyncMock()
    checkpoint_manager.cleanup_stale = AsyncMock()

    ws = AsyncMock()
    ws.broadcast = AsyncMock()

    settings = MagicMock()
    settings.render_retry_count = 3
    settings.render_mode = "real"

    return RenderService(
        repository=repo,
        queue=queue,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        connection_manager=ws,
        settings=settings,
        qc_service=qc_service,  # type: ignore[arg-type]
        dp_repo=dp_repo,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkerPathQC:
    """RenderService._complete_job() QC wiring."""

    async def test_qc_called_when_delivery_profile_present(self) -> None:
        """AC-001-1 / BL-477-AC-1: run_checks called with delivery_profile_id from settings."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(return_value=_make_qc_report(verdict="pass"))

        service = _make_service(qc_service=qc_service)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        qc_service.run_checks.assert_awaited_once()
        call_kwargs = qc_service.run_checks.call_args.kwargs
        assert call_kwargs["delivery_profile_id"] == _PROFILE_ID
        assert call_kwargs["job_id"] == _JOB_ID
        assert call_kwargs["artifact_path"] == _OUTPUT_PATH

    async def test_qc_not_called_without_delivery_profile(self) -> None:
        """AC-004-1 / BL-477-AC-4: run_checks NOT called when no delivery_profile_id in settings."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock()

        service = _make_service(qc_service=qc_service)
        job = _make_job(with_profile=False)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        qc_service.run_checks.assert_not_awaited()

    async def test_qc_not_called_when_qc_service_is_none(self) -> None:
        """Backward compat: no qc_service → no QC, job stays COMPLETED."""
        service = _make_service(qc_service=None)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        statuses = [c.args[1] for c in service._repo.update_status.call_args_list]
        assert RenderStatus.QC_FAILED not in statuses
        assert RenderStatus.COMPLETED in statuses

    async def test_qc_fail_transitions_to_qc_failed(self) -> None:
        """AC-002-1 / BL-477-AC-2: fail verdict triggers COMPLETED→QC_FAILED transition."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(return_value=_make_qc_report(verdict="fail"))

        service = _make_service(qc_service=qc_service)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        statuses = [c.args[1] for c in service._repo.update_status.call_args_list]
        assert RenderStatus.COMPLETED in statuses
        assert RenderStatus.QC_FAILED in statuses
        # COMPLETED must come before QC_FAILED
        completed_idx = statuses.index(RenderStatus.COMPLETED)
        qc_failed_idx = statuses.index(RenderStatus.QC_FAILED)
        assert completed_idx < qc_failed_idx

    async def test_qc_pass_job_stays_completed(self) -> None:
        """Pass verdict: job stays COMPLETED, no QC_FAILED transition."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(return_value=_make_qc_report(verdict="pass"))

        service = _make_service(qc_service=qc_service)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        statuses = [c.args[1] for c in service._repo.update_status.call_args_list]
        assert RenderStatus.QC_FAILED not in statuses
        assert RenderStatus.COMPLETED in statuses

    async def test_qc_exception_job_stays_completed(self) -> None:
        """NFR-001: QC exception must not block job completion — job stays COMPLETED."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(side_effect=Exception("QC crashed"))

        service = _make_service(qc_service=qc_service)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            # Must not raise
            await service._complete_job(job)

        statuses = [c.args[1] for c in service._repo.update_status.call_args_list]
        assert RenderStatus.QC_FAILED not in statuses
        assert RenderStatus.COMPLETED in statuses

    async def test_qc_service_filenotfounderror_swallowed(self) -> None:
        """NFR-001: FileNotFoundError from QCService is swallowed — worker resilience."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(
            side_effect=FileNotFoundError("artifact not found at path: ...")
        )

        service = _make_service(qc_service=qc_service)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        statuses = [c.args[1] for c in service._repo.update_status.call_args_list]
        assert RenderStatus.QC_FAILED not in statuses


class TestWorkerPathQCAssertions:
    """BL-488: _complete_job() builds delivery-profile assertions before run_checks."""

    async def test_assertions_populated_from_profile(self) -> None:
        """BL-488-AC-1/2: Worker path fetches profile and passes assertions to run_checks."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(return_value=_make_qc_report(verdict="pass"))

        dp_repo = AsyncMock()
        dp_repo.get_by_id = AsyncMock(
            return_value=_make_profile(loudness_target_lufs=-16.0, true_peak_ceiling_dbtp=-1.0)
        )

        service = _make_service(qc_service=qc_service, dp_repo=dp_repo)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        dp_repo.get_by_id.assert_awaited_once_with(_PROFILE_ID)
        qc_service.run_checks.assert_awaited_once()
        call_kwargs = qc_service.run_checks.call_args.kwargs
        assert call_kwargs["assertions"] is not None
        assert call_kwargs["assertions"]["loudness_integrated"] == -16.0
        assert call_kwargs["assertions"]["true_peak"] == -1.0

    async def test_assertions_none_when_profile_not_found(self) -> None:
        """BL-488 guard: dp_repo.get_by_id returns None → assertions=None, run_checks called."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(return_value=_make_qc_report(verdict="pass"))

        dp_repo = AsyncMock()
        dp_repo.get_by_id = AsyncMock(return_value=None)

        service = _make_service(qc_service=qc_service, dp_repo=dp_repo)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        qc_service.run_checks.assert_awaited_once()
        call_kwargs = qc_service.run_checks.call_args.kwargs
        assert call_kwargs["assertions"] is None

    async def test_assertions_none_when_dp_repo_raises(self) -> None:
        """BL-488 guard: dp_repo.get_by_id raises → assertions=None, run_checks still called."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(return_value=_make_qc_report(verdict="pass"))

        dp_repo = AsyncMock()
        dp_repo.get_by_id = AsyncMock(side_effect=Exception("db error"))

        service = _make_service(qc_service=qc_service, dp_repo=dp_repo)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        qc_service.run_checks.assert_awaited_once()
        call_kwargs = qc_service.run_checks.call_args.kwargs
        assert call_kwargs["assertions"] is None

    async def test_assertions_none_when_dp_repo_not_injected(self) -> None:
        """BL-488 guard: dp_repo=None (not wired) → assertions=None, run_checks still called."""
        qc_service = AsyncMock()
        qc_service.run_checks = AsyncMock(return_value=_make_qc_report(verdict="pass"))

        service = _make_service(qc_service=qc_service, dp_repo=None)
        job = _make_job(with_profile=True)

        with (
            patch("stoat_ferret.render.service.render_jobs_total"),
            patch("stoat_ferret.render.service.render_duration_seconds"),
            patch("stoat_ferret.render.service.render_disk_usage_bytes"),
        ):
            await service._complete_job(job)

        qc_service.run_checks.assert_awaited_once()
        call_kwargs = qc_service.run_checks.call_args.kwargs
        assert call_kwargs["assertions"] is None

    async def test_inline_path_assertions_unchanged(self) -> None:
        """BL-488-AC-4: Inline submit path assertions in render.py:538-545 not regressed.

        The inline path is comprehensively tested in
        tests/test_delivery_profiles.py::test_render_with_delivery_profile_triggers_qc.
        This test guards that the inline path source was not modified.
        """
        import inspect

        from stoat_ferret.api.routers import render as render_router

        source = inspect.getsource(render_router)
        assert '"loudness_integrated": delivery_profile.loudness_target_lufs' in source
        assert '"true_peak": delivery_profile.true_peak_ceiling_dbtp' in source


@pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1); deferred_post_merge — BL-488-AC-5",
)
class TestWorkerQCContractFFmpeg:
    """BL-488-AC-5: FFmpeg-gated contract test — deferred_post_merge.

    Discharge: set STOAT_TEST_FFMPEG=1 and run:
        uv run pytest tests/test_render_service_qc.py::TestWorkerQCContractFFmpeg -v
    """

    async def test_qc_assertions_non_null_with_delivery_profile(self, tmp_path: Path) -> None:
        """BL-488-AC-5: QCService produces non-null target and pass with delivery assertions."""
        import asyncio

        from stoat_ferret.api.services.qc_service import QCService
        from stoat_ferret.api.websocket.manager import ConnectionManager
        from stoat_ferret.db.qc_repository import InMemoryQCReportRepository

        sine_path = tmp_path / "sine.wav"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(sine_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        assert proc.returncode == 0, "ffmpeg sine fixture generation failed"

        ws = MagicMock(spec=ConnectionManager)
        ws.broadcast = AsyncMock()
        repo = InMemoryQCReportRepository()
        settings = MagicMock()
        qc_service = QCService(repository=repo, connection_manager=ws, settings=settings)

        assertions = {"loudness_integrated": -16.0, "true_peak": -1.0}
        report = await qc_service.run_checks(
            artifact_path=str(sine_path),
            job_id="test-contract-job",
            delivery_profile_id="test-profile-001",
            assertions=assertions,
        )

        checks = json.loads(report.checks)
        loudness = checks["loudness_integrated"]
        true_peak = checks["true_peak"]
        assert loudness["target"] is not None, "loudness_integrated.target must be non-null"
        assert loudness["pass"] is not None, "loudness_integrated.pass must be non-null"
        assert true_peak["target"] is not None, "true_peak.target must be non-null"
        assert true_peak["pass"] is not None, "true_peak.pass must be non-null"
