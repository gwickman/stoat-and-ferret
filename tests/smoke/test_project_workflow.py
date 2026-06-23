# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke tests for project CRUD (UC-03) and project deletion (UC-09).

Validates creating, listing, retrieving, and deleting projects through the
full backend stack.
"""

from __future__ import annotations

import httpx


async def test_uc03_project_crud(smoke_client: httpx.AsyncClient) -> None:
    """Create projects with default and custom settings, list, retrieve, and validate."""
    # Create project with default output settings
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "Default Project"},
    )
    assert resp.status_code == 201
    default_proj = resp.json()
    assert default_proj["name"] == "Default Project"
    assert default_proj["output_width"] == 1920
    assert default_proj["output_height"] == 1080
    assert default_proj["output_fps"] == 30

    # Create project with custom output settings
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={
            "name": "Custom Project",
            "output_width": 1280,
            "output_height": 720,
            "output_fps": 60,
        },
    )
    assert resp.status_code == 201
    custom_proj = resp.json()
    assert custom_proj["output_width"] == 1280
    assert custom_proj["output_height"] == 720
    assert custom_proj["output_fps"] == 60

    # List projects — both should appear
    resp = await smoke_client.get("/api/v1/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    project_ids = {p["id"] for p in body["projects"]}
    assert default_proj["id"] in project_ids
    assert custom_proj["id"] in project_ids

    # Retrieve by ID
    resp = await smoke_client.get(f"/api/v1/projects/{custom_proj['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == custom_proj["id"]
    assert resp.json()["name"] == "Custom Project"

    # Validation: empty name returns 422
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": ""},
    )
    assert resp.status_code == 422


async def test_uc09_project_deletion(smoke_client: httpx.AsyncClient) -> None:
    """Delete a project and verify idempotent behavior."""
    # Create a project
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={"name": "To Delete"},
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # Delete returns 204
    resp = await smoke_client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 204

    # Re-fetch returns 404
    resp = await smoke_client.get(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404

    # Double-delete returns 404
    resp = await smoke_client.delete(f"/api/v1/projects/{project_id}")
    assert resp.status_code == 404


async def test_project_create_audio_defaults(smoke_client: httpx.AsyncClient) -> None:
    """Project created without audio fields has default sample_rate=48000, bit_depth=24."""
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={
            "name": "Audio Defaults Test",
            "output_width": 1920,
            "output_height": 1080,
            "output_fps": 30,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["sample_rate"] == 48000
    assert data["bit_depth"] == 24


async def test_project_create_with_explicit_audio(smoke_client: httpx.AsyncClient) -> None:
    """Project created with explicit audio fields persists and returns those values."""
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={
            "name": "Explicit Audio Test",
            "output_width": 1920,
            "output_height": 1080,
            "output_fps": 30,
            "sample_rate": 96000,
            "bit_depth": 16,
        },
    )
    assert resp.status_code == 201
    pid = resp.json()["id"]
    resp = await smoke_client.get(f"/api/v1/projects/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_rate"] == 96000
    assert data["bit_depth"] == 16


async def test_project_create_invalid_sample_rate(smoke_client: httpx.AsyncClient) -> None:
    """Invalid sample_rate (22050 not in allowed set) → 422."""
    resp = await smoke_client.post(
        "/api/v1/projects",
        json={
            "name": "Invalid Audio Test",
            "output_width": 1920,
            "output_height": 1080,
            "output_fps": 30,
            "sample_rate": 22050,
        },
    )
    assert resp.status_code == 422
