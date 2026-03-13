"""Smoke tests for audio mix configuration and preview.

Validates configuring an audio mix for a project and previewing
a mix filter chain through the full HTTP stack with real Rust core.
"""

from __future__ import annotations

import httpx


async def test_audio_mix_configure(smoke_client: httpx.AsyncClient) -> None:
    """PUT /api/v1/projects/{id}/audio/mix returns 200 with filter preview."""
    client = smoke_client

    # Create a project
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Audio Smoke Project"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Configure audio mix with 2 tracks
    resp = await client.put(
        f"/api/v1/projects/{project_id}/audio/mix",
        json={
            "tracks": [
                {"volume": 1.0, "fade_in": 0.5, "fade_out": 0.5},
                {"volume": 0.8, "fade_in": 0.0, "fade_out": 1.0},
            ],
            "master_volume": 1.0,
            "normalize": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tracks_configured"] == 2
    assert isinstance(body["filter_preview"], str)
    assert len(body["filter_preview"]) > 0


async def test_audio_mix_preview(smoke_client: httpx.AsyncClient) -> None:
    """POST /api/v1/audio/mix/preview returns 200 with filter chain."""
    resp = await smoke_client.post(
        "/api/v1/audio/mix/preview",
        json={
            "tracks": [
                {"volume": 1.0, "fade_in": 0.0, "fade_out": 0.0},
                {"volume": 0.5, "fade_in": 1.0, "fade_out": 0.5},
            ],
            "master_volume": 0.9,
            "normalize": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tracks_configured"] == 2
    assert isinstance(body["filter_preview"], str)
    assert len(body["filter_preview"]) > 0
