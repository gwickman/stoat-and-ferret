"""Unit tests for render API quality_preset translation layer.

Covers the QUALITY_PRESET_MAP constant, public-to-FFmpeg vocabulary translation,
and validation that public API rejects FFmpeg preset names and invalid values.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.routers.render import _CODEC_ENCODER_MAP, QUALITY_PRESET_MAP
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService
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
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "draft"},
    )
    assert resp.status_code == 201
    assert resp.json()["quality_preset"] == "draft"


def test_valid_preset_standard_accepted(render_client: TestClient) -> None:
    """POST /render with quality_preset='standard' returns 201."""
    resp = render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "standard"},
    )
    assert resp.status_code == 201
    assert resp.json()["quality_preset"] == "standard"


def test_valid_preset_high_accepted(render_client: TestClient) -> None:
    """POST /render with quality_preset='high' returns 201."""
    resp = render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "high"},
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
    import json

    render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "draft"},
    )
    call_kwargs = mock_render_service.submit_job.call_args.kwargs
    plan = json.loads(call_kwargs["render_plan_json"])
    assert plan["settings"]["quality_preset"] == "veryfast"


def test_standard_translated_in_render_plan(
    render_client: TestClient,
    mock_render_service: AsyncMock,
) -> None:
    """standard preset translates to 'medium' in the render_plan passed to service."""
    import json

    render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "standard"},
    )
    call_kwargs = mock_render_service.submit_job.call_args.kwargs
    plan = json.loads(call_kwargs["render_plan_json"])
    assert plan["settings"]["quality_preset"] == "medium"


def test_high_translated_in_render_plan(
    render_client: TestClient,
    mock_render_service: AsyncMock,
) -> None:
    """high preset translates to 'slow' in the render_plan passed to service."""
    import json

    render_client.post(
        "/api/v1/render",
        json={"project_id": TEST_PROJECT_UUID, "quality_preset": "high"},
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
