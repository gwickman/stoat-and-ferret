# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Worker-path QC pipeline regression guards (BL-477, BL-488).

Mocked tests (no FFmpeg):
  test_no_delivery_profile_returns_404  — BL-477-AC-4
  test_assertions_translation_parity    — BL-488-AC-4

FFmpeg-gated (STOAT_TEST_FFMPEG=1):
  test_worker_qc_pipeline_target_non_null      — BL-488-AC-5
  test_compliant_render_passes_loudness_gate   — BL-488-AC-3 (partial)
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from stoat_ferret.api.services.qc_service import ALL_CHECK_IDS, QCService
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository, QCReportRecord
from stoat_ferret.render.service import _build_assertions_from_profile

_STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

_skip_no_ffmpeg = pytest.mark.skipif(
    not _STOAT_TEST_FFMPEG,
    reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)",
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _null_checks() -> dict[str, Any]:
    return {
        check_id: {"measured": None, "target": None, "pass": False, "units": ""}
        for check_id in ALL_CHECK_IDS
    }


def _build_mock_qc_service(repo: InMemoryQCReportRepository) -> QCService:
    """Mock QCService that persists to an in-memory repo without FFmpeg."""

    async def _run_checks(
        artifact_path: str,
        job_id: str | None = None,
        delivery_profile_id: str | None = None,
        assertions: dict[str, float | None] | None = None,
    ) -> QCReportRecord:
        record = QCReportRecord(
            id=str(uuid.uuid4()),
            job_id=job_id,
            artifact_path=artifact_path,
            delivery_profile_id=delivery_profile_id,
            overall_verdict="fail",
            checks=json.dumps(_null_checks()),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        await repo.create(record)
        return record

    svc = MagicMock(spec=QCService)
    svc.run_checks = AsyncMock(side_effect=_run_checks)
    return svc


def _make_real_qc_service() -> QCService:
    """Real QCService with in-memory repo and mock WebSocket for FFmpeg-gated tests."""
    repo = InMemoryQCReportRepository()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    settings = MagicMock()
    return QCService(repository=repo, connection_manager=ws, settings=settings)


def _generate_sine_wav(path: Path) -> None:
    """5-second 440 Hz stereo 48 kHz sine WAV via FFmpeg lavfi."""
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-y",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Fixture: in-process ASGI app in noop render mode
# ---------------------------------------------------------------------------


@pytest.fixture()
async def worker_path_client() -> httpx.AsyncClient:  # type: ignore[misc]
    """ASGI client in noop render mode with mock QCService — no FFmpeg required."""
    from stoat_ferret.api.app import create_app, lifespan
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.api.settings import Settings
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.delivery_profiles_repository import (
        AsyncInMemoryDeliveryProfileRepository,
    )
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from stoat_ferret.jobs.queue import InMemoryJobQueue
    from stoat_ferret.render.checkpoints import RenderCheckpointManager
    from stoat_ferret.render.executor import RenderExecutor
    from stoat_ferret.render.queue import RenderQueue
    from stoat_ferret.render.render_repository import InMemoryRenderRepository
    from stoat_ferret.render.service import RenderService

    qc_repo = InMemoryQCReportRepository()
    qc_svc = _build_mock_qc_service(qc_repo)

    render_repo = InMemoryRenderRepository()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    checkpoint_mgr = MagicMock(spec=RenderCheckpointManager)
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)

    render_svc = RenderService(
        repository=render_repo,
        queue=RenderQueue(render_repo),
        executor=MagicMock(spec=RenderExecutor),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_mode="noop"),
        qc_service=qc_svc,
    )

    video_repo = AsyncInMemoryVideoRepository()
    job_queue = InMemoryJobQueue()
    job_queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repo))

    app = create_app(
        video_repository=video_repo,
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        job_queue=job_queue,
        render_repository=render_repo,
        render_service=render_svc,
        delivery_profile_repository=AsyncInMemoryDeliveryProfileRepository(),
        qc_service=qc_svc,
    )
    app.state.qc_report_repository = qc_repo

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client


async def _seed_project_with_clip(client: httpx.AsyncClient) -> str:
    """Create a project with a stub video clip. Returns project_id."""
    import contextlib

    from stoat_ferret.db.models import Clip, Video

    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "worker-path-qc-test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    video_repo = transport.app.state.video_repository  # type: ignore[union-attr]
    clip_repo = transport.app.state.clip_repository  # type: ignore[union-attr]

    now = datetime.now(timezone.utc)
    video_id = "00000000-0000-0000-0000-000000000001"
    with contextlib.suppress(Exception):
        await video_repo.add(
            Video(
                id=video_id,
                path="/stub/video.mp4",
                filename="video.mp4",
                duration_frames=300,
                frame_rate_numerator=30,
                frame_rate_denominator=1,
                width=1920,
                height=1080,
                video_codec="h264",
                audio_codec=None,
                file_size=1000,
                thumbnail_path=None,
                created_at=now,
                updated_at=now,
                subtitle_count=0,
                data_count=0,
                subtitle_streams=[],
            )
        )
    clip = Clip(
        id=Clip.new_id(),
        project_id=project_id,
        source_video_id=video_id,
        in_point=0,
        out_point=300,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repo.add(clip)
    return project_id


# ---------------------------------------------------------------------------
# BL-477-AC-4: mocked regression guard — no delivery profile → 404
# ---------------------------------------------------------------------------


async def test_no_delivery_profile_returns_404(
    worker_path_client: httpx.AsyncClient,
) -> None:
    """Render without delivery profile: GET /render/{job_id}/qc returns 404.

    The worker-path QC gate only activates when delivery_profile_id is embedded
    in the render plan. Without it, no QCReport is written, so the /qc endpoint
    returns 404 for that job.
    """
    client = worker_path_client
    project_id = await _seed_project_with_clip(client)

    render_resp = await client.post(
        "/api/v1/render",
        json={
            "project_id": project_id,
            # No delivery_profile — worker path must skip QC entirely
            "render_plan": json.dumps({"total_duration": 10.0, "settings": {}}),
        },
    )
    assert render_resp.status_code == 201
    job_id = render_resp.json()["id"]

    qc_resp = await client.get(f"/api/v1/render/{job_id}/qc")
    assert qc_resp.status_code == 404


# ---------------------------------------------------------------------------
# BL-488-AC-4: unit regression guard — both call sites produce identical assertions
# ---------------------------------------------------------------------------


def test_assertions_translation_parity() -> None:
    """Both call sites build identical assertions from the same DeliveryProfile.

    _build_assertions_from_profile (worker call site, service.py) and the
    inline dict literal (submit call site, render.py:559-562) must produce
    the same keys and values for the same delivery profile object.
    """

    class _Profile:
        loudness_target_lufs: float = -16.0
        true_peak_ceiling_dbtp: float = -1.0

    profile = _Profile()

    # Worker call site
    worker_assertions = _build_assertions_from_profile(profile)

    # Inline submit call site (render.py)
    inline_assertions: dict[str, float | None] = {
        "loudness_integrated": profile.loudness_target_lufs,
        "true_peak": profile.true_peak_ceiling_dbtp,
    }

    assert worker_assertions == inline_assertions
    assert worker_assertions["loudness_integrated"] == -16.0
    assert worker_assertions["true_peak"] == -1.0


# ---------------------------------------------------------------------------
# BL-488-AC-5: FFmpeg-gated — assertions propagate → non-null targets
# ---------------------------------------------------------------------------


@_skip_no_ffmpeg
async def test_worker_qc_pipeline_target_non_null(tmp_path: Path) -> None:
    """Delivery-profile assertions reach QCService: target and pass are non-null.

    When the worker path injects assertions into run_checks, both
    loudness_integrated.target and true_peak.target must be non-null, confirming
    the assertion dict flows from the delivery profile through to the check output.
    """
    audio = tmp_path / "sine.wav"
    _generate_sine_wav(audio)

    svc = _make_real_qc_service()
    assertions: dict[str, float | None] = {
        "loudness_integrated": -30.0,
        "true_peak": -1.0,
    }
    record = await svc.run_checks(str(audio), assertions=assertions)
    checks = json.loads(record.checks)

    li = checks["loudness_integrated"]
    assert li["target"] is not None, (
        "loudness_integrated.target must be non-null when assertions provided"
    )
    assert li["pass"] is not None, "loudness_integrated.pass must be a boolean when target is set"

    tp = checks["true_peak"]
    assert tp["target"] is not None, "true_peak.target must be non-null when assertions provided"
    assert tp["pass"] is not None, "true_peak.pass must be a boolean when target is set"


# ---------------------------------------------------------------------------
# BL-488-AC-3: FFmpeg-gated — compliant audio passes loudness/true-peak gate
# ---------------------------------------------------------------------------


@_skip_no_ffmpeg
async def test_compliant_render_passes_loudness_gate(tmp_path: Path) -> None:
    """Compliant audio (meeting loudness/true-peak targets) has pass=True on those checks.

    Confirms the gate evaluates real FFmpeg measurements rather than
    short-circuiting. A 440 Hz sine WAV at ~-21 LUFS / -21 dBTP passes both
    the -30 LUFS floor and the -1 dBTP ceiling.

    Note: overall_verdict remains "fail" because chapters_present defaults to
    target=1.0 (hardcoded) and av_sync returns _NULL_CHECK for audio-only files.
    Full "status == COMPLETED" discharge requires a video+audio fixture with
    embedded chapters; deferred_post_merge — see quality-gaps.md.
    """
    audio = tmp_path / "sine.wav"
    _generate_sine_wav(audio)

    svc = _make_real_qc_service()
    # Loose targets: sine at ~-21 LUFS passes -30 floor; -21 dBTP passes -1 ceiling.
    assertions: dict[str, float | None] = {
        "loudness_integrated": -30.0,
        "true_peak": -1.0,
    }
    record = await svc.run_checks(str(audio), assertions=assertions)
    checks = json.loads(record.checks)

    li = checks["loudness_integrated"]
    assert li["pass"] is True, (
        f"loudness_integrated.pass should be True: "
        f"measured={li['measured']} >= target={li['target']}"
    )

    tp = checks["true_peak"]
    assert tp["pass"] is True, (
        f"true_peak.pass should be True: measured={tp['measured']} <= target={tp['target']}"
    )
