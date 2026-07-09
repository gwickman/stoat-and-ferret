# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

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
    """Return a deterministic checks dict with all 12 check IDs set to null."""
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


@pytest.fixture()
async def qc_smoke_client_with_dp() -> httpx.AsyncClient:  # type: ignore[misc]
    """Async httpx client with mock QCService and delivery_profile_repository injected.

    Extends qc_smoke_client with an in-memory delivery profile repository so that
    POST /qc/run with delivery_profile_id exercises the profile resolution path.
    """
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.delivery_profiles_repository import AsyncInMemoryDeliveryProfileRepository
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
        delivery_profile_repository=AsyncInMemoryDeliveryProfileRepository(),
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


async def test_smoke_post_qc_run_with_profile_resolves_targets(
    qc_smoke_client_with_dp: httpx.AsyncClient,
) -> None:
    """POST /qc/run with delivery_profile_id routes through profile lookup correctly (BL-628).

    Creates a delivery profile, then verifies POST /qc/run returns 201 and echoes
    delivery_profile_id back. Validates routing and DI wiring — not FFmpeg output.
    """
    client = qc_smoke_client_with_dp

    dp_resp = await client.post(
        "/api/v1/delivery_profiles",
        json={
            "name": "smoke-profile-qc",
            "output_formats": [{"container": "mp4", "codec": "h264", "bitrate_kbps": 2000}],
            "loudness_target_lufs": -14.0,
            "true_peak_ceiling_dbtp": -1.0,
        },
    )
    assert dp_resp.status_code == 201, dp_resp.text
    profile_id = dp_resp.json()["id"]

    resp = await client.post(
        "/api/v1/qc/run",
        json={"artifact_path": "/tmp/smoke.mp4", "delivery_profile_id": profile_id},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["delivery_profile_id"] == profile_id
    assert "checks" in body


async def test_smoke_post_qc_run_profile_not_found_returns_404(
    qc_smoke_client_with_dp: httpx.AsyncClient,
) -> None:
    """POST /qc/run with non-existent delivery_profile_id returns 404 (BL-628-AC-4)."""
    resp = await qc_smoke_client_with_dp.post(
        "/api/v1/qc/run",
        json={
            "artifact_path": "/tmp/smoke.mp4",
            "delivery_profile_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Worker-path QC smoke test (BL-477)
# ---------------------------------------------------------------------------


async def _seed_stub_project_with_clip(client: httpx.AsyncClient) -> str:
    """Create a project and insert a stub video+clip into the in-memory repos.

    Returns:
        The project_id string.
    """
    import contextlib

    from stoat_ferret.db.models import Clip, Video

    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "QC Worker Path Smoke Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    video_repo = transport.app.state.video_repository  # type: ignore[union-attr]
    clip_repo = transport.app.state.clip_repository  # type: ignore[union-attr]

    _VIDEO_ID = "00000000-0000-0000-0000-000000000099"
    now = datetime.now(timezone.utc)
    with contextlib.suppress(Exception):
        await video_repo.add(
            Video(
                id=_VIDEO_ID,
                path="/stub/video.mp4",
                filename="video.mp4",
                duration_frames=100,
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
        source_video_id=_VIDEO_ID,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repo.add(clip)
    return project_id


@pytest.fixture()
async def qc_worker_path_client() -> httpx.AsyncClient:  # type: ignore[misc]
    """Async client with mock QCService wired into noop RenderService (worker-path test).

    Uses fully in-memory repos and a mock QC service so that noop-mode renders
    trigger QC via RenderService._complete_job without requiring FFmpeg.
    """
    from unittest.mock import AsyncMock, MagicMock

    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.api.settings import Settings
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.db.delivery_profiles_repository import AsyncInMemoryDeliveryProfileRepository
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


async def test_smoke_render_qc_worker_path(
    qc_worker_path_client: httpx.AsyncClient,
) -> None:
    """Worker-path render with delivery profile stores QCReport at /render/{job_id}/qc."""
    client = qc_worker_path_client

    dp_resp = await client.post(
        "/api/v1/delivery_profiles",
        json={
            "name": "smoke-qc-profile",
            "output_formats": [{"container": "mp4", "codec": "h264", "bitrate_kbps": 2000}],
            "loudness_target_lufs": -16.0,
            "true_peak_ceiling_dbtp": -1.0,
        },
    )
    assert dp_resp.status_code == 201
    profile_name = dp_resp.json()["name"]

    project_id = await _seed_stub_project_with_clip(client)

    render_resp = await client.post(
        "/api/v1/render",
        json={
            "project_id": project_id,
            "delivery_profile": profile_name,
            "render_plan": json.dumps({"total_duration": 10.0, "settings": {}}),
        },
    )
    assert render_resp.status_code == 201
    job_id = render_resp.json()["id"]

    qc_resp = await client.get(f"/api/v1/render/{job_id}/qc")
    assert qc_resp.status_code == 200
    body = qc_resp.json()
    assert "id" in body
    assert "overall_verdict" in body
    assert "checks" in body
    assert len(body["checks"]) > 0
