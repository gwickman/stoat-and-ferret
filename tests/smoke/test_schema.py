"""Smoke tests for GET /api/v1/schema/{resource} endpoint (BL-271)."""

from __future__ import annotations

import httpx
import pytest


async def test_schema_project(smoke_client: httpx.AsyncClient) -> None:
    """GET /api/v1/schema/project returns a JSON Schema with the expected properties.

    Asserts ``properties.id``, ``properties.name``, and ``properties.created_at``
    are present — this proves the Pydantic model fields flow through to the
    response rather than a stub or empty object.
    """
    resp = await smoke_client.get("/api/v1/schema/project")
    assert resp.status_code == 200
    schema = resp.json()
    assert "properties" in schema
    properties = schema["properties"]
    for field in ("id", "name", "created_at"):
        assert field in properties, f"missing property: {field}"


@pytest.mark.parametrize(
    "resource",
    ["clip", "timeline", "render_job", "effect", "video"],
)
async def test_schema_resource_returns_properties(
    smoke_client: httpx.AsyncClient, resource: str
) -> None:
    """GET /api/v1/schema/{resource} returns 200 with a non-empty ``properties`` dict."""
    resp = await smoke_client.get(f"/api/v1/schema/{resource}")
    assert resp.status_code == 200, f"{resource}: expected 200, got {resp.status_code}"
    schema = resp.json()
    assert "properties" in schema, f"{resource}: missing 'properties' key"
    assert isinstance(schema["properties"], dict), f"{resource}: properties must be a dict"
    assert len(schema["properties"]) > 0, f"{resource}: properties must be non-empty"


async def test_schema_unknown_resource_returns_404(
    smoke_client: httpx.AsyncClient,
) -> None:
    """GET /api/v1/schema/unknown-resource returns HTTP 404."""
    resp = await smoke_client.get("/api/v1/schema/unknown-resource")
    assert resp.status_code == 404
