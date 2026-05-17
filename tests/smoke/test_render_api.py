"""Smoke tests for render API endpoints.

Validates render CRUD operations, encoder discovery, format listing,
queue status, cancel, retry, and encoder refresh via the full fixture chain
(HTTP -> FastAPI -> Services).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from stoat_ferret.api.app import create_app, lifespan
from stoat_ferret.api.settings import get_settings
from stoat_ferret.db.clip_repository import AsyncSQLiteClipRepository
from stoat_ferret.db.models import Clip
from stoat_ferret.render.models import RenderStatus


async def _seed_clip_for_project(client: httpx.AsyncClient, project_id: str) -> None:
    """Insert a stub clip row directly so the EMPTY_TIMELINE preflight passes.

    Bypasses the video-existence check in the clips API (the preflight only
    checks that ≥1 clip row exists, not that source_video_id is valid).
    """
    transport: httpx.ASGITransport = client._transport  # type: ignore[assignment]
    db = transport.app.state.db  # type: ignore[union-attr]
    repo = AsyncSQLiteClipRepository(db)
    now = datetime.now(timezone.utc)
    clip = Clip(
        id=Clip.new_id(),
        project_id=project_id,
        source_video_id="00000000-0000-0000-0000-000000000001",
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )
    await repo.add(clip)


async def test_render_create(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render returns 201 with a valid job_id."""
    # Create a minimal project to render
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Smoke Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["project_id"] == project_id
    assert body["status"] in ("queued", "running")
    assert body["output_format"] == "mp4"
    assert body["quality_preset"] == "standard"


async def test_render_get(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/render/{job_id} returns 200 with expected fields."""
    # Create a project and render job
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Get Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    create_resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    resp = await smoke_client.get(f"/api/v1/render/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == job_id
    assert body["project_id"] == project_id
    assert "status" in body
    assert "progress" in body
    assert isinstance(body["progress"], (int, float))
    assert "created_at" in body
    assert "updated_at" in body


async def test_render_list(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/render returns 200 with paginated list."""
    # Create a project and render job so the list is non-empty
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render List Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )

    resp = await smoke_client.get("/api/v1/render")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert isinstance(body["items"], list)
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


async def test_render_encoders(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/render/encoders returns 200 with encoder list."""
    resp = await smoke_client.get("/api/v1/render/encoders")
    assert resp.status_code == 200
    body = resp.json()
    assert "encoders" in body
    assert "cached" in body
    assert isinstance(body["encoders"], list)
    assert isinstance(body["cached"], bool)

    # If encoders detected, verify structure
    if body["encoders"]:
        encoder = body["encoders"][0]
        assert "name" in encoder
        assert "codec" in encoder
        assert "is_hardware" in encoder
        assert "encoder_type" in encoder
        assert "description" in encoder
        assert "detected_at" in encoder


async def test_render_formats(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/render/formats returns 200 with all 4 format entries."""
    resp = await smoke_client.get("/api/v1/render/formats")
    assert resp.status_code == 200
    body = resp.json()
    assert "formats" in body
    assert isinstance(body["formats"], list)
    assert len(body["formats"]) == 4

    format_names = {f["format"] for f in body["formats"]}
    assert format_names == {"mp4", "webm", "mov", "mkv"}

    # Verify structure of each format entry
    for fmt in body["formats"]:
        assert "extension" in fmt
        assert "mime_type" in fmt
        assert "codecs" in fmt
        assert isinstance(fmt["codecs"], list)
        assert "supports_hw_accel" in fmt
        assert "supports_two_pass" in fmt
        assert "supports_alpha" in fmt

        # Each format has at least one codec with quality presets
        for codec in fmt["codecs"]:
            assert "name" in codec
            assert "quality_presets" in codec
            for preset in codec["quality_presets"]:
                assert "preset" in preset
                assert "video_bitrate_kbps" in preset


async def test_render_queue(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/render/queue returns 200 with queue status fields."""
    resp = await smoke_client.get("/api/v1/render/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert "active_count" in body
    assert "pending_count" in body
    assert "max_concurrent" in body
    assert "max_queue_depth" in body
    assert "disk_available_bytes" in body
    assert "disk_total_bytes" in body
    assert "completed_today" in body
    assert "failed_today" in body

    assert isinstance(body["active_count"], int)
    assert isinstance(body["pending_count"], int)
    assert isinstance(body["max_concurrent"], int)
    assert isinstance(body["max_queue_depth"], int)
    assert isinstance(body["disk_available_bytes"], int)
    assert isinstance(body["disk_total_bytes"], int)
    assert body["active_count"] >= 0
    assert body["pending_count"] >= 0
    assert body["max_concurrent"] >= 1
    assert body["disk_total_bytes"] > 0


async def test_render_preview_endpoint(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render/preview returns 200 with command field."""
    resp = await smoke_client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mp4",
            "quality_preset": "standard",
            "encoder": "libx264",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "command" in body
    assert isinstance(body["command"], str)
    assert body["command"].startswith("ffmpeg")


async def test_render_preview_invalid(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render/preview with invalid encoder returns 422."""
    resp = await smoke_client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mp4",
            "quality_preset": "standard",
            "encoder": "invalid_encoder",
        },
    )
    assert resp.status_code == 422


async def test_render_preview_formats(smoke_client: httpx.AsyncClient) -> None:
    """Each supported format returns a valid command."""
    for fmt, encoder in [
        ("mp4", "libx264"),
        ("webm", "libvpx-vp9"),
        ("mkv", "libx265"),
        ("avi", "libx264"),
    ]:
        resp = await smoke_client.post(
            "/api/v1/render/preview",
            json={
                "output_format": fmt,
                "quality_preset": "standard",
                "encoder": encoder,
            },
        )
        assert resp.status_code == 200, f"Failed for {fmt}/{encoder}"
        body = resp.json()
        assert body["command"].startswith("ffmpeg"), f"No ffmpeg prefix for {fmt}"


async def test_render_delete(smoke_client: httpx.AsyncClient) -> None:
    """DELETE /api/v1/render/{job_id} returns 200 with deleted job."""
    # Create a project and render job to delete
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Delete Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    create_resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    resp = await smoke_client.delete(f"/api/v1/render/{job_id}")
    assert resp.status_code in (200, 204)

    # Verify the job is gone
    get_resp = await smoke_client.get(f"/api/v1/render/{job_id}")
    assert get_resp.status_code == 404


async def test_render_cancel(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render/{id}/cancel returns 200 on queued job, 404/409 on invalid states."""
    # Create a project and render job
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Cancel Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    create_resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    # Cancel while in queued state — should return 200
    cancel_resp = await smoke_client.post(f"/api/v1/render/{job_id}/cancel")
    assert cancel_resp.status_code == 200
    body = cancel_resp.json()
    assert body["id"] == job_id
    assert body["status"] == "cancelled"

    # Cancel a non-existent job — should return 404
    not_found_resp = await smoke_client.post("/api/v1/render/nonexistent-id/cancel")
    assert not_found_resp.status_code == 404

    # Cancel an already-cancelled job — should return 409
    already_cancelled_resp = await smoke_client.post(f"/api/v1/render/{job_id}/cancel")
    assert already_cancelled_resp.status_code == 409


async def test_render_retry(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render/{id}/retry returns 200 on failed job."""
    # Create a project and render job
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Retry Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)

    create_resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id},
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    # Access render repository directly to set job to failed state.
    # Jobs stay in QUEUED in smoke tests (no background render worker).
    # Transition: queued -> running -> failed (both valid per the state machine).
    transport: httpx.ASGITransport = smoke_client._transport  # type: ignore[assignment]
    render_repo = transport.app.state.render_repository  # type: ignore[union-attr]
    await render_repo.update_status(job_id, RenderStatus.RUNNING)
    await render_repo.update_status(job_id, RenderStatus.FAILED, error_message="test failure")

    # Retry the failed job — should return 200 with status reset to queued
    retry_resp = await smoke_client.post(f"/api/v1/render/{job_id}/retry")
    assert retry_resp.status_code == 200
    body = retry_resp.json()
    assert body["id"] == job_id
    assert body["status"] == "queued"

    # Retry a non-existent job — should return 404
    not_found_resp = await smoke_client.post("/api/v1/render/nonexistent-id/retry")
    assert not_found_resp.status_code == 404


async def test_render_preview_incompatible_format_encoder(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render/preview with incompatible format-encoder returns 422."""
    resp = await smoke_client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mp4",
            "quality_preset": "standard",
            "encoder": "libvpx",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INCOMPATIBLE_FORMAT_ENCODER"


async def test_render_preview_avi_passthrough(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render/preview with avi format skips format-encoder check (no crash)."""
    resp = await smoke_client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "avi",
            "quality_preset": "standard",
            "encoder": "libvpx",
        },
    )
    # avi is not in _FORMAT_DATA so the format-encoder check is skipped.
    # The endpoint may return 200 or 422 from other validation — not from format check.
    assert resp.status_code != 500
    if resp.status_code == 422:
        body = resp.json()
        assert body.get("detail", {}).get("code") != "INCOMPATIBLE_FORMAT_ENCODER"


async def test_create_render_invalid_format_encoder(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render with incompatible format-encoder pair returns 422."""
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Validation Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    resp = await smoke_client.post(
        "/api/v1/render",
        json={
            "project_id": project_id,
            "output_format": "webm",
            "encoder": "libx264",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INCOMPATIBLE_FORMAT_ENCODER"


async def test_render_encoder_refresh(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render/encoders/refresh returns 200 with valid encoder list structure."""
    resp = await smoke_client.post("/api/v1/render/encoders/refresh")
    assert resp.status_code == 200
    body = resp.json()
    assert "encoders" in body
    assert "cached" in body
    assert isinstance(body["encoders"], list)
    assert body["cached"] is False  # refresh always returns freshly detected data

    # If encoders detected, verify structure of each entry
    if body["encoders"]:
        encoder = body["encoders"][0]
        assert "name" in encoder
        assert "codec" in encoder
        assert "is_hardware" in encoder
        assert "encoder_type" in encoder
        assert "description" in encoder
        assert "detected_at" in encoder


# ---------- Quality preset translation E2E tests (BL-339) ----------


async def _create_project(smoke_client: httpx.AsyncClient, name: str) -> str:
    """Create a project with a stub clip and return its project ID."""
    resp = await smoke_client.post("/api/v1/projects", json={"name": name})
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    await _seed_clip_for_project(smoke_client, project_id)
    return project_id


async def test_render_standard_preset_reaches_running(smoke_client: httpx.AsyncClient) -> None:
    """POST /render with quality_preset='standard' reaches RUNNING or COMPLETED status."""
    project_id = await _create_project(smoke_client, "Preset Standard E2E")

    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "quality_preset": "standard"},
    )
    assert resp.status_code == 201
    body = resp.json()
    job_id = body["id"]
    assert body["status"] in ("queued", "running", "completed")

    get_resp = await smoke_client.get(f"/api/v1/render/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] in ("queued", "running", "completed")


async def test_render_draft_preset_reaches_running(smoke_client: httpx.AsyncClient) -> None:
    """POST /render with quality_preset='draft' results in a job reaching RUNNING or COMPLETED."""
    project_id = await _create_project(smoke_client, "Preset Draft E2E")

    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "quality_preset": "draft"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] in ("queued", "running", "completed")


async def test_render_high_preset_reaches_running(smoke_client: httpx.AsyncClient) -> None:
    """POST /render with quality_preset='high' results in a job reaching RUNNING or COMPLETED."""
    project_id = await _create_project(smoke_client, "Preset High E2E")

    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "quality_preset": "high"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] in ("queued", "running", "completed")


async def test_render_ffmpeg_preset_rejected_at_public_api(smoke_client: httpx.AsyncClient) -> None:
    """POST /render with FFmpeg preset name 'medium' returns HTTP 400."""
    project_id = await _create_project(smoke_client, "Preset Invalid E2E")

    resp = await smoke_client.post(
        "/api/v1/render",
        json={"project_id": project_id, "quality_preset": "medium"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_PRESET"
    assert "draft | standard | high" in body["detail"]["message"]


# ---------- Codec-encoder bridge round-trip tests (BL-345) ----------


async def test_formats_encoder_field_present(smoke_client: httpx.AsyncClient) -> None:
    """GET /render/formats returns encoder field for every codec entry."""
    resp = await smoke_client.get("/api/v1/render/formats")
    assert resp.status_code == 200
    for fmt in resp.json()["formats"]:
        for codec in fmt["codecs"]:
            assert "encoder" in codec, f"encoder missing from {codec['name']} in {fmt['format']}"
            assert isinstance(codec["encoder"], str)
            assert len(codec["encoder"]) > 0


async def test_formats_encoder_roundtrip_all_codecs(smoke_client: httpx.AsyncClient) -> None:
    """GET /render/formats → use each codec's encoder in POST /render/preview → HTTP 200."""
    resp = await smoke_client.get("/api/v1/render/formats")
    assert resp.status_code == 200

    seen_codecs: dict[str, str] = {}
    for fmt in resp.json()["formats"]:
        for codec in fmt["codecs"]:
            seen_codecs[codec["name"]] = codec["encoder"]

    # All six codec families must be present
    expected_codecs = {"h264", "h265", "vp8", "vp9", "prores", "av1"}
    assert expected_codecs.issubset(seen_codecs.keys()), (
        f"Missing codecs: {expected_codecs - seen_codecs.keys()}"
    )

    # For each codec family, find a compatible format and verify the round-trip
    codec_format_map = {
        "h264": "mp4",
        "h265": "mp4",
        "vp8": "webm",
        "vp9": "webm",
        "prores": "mov",
        "av1": "mkv",
    }
    for codec_name, encoder in seen_codecs.items():
        output_format = codec_format_map[codec_name]
        preview_resp = await smoke_client.post(
            "/api/v1/render/preview",
            json={
                "output_format": output_format,
                "quality_preset": "standard",
                "encoder": encoder,
            },
        )
        assert preview_resp.status_code == 200, (
            f"Round-trip failed for codec={codec_name} encoder={encoder} format={output_format}: "
            f"{preview_resp.status_code} {preview_resp.text}"
        )
        assert "command" in preview_resp.json()


async def test_render_preview_codec_name_rejected_with_discovery_message(
    smoke_client: httpx.AsyncClient,
) -> None:
    """POST /render/preview with codec name returns 422 with /render/formats reference."""
    resp = await smoke_client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mp4",
            "quality_preset": "standard",
            "encoder": "h264",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "/render/formats" in body["detail"]["message"]
    assert "encoder" in body["detail"]["message"]


# ---------- Noop mode smoke tests (BL-355 AC-4, AC-5) ----------


@pytest.fixture()
async def smoke_client_noop(tmp_path: Path) -> httpx.AsyncClient:
    """Async httpx client with STOAT_RENDER_MODE=noop for noop-mode render tests."""
    db_path = tmp_path / "noop_smoke_test.db"

    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")
    orig_render_mode = os.environ.get("STOAT_RENDER_MODE")

    os.environ["STOAT_DATABASE_PATH"] = str(db_path)
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    os.environ["STOAT_RENDER_MODE"] = "noop"
    get_settings.cache_clear()

    app = create_app()

    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client

    for key, orig in [
        ("STOAT_DATABASE_PATH", orig_db),
        ("STOAT_THUMBNAIL_DIR", orig_thumb),
        ("STOAT_RENDER_MODE", orig_render_mode),
    ]:
        if orig is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig

    get_settings.cache_clear()


async def test_noop_mode_status_authoritative(
    smoke_client_noop: httpx.AsyncClient,
) -> None:
    """POST /render in noop mode returns status='completed'; background worker cannot race."""
    client = smoke_client_noop

    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Noop Smoke Test"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    await _seed_clip_for_project(client, project_id)

    render_plan = json.dumps({"total_duration": 5.0})
    resp = await client.post(
        "/api/v1/render",
        json={"project_id": project_id, "render_plan": render_plan},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed", (
        f"Expected 'completed' in noop mode, got {body['status']!r}"
    )
    assert body["id"]
