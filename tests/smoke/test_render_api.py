"""Smoke tests for render API endpoints.

Validates render CRUD operations, encoder discovery, format listing,
queue status, cancel, retry, and encoder refresh via the full fixture chain
(HTTP -> FastAPI -> Services).
"""

from __future__ import annotations

import httpx

from stoat_ferret.render.models import RenderStatus


async def test_render_create(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/render returns 201 with a valid job_id."""
    # Create a minimal project to render
    proj_resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Render Smoke Test"},
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

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
