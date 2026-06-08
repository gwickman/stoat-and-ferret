"""Smoke tests for QC API endpoints.

Validates all three /qc routes are reachable and return correct schemas
without requiring FFmpeg. A mock QCService returns a deterministic QCReport.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.services.qc_service import ALL_CHECK_IDS, QCService
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository, QCReportRecord


def _null_checks() -> dict[str, Any]:
    """Return a deterministic checks dict with all 11 check IDs set to null."""
    return {
        check_id: {"measured": None, "target": None, "pass": False, "units": ""}
        for check_id in ALL_CHECK_IDS
    }


def _build_mock_qc_service(repo: InMemoryQCReportRepository) -> QCService:
    """Build a mock QCService that writes to an in-memory repo without FFmpeg."""

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


@pytest.fixture()
async def qc_smoke_client() -> httpx.AsyncClient:  # type: ignore[misc]
    """Async httpx client with mock QCService injected — no FFmpeg required.

    Uses app.state._deps_injected = True (set automatically when repositories
    are injected via create_app) to bypass lifespan DB and worker initialisation.
    """
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
    from stoat_ferret.jobs.queue import InMemoryJobQueue

    repo = InMemoryQCReportRepository()
    svc = _build_mock_qc_service(repo)

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
    app.state.qc_report_repository = repo

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client


async def test_smoke_post_qc_run(qc_smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/qc/run returns 201 with id, overall_verdict, and checks fields."""
    resp = await qc_smoke_client.post(
        "/api/v1/qc/run",
        json={"artifact_path": "/tmp/smoke-artifact.mp4"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert "overall_verdict" in body
    assert "checks" in body
    assert isinstance(body["overall_verdict"], str)
    assert isinstance(body["checks"], dict)
    assert len(body["checks"]) == len(ALL_CHECK_IDS)


async def test_smoke_get_qc_report_by_id(qc_smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/qc/reports/{id} returns 200 with correct schema fields."""
    post_resp = await qc_smoke_client.post(
        "/api/v1/qc/run",
        json={"artifact_path": "/tmp/smoke-artifact.mp4"},
    )
    assert post_resp.status_code == 201
    report_id = post_resp.json()["id"]

    resp = await qc_smoke_client.get(f"/api/v1/qc/reports/{report_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == report_id
    assert "overall_verdict" in body
    assert "checks" in body
    assert "artifact_path" in body
    assert "created_at" in body


async def test_smoke_get_render_job_qc(qc_smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/render/{job_id}/qc returns 404 with detail field when no report exists."""
    nonexistent_job_id = str(uuid.uuid4())
    resp = await qc_smoke_client.get(f"/api/v1/render/{nonexistent_job_id}/qc")
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body
