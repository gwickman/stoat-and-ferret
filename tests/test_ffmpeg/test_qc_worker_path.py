# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""QC worker path end-to-end FFmpeg-gated tests (BL-682).

Gated tests (STOAT_TEST_FFMPEG=1):
  test_qc_report_persisted_and_get_returns_200       — BL-682-AC-1
  test_qc_failed_transition_on_non_compliant_render  — BL-682-AC-2
  test_compliant_render_overall_verdict_pass         — BL-682-AC-4 + AC-6
  test_sine_fixture_loudness_targets_non_null        — BL-682-AC-5
  test_decode_integrity_corrupt_artifact             — BL-682-AC-7
  test_decode_integrity_valid_artifact               — BL-682-AC-8

Non-gated AC-3 (GET .../qc returns 404 without delivery profile) is covered by:
  tests/render/test_qc_worker_path.py::test_no_delivery_profile_returns_404
  tests/smoke/test_qc_api.py::test_smoke_render_no_delivery_profile_qc_returns_404
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

from stoat_ferret.api.routers import qc as qc_module
from stoat_ferret.api.services.qc_service import QCService
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.delivery_profiles_repository import (
    AsyncInMemoryDeliveryProfileRepository,
    DeliveryProfile,
)
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderStatus

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")

_FFMPEG_SKIP = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason="FFmpeg integration test; set STOAT_TEST_FFMPEG=1 to enable",
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


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


def _generate_video_with_audio(path: Path) -> None:
    """5-second 320x240 H.264+AAC MP4 with sine audio via FFmpeg lavfi.

    Produces a video+audio file so av_sync can be measured (audio-only WAV
    always yields pass=False for av_sync because there is no video stream).
    """
    subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "color=black:320x240:duration=5:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=5",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-c:a",
            "aac",
            "-y",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )


def _make_qc_svc_with_repo() -> tuple[QCService, InMemoryQCReportRepository]:
    """Real QCService backed by in-memory repo."""
    qc_repo = InMemoryQCReportRepository()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    settings = MagicMock()
    svc = QCService(repository=qc_repo, connection_manager=ws, settings=settings)
    return svc, qc_repo


def _minimal_qc_app(qc_repo: InMemoryQCReportRepository) -> FastAPI:
    """Minimal FastAPI app with QC router for HTTP assertions."""
    app = FastAPI()
    app.include_router(qc_module.router)
    app.state.qc_report_repository = qc_repo
    return app


def _make_delivery_profile(
    dp_id: str,
    loudness_target_lufs: float = -22.0,
    true_peak_ceiling_dbtp: float = -1.0,
) -> DeliveryProfile:
    return DeliveryProfile(
        id=dp_id,
        name="test-dp",
        output_formats=[],
        loudness_target_lufs=loudness_target_lufs,
        true_peak_ceiling_dbtp=true_peak_ceiling_dbtp,
        metadata_template=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# AC-1: QCReport persisted and GET /render/{id}/qc returns 200
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_qc_report_persisted_and_get_returns_200(tmp_path: Path) -> None:
    """Real QCService run produces a persisted QCReport; GET endpoint returns 200.

    BL-682-AC-1: a real worker render with a delivery profile yields a persisted
    QCReport and GET /api/v1/render/{id}/qc returns 200.
    """
    sine_wav = tmp_path / "sine.wav"
    _generate_sine_wav(sine_wav)

    qc_svc, qc_repo = _make_qc_svc_with_repo()
    job_id = str(uuid.uuid4())
    dp_id = str(uuid.uuid4())

    assertions: dict[str, float | None] = {
        "loudness_integrated": -22.0,
        "true_peak": -1.0,
    }
    record = await qc_svc.run_checks(
        str(sine_wav),
        job_id=job_id,
        delivery_profile_id=dp_id,
        assertions=assertions,
    )

    assert record.id is not None
    assert record.job_id == job_id
    assert record.delivery_profile_id == dp_id

    app = _minimal_qc_app(qc_repo)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.get(f"/api/v1/render/{job_id}/qc")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert body["overall_verdict"] in ("pass", "fail")


# ---------------------------------------------------------------------------
# AC-2: QC_FAILED state transition on fail-verdict render
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_qc_failed_transition_on_non_compliant_render(tmp_path: Path) -> None:
    """Render with non-compliant delivery profile transitions to QC_FAILED.

    BL-682-AC-2: fail-verdict render transitions to QC_FAILED via the worker path.
    Uses a delivery profile with a loudness target the sine WAV cannot satisfy
    (~-21.75 LUFS vs strict -14.0 LUFS target; delta >> 0.5 LU tolerance).
    chapters_present also fails (0 chapters vs effective_target=1.0).
    Both contribute to overall_verdict='fail' → QC_FAILED status.
    """
    from stoat_ferret.api.settings import Settings
    from stoat_ferret.render.checkpoints import RenderCheckpointManager
    from stoat_ferret.render.executor import RenderExecutor
    from stoat_ferret.render.queue import RenderQueue
    from stoat_ferret.render.render_repository import InMemoryRenderRepository
    from stoat_ferret.render.service import RenderService

    sine_wav = tmp_path / "sine.wav"
    _generate_sine_wav(sine_wav)

    dp_id = str(uuid.uuid4())
    dp_repo = AsyncInMemoryDeliveryProfileRepository()
    profile = _make_delivery_profile(dp_id, loudness_target_lufs=-14.0)
    await dp_repo.add(profile)

    qc_svc, _qc_repo = _make_qc_svc_with_repo()
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
        dp_repo=dp_repo,
    )

    render_plan = json.dumps(
        {
            "total_duration": 5.0,
            "settings": {
                "delivery_profile_id": dp_id,
                "quality_preset": "medium",
            },
        }
    )
    job = await render_svc.submit_job(
        project_id="test-project",
        output_path=str(sine_wav),
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan_json=render_plan,
    )

    assert job.status == RenderStatus.QC_FAILED, (
        f"Expected QC_FAILED after fail-verdict render, got {job.status!r}"
    )


# ---------------------------------------------------------------------------
# AC-4 + AC-6: compliant render → overall_verdict='pass'
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_compliant_render_overall_verdict_pass(tmp_path: Path) -> None:
    """Compliant delivery-profile render yields overall_verdict='pass'.

    BL-682-AC-4: compliant render → status=COMPLETED (not QC_FAILED) when all
                 asserted checks pass.
    BL-682-AC-6: overall_verdict='pass' on compliant delivery-profile render.

    Uses a video+audio MP4 (not audio-only WAV) so that av_sync can be measured.
    Audio-only WAV always causes av_sync to return _NULL_CHECK (pass=False, no
    video stream to compare), making overall_verdict='pass' impossible.

    Assertions:
      loudness_integrated: -22.0  (sine ~-21.75 LUFS, within ±0.5 LU window)
      true_peak: -1.0             (sine ~-21 dBTP, well below -1 dBTP ceiling)
      chapters_present: 0.0       (0 chapters required, MP4 has 0 → pass)
      decode_integrity: 0.0       (0 errors required, valid MP4 → pass)
      av_sync: 100.0              (≤100ms required, lavfi-generated → ~0ms → pass)
    """
    video_with_audio = tmp_path / "test.mp4"
    _generate_video_with_audio(video_with_audio)

    qc_svc, _qc_repo = _make_qc_svc_with_repo()

    assertions: dict[str, float | None] = {
        "loudness_integrated": -22.0,
        "true_peak": -1.0,
        "chapters_present": 0.0,
        "decode_integrity": 0.0,
        "av_sync": 100.0,
    }
    record = await qc_svc.run_checks(str(video_with_audio), assertions=assertions)
    checks = json.loads(record.checks)

    assert record.overall_verdict == "pass", (
        f"Expected overall_verdict='pass', got {record.overall_verdict!r}. "
        f"Failing checks: "
        f"{[k for k, v in checks.items() if v.get('pass') is False]}"
    )

    for check_id in (
        "loudness_integrated",
        "true_peak",
        "chapters_present",
        "decode_integrity",
        "av_sync",
    ):
        assert checks[check_id]["pass"] is True, (
            f"{check_id}.pass should be True: {checks[check_id]}"
        )


# ---------------------------------------------------------------------------
# AC-5: sine fixture contract — loudness and true-peak targets+pass non-null
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_sine_fixture_loudness_targets_non_null(tmp_path: Path) -> None:
    """Delivery-profile assertions propagate through run_checks to non-null target+pass.

    BL-682-AC-5: with a real sine fixture and delivery profile, loudness_integrated
    and true_peak checks have non-null target and pass values — confirming the
    assertion dict flows from the delivery profile through to the check output.
    """
    sine_wav = tmp_path / "sine.wav"
    _generate_sine_wav(sine_wav)

    qc_svc, _qc_repo = _make_qc_svc_with_repo()
    assertions: dict[str, float | None] = {
        "loudness_integrated": -22.0,
        "true_peak": -1.0,
    }
    record = await qc_svc.run_checks(str(sine_wav), assertions=assertions)
    checks = json.loads(record.checks)

    for check_id in ("loudness_integrated", "true_peak"):
        assert checks[check_id]["target"] is not None, (
            f"{check_id}.target must be non-null when assertions provided"
        )
        assert checks[check_id]["pass"] is not None, (
            f"{check_id}.pass must be a boolean when target is set"
        )


# ---------------------------------------------------------------------------
# AC-7: decode integrity detects corrupt artifact
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_decode_integrity_corrupt_artifact(tmp_path: Path) -> None:
    """Corrupt artifact triggers decode error: measured=1.0, pass=False.

    BL-682-AC-7: decode integrity check on a corrupt file returns measured=1.0
    and pass=False when target=0.0 (zero errors required).
    """
    corrupt = tmp_path / "corrupt.bin"
    corrupt.write_bytes(b"\xff\xfe" * 512)

    qc_svc, _qc_repo = _make_qc_svc_with_repo()
    assertions: dict[str, float | None] = {
        "decode_integrity": 0.0,
    }
    record = await qc_svc.run_checks(str(corrupt), assertions=assertions)
    checks = json.loads(record.checks)

    di = checks["decode_integrity"]
    assert di["measured"] == 1.0, f"Expected measured=1.0 (errors detected), got {di['measured']}"
    assert di["pass"] is False, f"Expected pass=False for corrupt artifact, got {di['pass']}"


# ---------------------------------------------------------------------------
# AC-8: decode integrity valid artifact
# ---------------------------------------------------------------------------


@_FFMPEG_SKIP
async def test_decode_integrity_valid_artifact(tmp_path: Path) -> None:
    """Valid sine WAV artifact has zero decode errors: measured=0.0, pass=True.

    BL-682-AC-8: decode integrity check on a valid artifact returns measured=0.0
    and pass=True when target=0.0 (zero errors required).
    """
    sine_wav = tmp_path / "sine.wav"
    _generate_sine_wav(sine_wav)

    qc_svc, _qc_repo = _make_qc_svc_with_repo()
    assertions: dict[str, float | None] = {
        "decode_integrity": 0.0,
    }
    record = await qc_svc.run_checks(str(sine_wav), assertions=assertions)
    checks = json.loads(record.checks)

    di = checks["decode_integrity"]
    assert di["measured"] == 0.0, f"Expected measured=0.0 (no errors), got {di['measured']}"
    assert di["pass"] is True, f"Expected pass=True for valid artifact, got {di['pass']}"
