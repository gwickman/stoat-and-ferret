# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for render API quality_preset translation layer.

Covers the QUALITY_PRESET_MAP constant, public-to-FFmpeg vocabulary translation,
and validation that public API rejects FFmpeg preset names and invalid values.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.routers.render import _CODEC_ENCODER_MAP, QUALITY_PRESET_MAP
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project, Track
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import CancelPreemptedError, RenderService
from tests.conftest import TEST_PROJECT_UUID

# ---------- Fixtures ----------


@pytest.fixture
def render_repo() -> InMemoryRenderRepository:
    """Isolated in-memory render repository."""
    return InMemoryRenderRepository()


@pytest.fixture
def mock_render_service(render_repo: InMemoryRenderRepository) -> AsyncMock:
    """Mock RenderService that records the render_plan_json it receives."""
    service = AsyncMock(spec=RenderService)

    async def fake_submit(
        *,
        project_id: str,
        output_path: str,
        output_format: OutputFormat,
        quality_preset: QualityPreset,
        render_plan_json: str,
    ) -> RenderJob:
        job = RenderJob.create(
            project_id=project_id,
            output_path=output_path,
            output_format=output_format,
            quality_preset=quality_preset,
            render_plan=render_plan_json,
        )
        return await render_repo.create(job)

    service.submit_job = AsyncMock(side_effect=fake_submit)
    service.cancel_job = AsyncMock(return_value=True)
    service.recover = AsyncMock(return_value=[])
    return service


@pytest.fixture
def render_app(
    render_repo: InMemoryRenderRepository,
    mock_render_service: AsyncMock,
) -> FastAPI:
    """Test app with render dependencies injected."""
    now = datetime.now(timezone.utc)
    project_repo = AsyncInMemoryProjectRepository()
    project_repo.seed(
        [
            Project(
                id=TEST_PROJECT_UUID,
                name="Test Project",
                output_width=1920,
                output_height=1080,
                output_fps=30,
                created_at=now,
                updated_at=now,
            )
        ]
    )
    clip_repo = AsyncInMemoryClipRepository()
    clip_repo.seed(
        [
            Clip(
                id="22222222-2222-2222-2222-222222222222",
                project_id=TEST_PROJECT_UUID,
                source_video_id="vid-test",
                in_point=0,
                out_point=100,
                timeline_position=0,
                created_at=now,
                updated_at=now,
            )
        ]
    )
    return create_app(
        render_repository=render_repo,
        render_service=mock_render_service,
        project_repository=project_repo,
        clip_repository=clip_repo,
    )


@pytest.fixture
def render_client(render_app: FastAPI) -> Generator[TestClient, None, None]:
    """Test client for render endpoints."""
    with TestClient(render_app) as c:
        yield c


# ---------- QUALITY_PRESET_MAP unit tests ----------


def test_quality_preset_map_draft() -> None:
    """QUALITY_PRESET_MAP maps 'draft' to FFmpeg 'veryfast'."""
    assert QUALITY_PRESET_MAP["draft"] == "veryfast"


def test_quality_preset_map_standard() -> None:
    """QUALITY_PRESET_MAP maps 'standard' to FFmpeg 'medium'."""
    assert QUALITY_PRESET_MAP["standard"] == "medium"


def test_quality_preset_map_high() -> None:
    """QUALITY_PRESET_MAP maps 'high' to FFmpeg 'slow'."""
    assert QUALITY_PRESET_MAP["high"] == "slow"


def test_quality_preset_map_complete() -> None:
    """QUALITY_PRESET_MAP covers all three public preset values."""
    assert set(QUALITY_PRESET_MAP.keys()) == {"draft", "standard", "high"}
    assert set(QUALITY_PRESET_MAP.values()) == {"veryfast", "medium", "slow"}


# ---------- API validation: valid public presets ----------


def test_valid_preset_draft_accepted(render_client: TestClient) -> None:
    """POST /render with quality_preset='draft' returns 201."""
    resp = render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "draft",
            "render_plan": json.dumps({"settings": {}}),
        },
    )
    assert resp.status_code == 201
    assert resp.json()["quality_preset"] == "draft"


def test_valid_preset_standard_accepted(render_client: TestClient) -> None:
    """POST /render with quality_preset='standard' returns 201."""
    resp = render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "standard",
            "render_plan": json.dumps({"settings": {}}),
        },
    )
    assert resp.status_code == 201
    assert resp.json()["quality_preset"] == "standard"


def test_valid_preset_high_accepted(render_client: TestClient) -> None:
    """POST /render with quality_preset='high' returns 201."""
    resp = render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "high",
            "render_plan": json.dumps({"settings": {}}),
        },
    )
    assert resp.status_code == 201
    assert resp.json()["quality_preset"] == "high"


# ---------- API validation: FFmpeg preset names rejected ----------


def test_ffmpeg_preset_veryfast_rejected(render_client: TestClient) -> None:
    """POST /render with FFmpeg preset 'veryfast' returns HTTP 400."""
    resp = render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "veryfast"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_PRESET"
    assert "draft | standard | high" in body["detail"]["message"]


def test_ffmpeg_preset_medium_rejected(render_client: TestClient) -> None:
    """POST /render with FFmpeg preset 'medium' returns HTTP 400."""
    resp = render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "medium"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_PRESET"
    assert "draft | standard | high" in body["detail"]["message"]


def test_ffmpeg_preset_slow_rejected(render_client: TestClient) -> None:
    """POST /render with FFmpeg preset 'slow' returns HTTP 400."""
    resp = render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "slow"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_PRESET"


# ---------- API validation: arbitrary invalid values rejected ----------


def test_invalid_preset_rejected(render_client: TestClient) -> None:
    """POST /render with an arbitrary invalid preset returns HTTP 400."""
    resp = render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "ultra"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_PRESET"
    assert "Use public vocabulary" in body["detail"]["message"]


def test_empty_preset_rejected(render_client: TestClient) -> None:
    """POST /render with empty string quality_preset returns HTTP 400."""
    resp = render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": ""},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_PRESET"


# ---------- Translation: FFmpeg preset injected into render_plan ----------


def test_draft_translated_in_render_plan(
    render_client: TestClient,
    mock_render_service: AsyncMock,
) -> None:
    """draft preset translates to 'veryfast' in the render_plan passed to service."""
    render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "draft",
            "render_plan": json.dumps({"settings": {}}),
        },
    )
    call_kwargs = mock_render_service.submit_job.call_args.kwargs
    plan = json.loads(call_kwargs["render_plan_json"])
    assert plan["settings"]["quality_preset"] == "veryfast"


def test_standard_translated_in_render_plan(
    render_client: TestClient,
    mock_render_service: AsyncMock,
) -> None:
    """standard preset translates to 'medium' in the render_plan passed to service."""
    render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "standard",
            "render_plan": json.dumps({"settings": {}}),
        },
    )
    call_kwargs = mock_render_service.submit_job.call_args.kwargs
    plan = json.loads(call_kwargs["render_plan_json"])
    assert plan["settings"]["quality_preset"] == "medium"


def test_high_translated_in_render_plan(
    render_client: TestClient,
    mock_render_service: AsyncMock,
) -> None:
    """high preset translates to 'slow' in the render_plan passed to service."""
    render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "high",
            "render_plan": json.dumps({"settings": {}}),
        },
    )
    call_kwargs = mock_render_service.submit_job.call_args.kwargs
    plan = json.loads(call_kwargs["render_plan_json"])
    assert plan["settings"]["quality_preset"] == "slow"


def test_existing_render_plan_settings_preserved(
    render_client: TestClient,
    mock_render_service: AsyncMock,
) -> None:
    """Translation preserves existing render_plan settings except quality_preset."""
    import json

    plan_input = json.dumps({"settings": {"codec": "libx264", "fps": 30.0}})
    render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "standard",
            "render_plan": plan_input,
        },
    )
    call_kwargs = mock_render_service.submit_job.call_args.kwargs
    plan = json.loads(call_kwargs["render_plan_json"])
    assert plan["settings"]["codec"] == "libx264"
    assert plan["settings"]["fps"] == 30.0
    assert plan["settings"]["quality_preset"] == "medium"


# ---------- Encoder field in /render/formats (BL-345) ----------


def test_formats_encoder_field_present(render_client: TestClient) -> None:
    """GET /render/formats returns encoder field for all codec entries."""
    resp = render_client.get("/api/v1/render/formats")
    assert resp.status_code == 200
    for fmt in resp.json()["formats"]:
        for codec in fmt["codecs"]:
            msg = f"encoder missing from codec {codec['name']} in {fmt['format']}"
            assert "encoder" in codec, msg
            assert isinstance(codec["encoder"], str)
            assert len(codec["encoder"]) > 0


def test_formats_encoder_values_correct(render_client: TestClient) -> None:
    """GET /render/formats returns correct FFmpeg encoder names for each codec."""
    resp = render_client.get("/api/v1/render/formats")
    assert resp.status_code == 200
    seen: dict[str, str] = {}
    for fmt in resp.json()["formats"]:
        for codec in fmt["codecs"]:
            name = codec["name"]
            encoder = codec["encoder"]
            if name in seen:
                assert seen[name] == encoder, f"Inconsistent encoder for {name}"
            else:
                seen[name] = encoder
    # Verify each seen codec maps to the expected FFmpeg encoder
    for codec_name, encoder_name in seen.items():
        assert encoder_name == _CODEC_ENCODER_MAP[codec_name], (
            f"Codec {codec_name}: expected {_CODEC_ENCODER_MAP[codec_name]}, got {encoder_name}"
        )


def test_formats_all_six_codecs_have_encoder(render_client: TestClient) -> None:
    """GET /render/formats covers all six codec families, each with an encoder field."""
    resp = render_client.get("/api/v1/render/formats")
    assert resp.status_code == 200
    found_codecs: dict[str, str] = {}
    for fmt in resp.json()["formats"]:
        for codec in fmt["codecs"]:
            found_codecs[codec["name"]] = codec["encoder"]
    expected = {
        "h264": "libx264",
        "h265": "libx265",
        "vp8": "libvpx",
        "vp9": "libvpx-vp9",
        "prores": "prores_ks",
        "av1": "libaom-av1",
    }
    for codec_name, expected_encoder in expected.items():
        assert codec_name in found_codecs, f"Codec {codec_name} not found in any format"
        assert found_codecs[codec_name] == expected_encoder, (
            f"Codec {codec_name}: expected {expected_encoder}, got {found_codecs[codec_name]}"
        )


# ---------- Cancel 409 on already-terminal job (BL-412) ----------


def test_cancel_preempted_error_returns_409_not_cancellable(
    render_client: TestClient,
    mock_render_service: AsyncMock,
) -> None:
    """When cancel_job raises CancelPreemptedError, router returns 409 NOT_CANCELLABLE."""
    # Create a job via the API so the render_repo has it in QUEUED status.
    create_resp = render_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "quality_preset": "standard",
            "render_plan": json.dumps({"settings": {}}),
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    # Configure the service to raise CancelPreemptedError (simulates the CAS path).
    mock_render_service.cancel_job = AsyncMock(side_effect=CancelPreemptedError("completed"))

    resp = render_client.post(f"/api/v1/render/{job_id}/cancel")
    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["code"] == "NOT_CANCELLABLE"
    assert body["detail"]["status"] == "completed"


async def test_cancel_non_cancellable_job_returns_409(
    render_app: FastAPI,
    render_repo: InMemoryRenderRepository,
    mock_render_service: AsyncMock,
) -> None:
    """POST cancel on a job whose pre-check status is terminal returns 409 NOT_CANCELLABLE."""
    from httpx import ASGITransport, AsyncClient

    from stoat_ferret.render.models import RenderJob, RenderStatus

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    completed_job = RenderJob(
        id="job-completed-precheck",
        project_id=TEST_PROJECT_UUID,
        status=RenderStatus.COMPLETED,
        output_path="/tmp/done.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan="{}",
        progress=1.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    await render_repo.create(completed_job)

    async with AsyncClient(
        transport=ASGITransport(app=render_app), base_url="http://test"
    ) as client:
        resp = await client.post(f"/api/v1/render/{completed_job.id}/cancel")

    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["code"] == "NOT_CANCELLABLE"


# ---------- partial_file_detected field in REST response (BL-415) ----------


async def test_partial_file_detected_false_by_default(
    render_app: FastAPI,
    render_repo: InMemoryRenderRepository,
) -> None:
    """GET /render/{job_id} for a new job returns partial_file_detected=False."""
    from httpx import ASGITransport, AsyncClient

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job = RenderJob(
        id="job-partial-default",
        project_id=TEST_PROJECT_UUID,
        status=RenderStatus.QUEUED,
        output_path="/tmp/out.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan="{}",
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    await render_repo.create(job)

    async with AsyncClient(
        transport=ASGITransport(app=render_app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/render/{job.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert "partial_file_detected" in body
    assert body["partial_file_detected"] is False


async def test_partial_file_detected_true_for_cancelled_job(
    render_app: FastAPI,
    render_repo: InMemoryRenderRepository,
) -> None:
    """GET /render/{job_id} for a cancelled job with partial file returns partial_file_detected=True."""  # noqa: E501
    from httpx import ASGITransport, AsyncClient

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job = RenderJob(
        id="job-partial-cancelled",
        project_id=TEST_PROJECT_UUID,
        status=RenderStatus.CANCELLED,
        output_path="/tmp/partial.mp4",
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan="{}",
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=now,
        partial_file_detected=True,
    )
    await render_repo.create(job)

    async with AsyncClient(
        transport=ASGITransport(app=render_app), base_url="http://test"
    ) as client:
        resp = await client.get(f"/api/v1/render/{job.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert "partial_file_detected" in body
    assert body["partial_file_detected"] is True


# ---------- FK constraint enforcement tests (BL-413) ----------


@pytest.fixture
async def fk_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """In-memory aiosqlite connection with FK enforcement ON via create_tables_async."""
    from stoat_ferret.db.schema import create_tables_async

    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await create_tables_async(conn)
        yield conn


@pytest.fixture
async def fk_video_app(fk_db: aiosqlite.Connection) -> FastAPI:
    """App with real SQLite repos backed by FK-enforced in-memory DB."""
    from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository
    from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
    from stoat_ferret.db.project_repository import AsyncSQLiteProjectRepository

    return create_app(
        video_repository=AsyncSQLiteVideoRepository(fk_db),
        clip_repository=AsyncSQLiteClipRepository(fk_db),
        project_repository=AsyncSQLiteProjectRepository(fk_db),
    )


async def test_delete_referenced_video_returns_409(
    fk_db: aiosqlite.Connection,
    fk_video_app: FastAPI,
) -> None:
    """DELETE /videos/{id} for a video referenced by a clip returns 409 FK_CONSTRAINT_VIOLATION."""
    from httpx import ASGITransport, AsyncClient

    from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository
    from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
    from stoat_ferret.db.project_repository import AsyncSQLiteProjectRepository
    from tests.factories import make_test_video

    video_repo = AsyncSQLiteVideoRepository(fk_db)
    project_repo = AsyncSQLiteProjectRepository(fk_db)
    clip_repo = AsyncSQLiteClipRepository(fk_db)

    now = datetime.now(timezone.utc)
    video = make_test_video()
    await video_repo.add(video)

    project = Project(
        id=Project.new_id(),
        name="FK Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repo.add(project)

    clip = Clip(
        id=Clip.new_id(),
        project_id=project.id,
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repo.add(clip)

    async with AsyncClient(
        transport=ASGITransport(app=fk_video_app), base_url="http://test"
    ) as client:
        resp = await client.delete(f"/api/v1/videos/{video.id}")

    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["code"] == "FK_CONSTRAINT_VIOLATION"

    # Video row still exists (not deleted)
    still_there = await video_repo.get(video.id)
    assert still_there is not None


async def test_delete_unreferenced_video_returns_204(
    fk_db: aiosqlite.Connection,
    fk_video_app: FastAPI,
) -> None:
    """DELETE /videos/{id} for a video with no referencing clips returns 204."""
    from httpx import ASGITransport, AsyncClient

    from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository
    from tests.factories import make_test_video

    video_repo = AsyncSQLiteVideoRepository(fk_db)
    video = make_test_video()
    await video_repo.add(video)

    async with AsyncClient(
        transport=ASGITransport(app=fk_video_app), base_url="http://test"
    ) as client:
        resp = await client.delete(f"/api/v1/videos/{video.id}")

    assert resp.status_code == 204

    # Video row is gone
    gone = await video_repo.get(video.id)
    assert gone is None


async def test_delete_project_cascades_clips(
    fk_db: aiosqlite.Connection,
    fk_video_app: FastAPI,
) -> None:
    """DELETE /projects/{id} with FK enforcement ON cascades to clips (AC-4)."""
    from httpx import ASGITransport, AsyncClient

    from stoat_ferret.db.async_repository import AsyncSQLiteVideoRepository
    from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
    from stoat_ferret.db.project_repository import AsyncSQLiteProjectRepository
    from tests.factories import make_test_video

    video_repo = AsyncSQLiteVideoRepository(fk_db)
    project_repo = AsyncSQLiteProjectRepository(fk_db)
    clip_repo = AsyncSQLiteClipRepository(fk_db)

    now = datetime.now(timezone.utc)
    video = make_test_video()
    await video_repo.add(video)

    project = Project(
        id=Project.new_id(),
        name="Cascade Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repo.add(project)

    clip = Clip(
        id=Clip.new_id(),
        project_id=project.id,
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repo.add(clip)

    async with AsyncClient(
        transport=ASGITransport(app=fk_video_app), base_url="http://test"
    ) as client:
        resp = await client.delete(f"/api/v1/projects/{project.id}")

    assert resp.status_code == 204

    # Clips were cascade-deleted
    clips_after = await clip_repo.list_by_project(project.id)
    assert clips_after == []


# ---------- Duplicate POST timeline clip returns 409 (BL-410) ----------


@pytest.mark.api
async def test_duplicate_post_timeline_clip_returns_409(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    clip_repository: AsyncInMemoryClipRepository,
) -> None:
    """POST .../timeline/clips twice for same clip returns 409 CLIP_ALREADY_PLACED."""
    from tests.factories import make_test_video

    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-409",
        name="409 Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    await project_repository.add(project)

    track = Track(id="track-409", project_id="proj-409", track_type="video", label="V1", z_index=0)
    await timeline_repository.create_track(track)

    video = make_test_video()
    clip = Clip(
        id="clip-409",
        project_id="proj-409",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await clip_repository.add(clip)

    payload = {
        "clip_id": "clip-409",
        "track_id": "track-409",
        "timeline_start": 0.0,
        "timeline_end": 5.0,
    }

    # First placement → 201
    resp1 = client.post("/api/v1/projects/proj-409/timeline/clips", json=payload)
    assert resp1.status_code == 201

    # Duplicate placement → 409
    resp2 = client.post("/api/v1/projects/proj-409/timeline/clips", json=payload)
    assert resp2.status_code == 409
    body = resp2.json()
    assert body["detail"]["code"] == "CLIP_ALREADY_PLACED"
    assert body["detail"]["existing_track_id"] == "track-409"


# ---------- Preflight hoist: real-mode 422 for incomplete plan (BL-460) ----------


def _build_real_render_service_for_preflight(
    render_repo: InMemoryRenderRepository,
) -> RenderService:
    """Build a real RenderService in real mode with peripherals mocked for preflight tests."""
    from stoat_ferret.api.settings import Settings
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.render.checkpoints import RenderCheckpointManager
    from stoat_ferret.render.executor import RenderExecutor
    from stoat_ferret.render.queue import RenderQueue

    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()

    checkpoint_mgr = MagicMock(spec=RenderCheckpointManager)
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)

    service = RenderService(
        repository=render_repo,
        queue=RenderQueue(render_repo),
        executor=MagicMock(spec=RenderExecutor),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_mode="real"),
    )
    # Override FFmpeg availability so preflight tests run on hosts without FFmpeg.
    service._ffmpeg_available = True
    return service


def _build_noop_render_service_for_preflight(
    render_repo: InMemoryRenderRepository,
) -> RenderService:
    """Build a real RenderService in noop mode for preflight regression tests."""
    from stoat_ferret.api.settings import Settings
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.render.checkpoints import RenderCheckpointManager
    from stoat_ferret.render.executor import RenderExecutor
    from stoat_ferret.render.queue import RenderQueue

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


def _make_preflight_repos() -> tuple[AsyncInMemoryProjectRepository, AsyncInMemoryClipRepository]:
    """Create project and clip repos seeded with TEST_PROJECT_UUID data for preflight tests."""
    now = datetime.now(timezone.utc)
    project_repo = AsyncInMemoryProjectRepository()
    project_repo.seed(
        [
            Project(
                id=TEST_PROJECT_UUID,
                name="Preflight Test Project",
                output_width=1920,
                output_height=1080,
                output_fps=30,
                created_at=now,
                updated_at=now,
            )
        ]
    )
    clip_repo = AsyncInMemoryClipRepository()
    clip_repo.seed(
        [
            Clip(
                id="33333333-3333-3333-3333-333333333333",
                project_id=TEST_PROJECT_UUID,
                source_video_id="vid-preflight",
                in_point=0,
                out_point=100,
                timeline_position=0,
                created_at=now,
                updated_at=now,
            )
        ]
    )
    return project_repo, clip_repo


@pytest.fixture
def real_render_repo() -> InMemoryRenderRepository:
    """Isolated in-memory render repository for real-mode preflight tests."""
    return InMemoryRenderRepository()


@pytest.fixture
def real_preflight_app(real_render_repo: InMemoryRenderRepository) -> FastAPI:
    """Test app with a real RenderService in real (default) mode for preflight tests."""
    project_repo, clip_repo = _make_preflight_repos()
    return create_app(
        render_repository=real_render_repo,
        render_service=_build_real_render_service_for_preflight(real_render_repo),
        project_repository=project_repo,
        clip_repository=clip_repo,
    )


@pytest.fixture
def real_preflight_client(
    real_preflight_app: FastAPI,
) -> Generator[TestClient, None, None]:
    """Test client backed by a real RenderService in real (default) mode."""
    with TestClient(real_preflight_app) as c:
        yield c


@pytest.fixture
def noop_preflight_repo() -> InMemoryRenderRepository:
    """Isolated in-memory render repository for noop-mode preflight regression tests."""
    return InMemoryRenderRepository()


@pytest.fixture
def noop_preflight_app(noop_preflight_repo: InMemoryRenderRepository) -> FastAPI:
    """Test app with a real RenderService in noop mode for preflight regression."""
    project_repo, clip_repo = _make_preflight_repos()
    return create_app(
        render_repository=noop_preflight_repo,
        render_service=_build_noop_render_service_for_preflight(noop_preflight_repo),
        project_repository=project_repo,
        clip_repository=clip_repo,
    )


@pytest.fixture
def noop_preflight_client(
    noop_preflight_app: FastAPI,
) -> Generator[TestClient, None, None]:
    """Test client backed by a real RenderService in noop mode."""
    with TestClient(noop_preflight_app) as c:
        yield c


def test_real_mode_incomplete_plan_returns_422_preflight_failed(
    real_preflight_client: TestClient,
) -> None:
    """FR-001-AC-1: Real-mode POST /render with no total_duration returns 422 PREFLIGHT_FAILED."""
    resp = real_preflight_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "render_plan": "{}"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "PREFLIGHT_FAILED"


def test_real_mode_incomplete_plan_no_db_row_created(
    real_preflight_client: TestClient,
    real_render_repo: InMemoryRenderRepository,
) -> None:
    """FR-001-AC-2: Preflight fires before RenderJob.create(); no DB row created on 422."""
    resp = real_preflight_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "render_plan": "{}"},
    )
    assert resp.status_code == 422
    assert len(real_render_repo._jobs) == 0


def test_real_mode_complete_plan_returns_201(
    real_preflight_client: TestClient,
) -> None:
    """FR-001-AC-3: POST /render with both total_duration and settings returns 201."""
    import json

    resp = real_preflight_client.post(
        "/api/v1/render",
        json={
            "project_id": TEST_PROJECT_UUID,
            "render_plan": json.dumps({"total_duration": 10.0, "settings": {}}),
        },
    )
    assert resp.status_code == 201


def test_real_mode_settings_absent_returns_422_preflight_failed(
    real_preflight_client: TestClient,
) -> None:
    """BL-465-AC-1: Real-mode POST /render with settings absent returns 422 PREFLIGHT_FAILED."""
    import json

    resp = real_preflight_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "render_plan": json.dumps({"total_duration": 10.0})},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "PREFLIGHT_FAILED"
    assert "settings" in resp.json()["detail"]["message"]


def test_noop_mode_incomplete_plan_still_returns_422_preflight_failed(
    noop_preflight_client: TestClient,
) -> None:
    """FR-001-AC-4: Noop-mode 422 behaviour for incomplete plans is preserved (no regression)."""
    resp = noop_preflight_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "render_plan": "{}"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "PREFLIGHT_FAILED"
