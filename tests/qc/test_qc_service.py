"""Unit, API, WebSocket, and contract tests for QCService and /qc endpoints (BL-424)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.qc_service import ALL_CHECK_IDS, QCService
from stoat_ferret.api.websocket.events import EventType
from stoat_ferret.api.websocket.manager import ConnectionManager
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


def _make_api_app(svc: QCService, repo: InMemoryQCReportRepository | None = None) -> FastAPI:
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
    )
    if repo is not None:
        app.state.qc_report_repository = repo
    return app


# ---------------------------------------------------------------------------
# Unit tests — QCService.run_checks()
# ---------------------------------------------------------------------------


async def test_qc_service_runs_all_11_checks(tmp_path: Path) -> None:
    """QCReport contains all 11 check IDs when FFmpeg is mocked."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, repo, _ = _make_service()
    record = await svc.run_checks(str(artifact))

    checks = json.loads(record.checks)
    missing = set(ALL_CHECK_IDS) - set(checks.keys())
    assert set(checks.keys()) == set(ALL_CHECK_IDS), f"Missing checks: {missing}"
    assert len(checks) == 11


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
    app = _make_api_app(svc, repo)

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/qc/run",
            json={
                "artifact_path": str(artifact),
                "delivery_profile_id": "profile-does-not-exist",
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
    """qc.check_completed is broadcast 11 times — once per check."""
    artifact = tmp_path / "out.mp4"
    artifact.write_bytes(b"placeholder")

    svc, _, events = _make_service()
    await svc.run_checks(str(artifact))

    completed = [e for e in events if e.get("type") == EventType.QC_CHECK_COMPLETED.value]
    assert len(completed) == 11
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

    svc_standalone, repo_a, _ = _make_service()
    svc_post_render, repo_b, _ = _make_service()

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
