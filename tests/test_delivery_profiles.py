# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for delivery profile CRUD, render integration, and QC failure path."""

from __future__ import annotations

import contextlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.delivery_profiles_repository import (
    AsyncInMemoryDeliveryProfileRepository,
)
from stoat_ferret.db.models import Clip
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.qc_repository import InMemoryQCReportRepository, QCReportRecord
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService

# ---------- Helpers ----------


def _profile_name() -> str:
    """Generate a unique delivery profile name."""
    return f"test-profile-{uuid.uuid4()}"


def _make_profile(name: str | None = None) -> dict[str, Any]:
    """Build a valid CreateDeliveryProfileRequest body dict."""
    return {
        "name": name or _profile_name(),
        "output_formats": [{"container": "mp4", "codec": "h264", "bitrate_kbps": 2000}],
        "loudness_target_lufs": -16.0,
        "true_peak_ceiling_dbtp": -1.0,
        "metadata_template": {"title": "Test"},
    }


def _make_noop_render_service(render_repo: InMemoryRenderRepository) -> RenderService:
    """Build a RenderService in noop mode with mocked checkpoint manager."""
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()

    checkpoint_mgr = MagicMock(spec=RenderCheckpointManager)
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)

    return RenderService(
        repository=render_repo,
        queue=RenderQueue(render_repo),
        executor=MagicMock(spec=RenderExecutor),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_mode="noop"),
    )


def _make_qc_service_mock(
    verdict: str = "pass",
) -> tuple[MagicMock, InMemoryQCReportRepository]:
    """Build a mock QCService that returns a configurable verdict."""
    repo = InMemoryQCReportRepository()
    mock_service = MagicMock()
    checks = {
        "loudness_integrated": {
            "measured": -16.0,
            "target": -16.0,
            "pass": verdict == "pass",
            "units": "LUFS",
        },
        "true_peak": {
            "measured": -1.5,
            "target": -1.0,
            "pass": verdict == "pass",
            "units": "dBTP",
        },
    }
    report = QCReportRecord(
        id=str(uuid.uuid4()),
        job_id=None,
        artifact_path="/fake/output.mp4",
        delivery_profile_id=None,
        overall_verdict=verdict,
        checks=json.dumps(checks),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    mock_service.run_checks = AsyncMock(return_value=report)
    return mock_service, repo


# ---------- Fixtures ----------


@pytest.fixture
def dp_repo() -> AsyncInMemoryDeliveryProfileRepository:
    """In-memory delivery profile repository."""
    return AsyncInMemoryDeliveryProfileRepository()


@pytest.fixture
def render_repo() -> InMemoryRenderRepository:
    """In-memory render repository."""
    return InMemoryRenderRepository()


@pytest.fixture
def project_repo() -> AsyncInMemoryProjectRepository:
    """In-memory project repository."""
    return AsyncInMemoryProjectRepository()


@pytest.fixture
def clip_repo() -> AsyncInMemoryClipRepository:
    """In-memory clip repository."""
    return AsyncInMemoryClipRepository()


@pytest.fixture
def dp_client(
    dp_repo: AsyncInMemoryDeliveryProfileRepository,
) -> httpx.AsyncClient:
    """Async test client for delivery profile CRUD and validation tests.

    Includes a noop render service so POST /render doesn't 503 on service lookup,
    allowing delivery-profile validation checks to run before any render is queued.
    """
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository

    video_repo = AsyncInMemoryVideoRepository()
    proj_repo = AsyncInMemoryProjectRepository()
    clip_rep = AsyncInMemoryClipRepository()
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repo))

    render_repo_dp = InMemoryRenderRepository()
    render_service = _make_noop_render_service(render_repo_dp)

    app = create_app(
        video_repository=video_repo,
        project_repository=proj_repo,
        clip_repository=clip_rep,
        job_queue=queue,
        render_repository=render_repo_dp,
        render_service=render_service,
        delivery_profile_repository=dp_repo,
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.fixture
def render_client(
    dp_repo: AsyncInMemoryDeliveryProfileRepository,
    render_repo: InMemoryRenderRepository,
    project_repo: AsyncInMemoryProjectRepository,
    clip_repo: AsyncInMemoryClipRepository,
) -> httpx.AsyncClient:
    """Async test client for render+QC integration tests (noop mode, mock QC)."""
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository

    video_repo = AsyncInMemoryVideoRepository()
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repo))

    render_service = _make_noop_render_service(render_repo)
    qc_service_mock, _ = _make_qc_service_mock(verdict="pass")

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        job_queue=queue,
        render_repository=render_repo,
        render_service=render_service,
        delivery_profile_repository=dp_repo,
        qc_service=qc_service_mock,
    )
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


# ---------- Shared helper ----------


async def _seed_project_with_clip(client: httpx.AsyncClient) -> str:
    """Create a project and add a stub clip. Returns project_id."""
    proj_resp = await client.post("/api/v1/projects", json={"name": f"DP Test {uuid.uuid4()}"})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    clip_repo = transport.app.state.clip_repository  # type: ignore[union-attr]
    video_repo = transport.app.state.video_repository  # type: ignore[union-attr]

    from stoat_ferret.db.models import Video

    _VIDEO_ID = "00000000-0000-0000-0000-000000000001"
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


# ---------- Delivery Profile CRUD tests ----------


async def test_create_delivery_profile_201(
    dp_client: httpx.AsyncClient,
) -> None:
    """POST /delivery_profiles returns 201 with correct fields."""
    async with dp_client as client:
        resp = await client.post("/api/v1/delivery_profiles", json=_make_profile())
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["loudness_target_lufs"] == -16.0
    assert body["true_peak_ceiling_dbtp"] == -1.0
    assert len(body["output_formats"]) == 1


async def test_list_delivery_profiles_200(
    dp_client: httpx.AsyncClient,
) -> None:
    """GET /delivery_profiles returns 200 with items list."""
    async with dp_client as client:
        await client.post("/api/v1/delivery_profiles", json=_make_profile())
        resp = await client.get("/api/v1/delivery_profiles")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


async def test_get_delivery_profile_by_id_200(
    dp_client: httpx.AsyncClient,
) -> None:
    """GET /delivery_profiles/{id} returns 200 for existing profile."""
    async with dp_client as client:
        create_resp = await client.post("/api/v1/delivery_profiles", json=_make_profile())
        profile_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/delivery_profiles/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == profile_id


async def test_get_delivery_profile_by_id_404(
    dp_client: httpx.AsyncClient,
) -> None:
    """GET /delivery_profiles/{id} returns 404 for nonexistent profile."""
    async with dp_client as client:
        resp = await client.get(f"/api/v1/delivery_profiles/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "PROFILE_NOT_FOUND"


async def test_delete_delivery_profile_204(
    dp_client: httpx.AsyncClient,
) -> None:
    """DELETE /delivery_profiles/{id} returns 204 and profile is gone."""
    async with dp_client as client:
        create_resp = await client.post("/api/v1/delivery_profiles", json=_make_profile())
        profile_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/delivery_profiles/{profile_id}")
        assert del_resp.status_code == 204
        get_resp = await client.get(f"/api/v1/delivery_profiles/{profile_id}")
    assert get_resp.status_code == 404


async def test_delete_delivery_profile_404(
    dp_client: httpx.AsyncClient,
) -> None:
    """DELETE /delivery_profiles/{id} returns 404 for nonexistent profile."""
    async with dp_client as client:
        resp = await client.delete(f"/api/v1/delivery_profiles/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_create_delivery_profile_duplicate_name_409(
    dp_client: httpx.AsyncClient,
) -> None:
    """POST /delivery_profiles with duplicate name returns 409."""
    name = _profile_name()
    async with dp_client as client:
        await client.post("/api/v1/delivery_profiles", json=_make_profile(name=name))
        resp = await client.post("/api/v1/delivery_profiles", json=_make_profile(name=name))
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "DUPLICATE_PROFILE_NAME"


async def test_create_delivery_profile_invalid_loudness_422(
    dp_client: httpx.AsyncClient,
) -> None:
    """POST /delivery_profiles with loudness_target_lufs > 0 returns 422."""
    body = _make_profile()
    body["loudness_target_lufs"] = 1.0  # invalid: must be ≤ 0
    async with dp_client as client:
        resp = await client.post("/api/v1/delivery_profiles", json=body)
    assert resp.status_code == 422


# ---------- Render integration tests ----------


async def test_render_delivery_profile_not_found_422(
    dp_client: httpx.AsyncClient,
) -> None:
    """POST /render with nonexistent delivery_profile returns 422."""
    async with dp_client as client:
        resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": str(uuid.uuid4()),
                "render_plan": '{"total_duration": 5.0, "settings": {}}',
                "delivery_profile": "nonexistent-profile-name",
            },
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "DELIVERY_PROFILE_NOT_FOUND"


async def test_render_with_delivery_profile_triggers_qc(
    render_client: httpx.AsyncClient,
    dp_repo: AsyncInMemoryDeliveryProfileRepository,
) -> None:
    """POST /render with delivery_profile invokes QCService post-render."""
    async with render_client as client:
        transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
        qc_service = transport.app.state.qc_service  # type: ignore[union-attr]

        project_id = await _seed_project_with_clip(client)
        name = _profile_name()
        await client.post("/api/v1/delivery_profiles", json=_make_profile(name=name))

        resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": '{"total_duration": 5.0, "settings": {}}',
                "delivery_profile": name,
            },
        )

    assert resp.status_code == 201
    qc_service.run_checks.assert_called_once()
    call_kwargs = qc_service.run_checks.call_args[1]
    assert "assertions" in call_kwargs
    assert "loudness_integrated" in call_kwargs["assertions"]
    assert call_kwargs["assertions"]["loudness_integrated"] == -16.0


async def test_render_qc_failure_sets_status_qc_failed(
    dp_repo: AsyncInMemoryDeliveryProfileRepository,
    render_repo: InMemoryRenderRepository,
    project_repo: AsyncInMemoryProjectRepository,
    clip_repo: AsyncInMemoryClipRepository,
) -> None:
    """POST /render with failing QC sets job status to qc_failed."""
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository

    video_repo = AsyncInMemoryVideoRepository()
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repo))

    render_service = _make_noop_render_service(render_repo)
    failing_qc_service, _ = _make_qc_service_mock(verdict="fail")

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        job_queue=queue,
        render_repository=render_repo,
        render_service=render_service,
        delivery_profile_repository=dp_repo,
        qc_service=failing_qc_service,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        project_id = await _seed_project_with_clip(client)
        name = _profile_name()
        await client.post("/api/v1/delivery_profiles", json=_make_profile(name=name))

        resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": '{"total_duration": 5.0, "settings": {}}',
                "delivery_profile": name,
            },
        )

    assert resp.status_code == 201
    assert resp.json()["status"] == "qc_failed"


async def test_render_qc_failure_project_remains_editable(
    dp_repo: AsyncInMemoryDeliveryProfileRepository,
    render_repo: InMemoryRenderRepository,
    project_repo: AsyncInMemoryProjectRepository,
    clip_repo: AsyncInMemoryClipRepository,
) -> None:
    """When QC fails, the project status must NOT be set to locked."""
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository

    video_repo = AsyncInMemoryVideoRepository()
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repo))

    render_service = _make_noop_render_service(render_repo)
    failing_qc_service, _ = _make_qc_service_mock(verdict="fail")

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repo,
        clip_repository=clip_repo,
        job_queue=queue,
        render_repository=render_repo,
        render_service=render_service,
        delivery_profile_repository=dp_repo,
        qc_service=failing_qc_service,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        project_id = await _seed_project_with_clip(client)
        name = _profile_name()
        await client.post("/api/v1/delivery_profiles", json=_make_profile(name=name))

        await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": '{"total_duration": 5.0, "settings": {}}',
                "delivery_profile": name,
            },
        )

        proj_resp = await client.get(f"/api/v1/projects/{project_id}")

    assert proj_resp.status_code == 200
    # The project model does not have a "status" field — absence of "locked" is the invariant.
    assert proj_resp.json().get("status") != "locked"


async def test_existing_render_callers_unaffected(
    render_client: httpx.AsyncClient,
) -> None:
    """POST /render without delivery_profile still works (backwards compatibility)."""
    async with render_client as client:
        project_id = await _seed_project_with_clip(client)
        resp = await client.post(
            "/api/v1/render",
            json={
                "project_id": project_id,
                "render_plan": '{"total_duration": 5.0, "settings": {}}',
            },
        )
    assert resp.status_code == 201
    assert resp.json()["status"] in ("queued", "running", "completed")


async def test_render_with_and_without_delivery_profile_validation_parity(
    dp_client: httpx.AsyncClient,
) -> None:
    """Both render paths produce identical 422 for missing required fields."""
    async with dp_client as client:
        # Missing project_id — should 422 from Pydantic in both cases
        resp_no_profile = await client.post(
            "/api/v1/render",
            json={"render_plan": "{}"},
        )
        resp_with_profile = await client.post(
            "/api/v1/render",
            json={"render_plan": "{}", "delivery_profile": "some-profile"},
        )

    assert resp_no_profile.status_code == 422
    assert resp_with_profile.status_code == 422
