"""Tests for POST /render/preview endpoint.

Validates that the render preview returns FFmpeg command strings for
valid format/encoder/quality combinations, and 422 for invalid ones.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_preview_valid_mp4_libx264(client: TestClient) -> None:
    """Valid mp4/libx264/standard request returns 200 with ffmpeg command."""
    resp = client.post(
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
    assert body["command"].startswith("ffmpeg")
    assert "libx264" in body["command"]


def test_preview_valid_webm_vp9(client: TestClient) -> None:
    """Valid webm/libvpx-vp9/high request returns 200."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "webm",
            "quality_preset": "high",
            "encoder": "libvpx-vp9",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["command"].startswith("ffmpeg")
    assert "libvpx-vp9" in body["command"]


def test_preview_valid_mkv_libx265(client: TestClient) -> None:
    """Valid mkv/libx265/draft request returns 200."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mkv",
            "quality_preset": "draft",
            "encoder": "libx265",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["command"].startswith("ffmpeg")
    assert "libx265" in body["command"]


def test_preview_valid_avi(client: TestClient) -> None:
    """Valid avi format returns 200."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "avi",
            "quality_preset": "standard",
            "encoder": "libx264",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["command"].startswith("ffmpeg")


def test_preview_valid_mov(client: TestClient) -> None:
    """Valid mov format returns 200."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mov",
            "quality_preset": "standard",
            "encoder": "libx264",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["command"].startswith("ffmpeg")


def test_preview_invalid_format_returns_422(client: TestClient) -> None:
    """Unsupported output format returns 422."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "flv",
            "quality_preset": "standard",
            "encoder": "libx264",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_RENDER_SETTINGS"


def test_preview_invalid_encoder_returns_422(client: TestClient) -> None:
    """Unsupported encoder returns 422."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mp4",
            "quality_preset": "standard",
            "encoder": "not_a_real_encoder",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_RENDER_SETTINGS"


def test_preview_invalid_quality_preset_returns_422(client: TestClient) -> None:
    """Unsupported quality preset returns 422."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mp4",
            "quality_preset": "ultra",
            "encoder": "libx264",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_QUALITY_PRESET"


def test_preview_missing_required_field_returns_422(client: TestClient) -> None:
    """Missing required field returns 422 (Pydantic validation)."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "mp4",
            "quality_preset": "standard",
            # encoder missing
        },
    )
    assert resp.status_code == 422


def test_preview_command_contains_format_flag(client: TestClient) -> None:
    """Returned command includes the -f format flag matching the request."""
    resp = client.post(
        "/api/v1/render/preview",
        json={
            "output_format": "webm",
            "quality_preset": "draft",
            "encoder": "libvpx-vp9",
        },
    )
    assert resp.status_code == 200
    cmd = resp.json()["command"]
    # The command should contain -f webm
    assert "-f webm" in cmd


def test_preview_is_stateless(client: TestClient) -> None:
    """Calling preview twice with same args returns identical results."""
    payload = {
        "output_format": "mp4",
        "quality_preset": "standard",
        "encoder": "libx264",
    }
    resp1 = client.post("/api/v1/render/preview", json=payload)
    resp2 = client.post("/api/v1/render/preview", json=payload)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()
