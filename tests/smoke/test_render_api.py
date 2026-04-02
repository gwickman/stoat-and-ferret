"""Smoke tests for render API endpoints.

Validates render CRUD operations, encoder discovery, format listing,
and queue status via the full fixture chain (HTTP -> FastAPI -> Services).
"""

from __future__ import annotations

import httpx


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
