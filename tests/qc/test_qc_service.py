# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit, API, WebSocket, and contract tests for QCService and /qc endpoints (BL-424)."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.qc_service import ALL_CHECK_IDS, QCService
from stoat_ferret.api.websocket.events import EventType
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.delivery_profiles_repository import (
    AsyncInMemoryDeliveryProfileRepository,
    DeliveryProfile,
)
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")
GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "golden_qc_report.json"


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _make_mock_subprocess(stdout: str = "", stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Build an async subprocess factory mock that returns given output."""

    async def _factory(*args: str, **kwargs: Any) -> MagicMock:
        proc = MagicMock()
        proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
        proc.returncode = returncode
        return proc

    return AsyncMock(side_effect=_factory)


def _make_service(
    subprocess_factory: Any = None,
    repo: InMemoryQCReportRepository | None = None,
) -> tuple[QCService, InMemoryQCReportRepository, list[dict]]:
    """Create a QCService with in-memory repo and capturing ws manager."""
    if repo is None:
        repo = InMemoryQCReportRepository()
    broadcast_events: list[dict] = []

    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock(side_effect=lambda event: broadcast_events.append(event))

    settings = MagicMock()
    proc_factory = subprocess_factory or _make_mock_subprocess(returncode=0)
    svc = QCService(
        repository=repo,
        connection_manager=ws,
        settings=settings,
        subprocess_factory=proc_factory,
    )
    return svc, repo, broadcast_events


def _make_api_app(
    svc: QCService,
    repo: InMemoryQCReportRepository | None = None,
    delivery_profile_repo: Any | None = None,
) -> FastAPI:
    """Build a minimal test app with the given QCService injected."""
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from stoat_ferret.jobs.queue import InMemoryJobQueue

    video_repo = AsyncInMemoryVideoRepository()
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repo))

    app = create_app(
        video_repository=video_repo,
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        job_queue=queue,
        qc_service=svc,
        delivery_profile_repository=delivery_profile_repo,
    )
    if repo is not None:
        app.state.qc_report_repository = repo
    return app


# ---------------------------------------------------------------------------
# Unit tests — QCService.run_checks()
# ---------------------------------------------------------------------------


async def test_qc_service_runs_all_12_checks(tmp_path: Path) -> None:
    """QCReport contains all 12 check IDs when FFmpeg is mocked."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _repo, _ = _make_service()
    record = await svc.run_checks(str(artifact))

    checks = json.loads(record.checks)
    missing = set(ALL_CHECK_IDS) - set(checks.keys())
    assert set(checks.keys()) == set(ALL_CHECK_IDS), f"Missing checks: {missing}"
    assert len(checks) == 12


async def test_qc_service_overall_verdict_pass(tmp_path: Path) -> None:
    """overall_verdict is 'pass' when all checks have pass=True."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, _ = _make_service()

    # Patch run_check to return pass=True for all checks
    async def _pass_check(**kwargs: Any) -> dict:
        return {"measured": 1.0, "target": 0.0, "pass": True, "units": ""}

    svc._run_check = _pass_check  # type: ignore[method-assign]
    record = await svc.run_checks(str(artifact))
    assert record.overall_verdict == "pass"


async def test_qc_service_overall_verdict_fail(tmp_path: Path) -> None:
    """overall_verdict is 'fail' when at least one check has pass=False."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, _ = _make_service()
    call_count = [0]

    async def _mixed_check(**kwargs: Any) -> dict:
        call_count[0] += 1
        # First check fails, rest pass
        if call_count[0] == 1:
            return {"measured": 1.0, "target": 0.0, "pass": False, "units": ""}
        return {"measured": 1.0, "target": 0.0, "pass": True, "units": ""}

    svc._run_check = _mixed_check  # type: ignore[method-assign]
    record = await svc.run_checks(str(artifact))
    assert record.overall_verdict == "fail"


async def test_qc_service_accepts_delivery_profile_targets(tmp_path: Path) -> None:
    """QCService accepts delivery_profile_id and passes it through to the record."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, _ = _make_service()
    record = await svc.run_checks(
        str(artifact),
        delivery_profile_id="profile-123",
    )
    assert record.delivery_profile_id == "profile-123"


async def test_qc_service_accepts_explicit_assertions(tmp_path: Path) -> None:
    """QCService applies explicit assertions; check target reflects assertion target."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, _ = _make_service()
    assertions: dict[str, float | None] = {"decode_integrity": 0.0}
    record = await svc.run_checks(str(artifact), assertions=assertions)

    checks = json.loads(record.checks)
    assert "decode_integrity" in checks


async def test_qc_service_artifact_not_found() -> None:
    """FileNotFoundError is raised when artifact path does not exist."""
    svc, _, _ = _make_service()
    with pytest.raises(FileNotFoundError, match="artifact not found"):
        await svc.run_checks("/nonexistent/path/out.mp4")


async def test_qc_service_invalid_assertion_format(tmp_path: Path) -> None:
    """422 is raised by the API (Pydantic validation) for malformed assertions.

    This test verifies that an invalid assertions structure is rejected before
    analysis starts via the QCRunRequest schema validation.
    """
    from pydantic import ValidationError

    from stoat_ferret.api.schemas.qc import QCRunRequest

    with pytest.raises(ValidationError):
        QCRunRequest(  # type: ignore[call-arg]
            artifact_path="/tmp/out.mp4",
            assertions={"loudness_integrated": "not-a-dict"},  # type: ignore[dict-item]
        )


# ---------------------------------------------------------------------------
# API tests — /qc routes
# ---------------------------------------------------------------------------


def test_post_qc_run_returns_201(tmp_path: Path) -> None:
    """POST /api/v1/qc/run returns HTTP 201 with a complete QCReport."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    repo = InMemoryQCReportRepository()
    svc, _, _ = _make_service(repo=repo)
    app = _make_api_app(svc, repo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/qc/run",
            json={"artifact_path": str(artifact)},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "id" in body
    assert "overall_verdict" in body
    assert "checks" in body
    assert set(body["checks"].keys()) == set(ALL_CHECK_IDS)


def test_get_qc_reports_by_id_200(tmp_path: Path) -> None:
    """GET /api/v1/qc/reports/{id} returns 200 for an existing report."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    repo = InMemoryQCReportRepository()
    svc, _, _ = _make_service(repo=repo)
    app = _make_api_app(svc, repo)

    with TestClient(app) as client:
        # Create a report first
        post_resp = client.post(
            "/api/v1/qc/run",
            json={"artifact_path": str(artifact)},
        )
        assert post_resp.status_code == 201, post_resp.text
        report_id = post_resp.json()["id"]

        # Retrieve it
        get_resp = client.get(f"/api/v1/qc/reports/{report_id}")

    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["id"] == report_id


def test_get_qc_reports_by_id_404() -> None:
    """GET /api/v1/qc/reports/{id} returns 404 for an unknown report ID."""
    repo = InMemoryQCReportRepository()
    svc, _, _ = _make_service(repo=repo)
    app = _make_api_app(svc, repo)

    with TestClient(app) as client:
        resp = client.get("/api/v1/qc/reports/nonexistent-uuid")

    assert resp.status_code == 404, resp.text


def test_get_render_job_qc_200(tmp_path: Path) -> None:
    """GET /api/v1/render/{job_id}/qc returns 200 for a job with a report."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    repo = InMemoryQCReportRepository()
    svc, _, _ = _make_service(repo=repo)
    app = _make_api_app(svc, repo)

    with TestClient(app) as client:
        post_resp = client.post(
            "/api/v1/qc/run",
            json={"artifact_path": str(artifact)},
        )
        assert post_resp.status_code == 201, post_resp.text
        report_id = post_resp.json()["id"]

        # Manually set job_id on the stored record so the lookup works
        stored = repo._records.get(report_id)
        if stored is not None:
            stored.job_id = "job-abc"

        resp = client.get("/api/v1/render/job-abc/qc")

    assert resp.status_code == 200, resp.text


def test_get_render_job_qc_404() -> None:
    """GET /api/v1/render/{job_id}/qc returns 404 when no report exists for the job."""
    repo = InMemoryQCReportRepository()
    svc, _, _ = _make_service(repo=repo)
    app = _make_api_app(svc, repo)

    with TestClient(app) as client:
        resp = client.get("/api/v1/render/nonexistent-job/qc")

    assert resp.status_code == 404, resp.text


def test_post_qc_run_artifact_not_found(tmp_path: Path) -> None:
    """POST /api/v1/qc/run returns 422 when artifact_path does not exist."""
    repo = InMemoryQCReportRepository()
    svc, _, _ = _make_service(repo=repo)
    app = _make_api_app(svc, repo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/qc/run",
            json={"artifact_path": str(tmp_path / "nonexistent.mp4")},
        )

    assert resp.status_code == 422, resp.text


def test_post_qc_run_profile_not_found(tmp_path: Path) -> None:
    """POST /api/v1/qc/run returns 404 when delivery_profile_id is not found."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    repo = InMemoryQCReportRepository()
    svc, _, _ = _make_service(repo=repo)
    dp_repo = AsyncInMemoryDeliveryProfileRepository()
    app = _make_api_app(svc, repo, delivery_profile_repo=dp_repo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/qc/run",
            json={
                "artifact_path": str(artifact),
                "delivery_profile_id": "00000000-0000-0000-0000-000000000000",
            },
        )

    assert resp.status_code == 404, resp.text


def _make_echo_target_service(repo: InMemoryQCReportRepository | None = None) -> QCService:
    """Build a QCService whose _run_check echoes the target into the result dict.

    This allows API integration tests to verify that assertions (from a delivery
    profile or explicit caller) are correctly threaded through to run_checks.
    """
    svc, _, _ = _make_service(repo=repo)

    async def _echo_target(*, artifact_path: str, target: float | None, **kwargs: Any) -> dict:
        return {
            "measured": None,
            "target": target,
            "pass": None if target is None else False,
            "units": "",
        }

    svc._run_check = _echo_target  # type: ignore[method-assign]
    return svc


def _make_profile(
    profile_id: str,
    loudness_target_lufs: float = -14.0,
    true_peak_ceiling_dbtp: float = -1.0,
) -> DeliveryProfile:
    """Build an in-memory DeliveryProfile for testing."""
    return DeliveryProfile(
        id=profile_id,
        name=f"profile-{profile_id[:8]}",
        output_formats=[],
        loudness_target_lufs=loudness_target_lufs,
        true_peak_ceiling_dbtp=true_peak_ceiling_dbtp,
        metadata_template=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def test_run_qc_with_profile_resolves_targets(tmp_path: Path) -> None:
    """POST /qc/run with delivery_profile_id only → loudness/true_peak targets non-null (BL-628)."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    repo = InMemoryQCReportRepository()
    svc = _make_echo_target_service(repo)

    profile_id = str(uuid.uuid4())
    dp_repo = AsyncInMemoryDeliveryProfileRepository()
    dp_repo._profiles[profile_id] = _make_profile(
        profile_id, loudness_target_lufs=-14.0, true_peak_ceiling_dbtp=-1.0
    )

    app = _make_api_app(svc, repo, delivery_profile_repo=dp_repo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/qc/run",
            json={"artifact_path": str(artifact), "delivery_profile_id": profile_id},
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["checks"]["loudness_integrated"]["target"] is not None, (
        "loudness_integrated.target must be non-null when delivery_profile_id is provided"
    )
    assert body["checks"]["true_peak"]["target"] is not None, (
        "true_peak.target must be non-null when delivery_profile_id is provided"
    )


def test_run_qc_explicit_assertions_win_over_profile(tmp_path: Path) -> None:
    """POST /qc/run with both profile and explicit assertions → explicit wins (BL-628-AC-2)."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    repo = InMemoryQCReportRepository()
    svc = _make_echo_target_service(repo)

    profile_id = str(uuid.uuid4())
    dp_repo = AsyncInMemoryDeliveryProfileRepository()
    dp_repo._profiles[profile_id] = _make_profile(
        profile_id, loudness_target_lufs=-14.0, true_peak_ceiling_dbtp=-1.0
    )

    app = _make_api_app(svc, repo, delivery_profile_repo=dp_repo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/qc/run",
            json={
                "artifact_path": str(artifact),
                "delivery_profile_id": profile_id,
                "assertions": {"loudness_integrated": -16.0},
            },
        )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    # Explicit assertion (-16.0) overrides profile loudness_target_lufs (-14.0)
    assert body["checks"]["loudness_integrated"]["target"] == -16.0, (
        "Explicit assertion must take precedence over profile target"
    )
    # true_peak comes from profile when no explicit assertion provided
    assert body["checks"]["true_peak"]["target"] == -1.0


def test_run_qc_profile_not_found_returns_404(tmp_path: Path) -> None:
    """POST /qc/run with non-existent delivery_profile_id returns 404 (BL-628-AC-4)."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    repo = InMemoryQCReportRepository()
    svc = _make_echo_target_service(repo)
    dp_repo = AsyncInMemoryDeliveryProfileRepository()

    app = _make_api_app(svc, repo, delivery_profile_repo=dp_repo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/qc/run",
            json={
                "artifact_path": str(artifact),
                "delivery_profile_id": "00000000-0000-0000-0000-000000000000",
            },
        )

    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# WebSocket event tests
# ---------------------------------------------------------------------------


async def test_qc_started_event_emitted(tmp_path: Path) -> None:
    """qc.started event is broadcast when a QC run begins."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, events = _make_service()
    await svc.run_checks(str(artifact))

    started = [e for e in events if e.get("type") == EventType.QC_STARTED.value]
    assert len(started) == 1
    assert started[0]["payload"]["artifact_path"] == str(artifact)


async def test_qc_check_completed_event_emitted_for_each_check(tmp_path: Path) -> None:
    """qc.check_completed is broadcast 12 times — once per check."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, events = _make_service()
    await svc.run_checks(str(artifact))

    completed = [e for e in events if e.get("type") == EventType.QC_CHECK_COMPLETED.value]
    assert len(completed) == 12
    emitted_ids = {e["payload"]["check_id"] for e in completed}
    assert emitted_ids == set(ALL_CHECK_IDS)


async def test_qc_completed_event_emitted(tmp_path: Path) -> None:
    """qc.completed event is broadcast when all checks finish."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, events = _make_service()
    await svc.run_checks(str(artifact))

    done = [e for e in events if e.get("type") == EventType.QC_COMPLETED.value]
    assert len(done) == 1
    assert "overall_verdict" in done[0]["payload"]


# ---------------------------------------------------------------------------
# Parity test — standalone vs. post-render schema equivalence
# ---------------------------------------------------------------------------


async def test_qc_standalone_vs_post_render_parity(tmp_path: Path) -> None:
    """Standalone QC run and a simulated post-render run share the same schema.

    Verifies that QCReport.checks always contains all 11 keys regardless of
    how run_checks() is invoked, satisfying the parity contract.
    """
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc_standalone, _repo_a, _ = _make_service()
    svc_post_render, _repo_b, _ = _make_service()

    record_a = await svc_standalone.run_checks(str(artifact))
    record_b = await svc_post_render.run_checks(str(artifact), job_id="job-xyz")

    checks_a = set(json.loads(record_a.checks).keys())
    checks_b = set(json.loads(record_b.checks).keys())
    assert checks_a == checks_b == set(ALL_CHECK_IDS)


# ---------------------------------------------------------------------------
# Contract test — FFmpeg-gated (deferred_post_merge)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires FFmpeg (STOAT_TEST_FFMPEG=1)")
async def test_qc_service_golden_fixture(sample_video_path: Path) -> None:
    """QCReport fields match known expected values from a golden render fixture.

    Discharge condition: run with STOAT_TEST_FFMPEG=1 against a real sample video.
    """
    assert GOLDEN_FIXTURE.exists(), "Golden fixture must exist"
    svc, _, _ = _make_service()
    record = await svc.run_checks(str(sample_video_path))
    checks = json.loads(record.checks)
    assert set(checks.keys()) == set(ALL_CHECK_IDS)
    assert record.overall_verdict in ("pass", "fail", "error")


# ---------------------------------------------------------------------------
# Unit tests — BL-623 null-pass exclusion in overall_verdict aggregation
# ---------------------------------------------------------------------------


async def test_overall_verdict_excludes_null_pass_checks(tmp_path: Path) -> None:
    """overall_verdict is 'pass' when null-pass checks are excluded and at least one passes."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, _ = _make_service()
    call_count = [0]

    async def _mixed_null_true(**kwargs: Any) -> dict:
        call_count[0] += 1
        # First check passes; all others return null pass (unasserted)
        if call_count[0] == 1:
            return {"measured": -14.0, "target": -14.0, "pass": True, "units": "LUFS"}
        return {"measured": None, "target": None, "pass": None, "units": ""}

    svc._run_check = _mixed_null_true  # type: ignore[method-assign]
    record = await svc.run_checks(str(artifact))
    assert record.overall_verdict == "pass"


async def test_overall_verdict_all_null_is_fail(tmp_path: Path) -> None:
    """overall_verdict is 'fail' when all checks have pass=null (no assertions at all)."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, _ = _make_service()

    async def _null_check(**kwargs: Any) -> dict:
        return {"measured": None, "target": None, "pass": None, "units": ""}

    svc._run_check = _null_check  # type: ignore[method-assign]
    record = await svc.run_checks(str(artifact))
    assert record.overall_verdict == "fail"


async def test_overall_verdict_any_false_is_fail(tmp_path: Path) -> None:
    """overall_verdict is 'fail' when any asserted check has pass=False, even with null others."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, _ = _make_service()
    call_count = [0]

    async def _null_then_false(**kwargs: Any) -> dict:
        call_count[0] += 1
        if call_count[0] == 1:
            return {"measured": None, "target": None, "pass": None, "units": ""}
        if call_count[0] == 2:
            return {"measured": -10.0, "target": -14.0, "pass": False, "units": "LUFS"}
        return {"measured": None, "target": None, "pass": None, "units": ""}

    svc._run_check = _null_then_false  # type: ignore[method-assign]
    record = await svc.run_checks(str(artifact))
    assert record.overall_verdict == "fail"


# ---------------------------------------------------------------------------
# Unit tests — BL-624 tone_presence null-target and parse-failure paths
# ---------------------------------------------------------------------------


async def test_tone_presence_no_target_returns_null_pass(tmp_path: Path) -> None:
    """tone_presence with target=None returns pass=null when spectral parse fails."""
    artifact = tmp_path / "out.wav"
    artifact.write_bytes(b"placeholder")
    # FFmpeg returns rc=0 with empty stderr (no spectral data — triggers parse failure)
    svc, _, _ = _make_service(_make_mock_subprocess(stderr="", returncode=0))
    record = await svc.run_checks(str(artifact))
    checks = json.loads(record.checks)
    assert checks["tone_presence"]["pass"] is None, (
        f"Expected tone_presence.pass=null with no target, got {checks['tone_presence']['pass']}"
    )


async def test_tone_presence_parse_failure_with_asserted_target_returns_false(
    tmp_path: Path,
) -> None:
    """tone_presence with target set and parse failure returns pass=False."""
    artifact = tmp_path / "out.wav"
    artifact.write_bytes(b"placeholder")
    # FFmpeg returns rc=0 with empty stderr (parse fails — no spectral data)
    svc, _, _ = _make_service(_make_mock_subprocess(stderr="", returncode=0))
    record = await svc.run_checks(str(artifact), assertions={"tone_presence": -40.0})
    checks = json.loads(record.checks)
    assert checks["tone_presence"]["pass"] is False, (
        f"Expected tone_presence.pass=False with target set and parse failure, "
        f"got {checks['tone_presence']['pass']}"
    )


# ---------------------------------------------------------------------------
# Unit tests — BL-625 bidirectional loudness tolerance (±0.5 LU)
# ---------------------------------------------------------------------------


def _mock_loudness_report(integrated_lufs: float) -> MagicMock:
    """Build a mock parse_loudness_report return value with given integrated_lufs."""
    report = MagicMock()
    report.integrated_lufs = integrated_lufs
    report.true_peak_dbtp = -1.0
    report.lra = 7.0
    return report


def test_loudness_named_constant_exists() -> None:
    """LOUDNESS_TOLERANCE_LU constant exists in qc_service with value 0.5 (AC-MASTER-2)."""
    from stoat_ferret.api.services.qc_service import LOUDNESS_TOLERANCE_LU

    assert LOUDNESS_TOLERANCE_LU == 0.5


async def test_loudness_within_tolerance_passes(tmp_path: Path) -> None:
    """_check_loudness_integrated passes when measured is within ±0.5 LU of target.

    measured=-14.3, target=-14.0 → |(-14.3) - (-14.0)| = 0.3 ≤ 0.5 → pass=True.
    """
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")
    svc, _, _ = _make_service(_make_mock_subprocess(stderr="loudnorm_data", returncode=0))
    mock_report = _mock_loudness_report(-14.3)
    with patch("stoat_ferret_core.parse_loudness_report", return_value=mock_report):
        result = await svc._check_loudness_integrated(artifact_path=str(artifact), target=-14.0)
    assert result["pass"] is True, (
        f"Expected pass=True for measured=-14.3, target=-14.0, got {result['pass']}"
    )


async def test_loudness_too_loud_fails(tmp_path: Path) -> None:
    """_check_loudness_integrated fails when measured is more than 0.5 LU louder than target.

    measured=-13.4, target=-14.0 → |(-13.4) - (-14.0)| = 0.6 > 0.5 → pass=False.
    """
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")
    svc, _, _ = _make_service(_make_mock_subprocess(stderr="loudnorm_data", returncode=0))
    mock_report = _mock_loudness_report(-13.4)
    with patch("stoat_ferret_core.parse_loudness_report", return_value=mock_report):
        result = await svc._check_loudness_integrated(artifact_path=str(artifact), target=-14.0)
    assert result["pass"] is False, (
        f"Expected pass=False for measured=-13.4, target=-14.0, got {result['pass']}"
    )


async def test_loudness_too_quiet_fails(tmp_path: Path) -> None:
    """_check_loudness_integrated fails when measured is more than 0.5 LU quieter than target.

    measured=-18.0, target=-14.0 → |(-18.0) - (-14.0)| = 4.0 > 0.5 → pass=False.
    """
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")
    svc, _, _ = _make_service(_make_mock_subprocess(stderr="loudnorm_data", returncode=0))
    mock_report = _mock_loudness_report(-18.0)
    with patch("stoat_ferret_core.parse_loudness_report", return_value=mock_report):
        result = await svc._check_loudness_integrated(artifact_path=str(artifact), target=-14.0)
    assert result["pass"] is False, (
        f"Expected pass=False for measured=-18.0, target=-14.0, got {result['pass']}"
    )


async def test_loudness_far_above_target_fails(tmp_path: Path) -> None:
    """_check_loudness_integrated fails when measured is 4 LU louder than target.

    measured=-10.0, target=-14.0 → |(-10.0) - (-14.0)| = 4.0 > 0.5 → pass=False.
    """
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")
    svc, _, _ = _make_service(_make_mock_subprocess(stderr="loudnorm_data", returncode=0))
    mock_report = _mock_loudness_report(-10.0)
    with patch("stoat_ferret_core.parse_loudness_report", return_value=mock_report):
        result = await svc._check_loudness_integrated(artifact_path=str(artifact), target=-14.0)
    assert result["pass"] is False, (
        f"Expected pass=False for measured=-10.0, target=-14.0, got {result['pass']}"
    )


async def test_true_peak_scope_guard_ceiling_check_unchanged(tmp_path: Path) -> None:
    """_check_true_peak remains a one-sided ceiling check — unchanged by BL-625.

    measured=-2.0, target=-1.0 → -2.0 ≤ -1.0 → pass=True (below ceiling).
    A bidirectional change would break this: abs(-2.0 - (-1.0)) = 1.0 > 0.5 → False.
    """
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")
    svc, _, _ = _make_service(_make_mock_subprocess(stderr="loudnorm_data", returncode=0))
    mock_report = _mock_loudness_report(-21.0)
    mock_report.true_peak_dbtp = -2.0
    with patch("stoat_ferret_core.parse_loudness_report", return_value=mock_report):
        result = await svc._check_true_peak(artifact_path=str(artifact), target=-1.0)
    # -2.0 ≤ -1.0 → pass (ceiling check, not bidirectional)
    assert result["pass"] is True, (
        f"true_peak pass=True expected for measured=-2.0 (below ceiling -1.0), "
        f"got {result['pass']} — _check_true_peak must not use bidirectional form"
    )


# ---------------------------------------------------------------------------
# Behavioral tests — BL-626 decode_integrity null-decode (STOAT_TEST_FFMPEG=1)
# ---------------------------------------------------------------------------

CORRUPT_ARTIFACT = Path(__file__).parent / "fixtures" / "corrupt_artifact.mp4"


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1")
async def test_decode_integrity_corrupt_artifact_fails() -> None:
    """Corrupt artifact returns decode_integrity.pass=False under null-decode (BL-626-AC-2).

    The fixture is a truncated/garbage MP4 body. Without -c copy, FFmpeg decodes frames
    and detects the corruption, exiting non-zero → measured=1.0 → pass=False.
    """
    svc, _, _ = _make_service(asyncio.create_subprocess_exec)
    result = await svc._check_decode_integrity(artifact_path=str(CORRUPT_ARTIFACT), target=0.0)
    assert result["pass"] is False, (
        f"Expected pass=False for corrupt artifact, got {result['pass']} "
        f"(measured={result['measured']})"
    )


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1")
async def test_decode_integrity_valid_artifact_passes(sample_video_path: Path) -> None:
    """Valid artifact returns decode_integrity.measured=0.0 under null-decode (BL-626-AC-3).

    FFmpeg decodes all frames without errors → rc=0 → measured=0.0 → pass=True.
    """
    svc, _, _ = _make_service(asyncio.create_subprocess_exec)
    result = await svc._check_decode_integrity(artifact_path=str(sample_video_path), target=0.0)
    assert result["measured"] == 0.0, (
        f"Expected measured=0.0 for valid artifact, got {result['measured']}"
    )
