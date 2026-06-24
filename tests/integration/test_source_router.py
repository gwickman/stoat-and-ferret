# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Integration tests for GET /api/v1/source (BL-525)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_source_returns_200_with_all_fields(client: TestClient) -> None:
    """GET /api/v1/source returns 200 with all four required fields."""
    resp = client.get("/api/v1/source")
    assert resp.status_code == 200
    body = resp.json()
    assert "source_url" in body
    assert "version" in body
    assert "commit" in body
    assert body["license"] == "AGPL-3.0-or-later"


def test_source_url_override(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """STOAT_SOURCE_URL override propagates to response."""
    from stoat_ferret.api.settings import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("STOAT_SOURCE_URL", "https://example.com/custom-source")
    try:
        resp = client.get("/api/v1/source")
        assert resp.json()["source_url"] == "https://example.com/custom-source"
    finally:
        get_settings.cache_clear()


def test_absent_build_commit_returns_unknown(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Absent STOAT_BUILD_COMMIT returns commit: 'unknown'."""
    from stoat_ferret.api.settings import get_settings

    get_settings.cache_clear()
    monkeypatch.delenv("STOAT_BUILD_COMMIT", raising=False)
    try:
        resp = client.get("/api/v1/source")
        assert resp.json()["commit"] == "unknown"
    finally:
        get_settings.cache_clear()


def test_source_response_all_fields_non_null(client: TestClient) -> None:
    """GET /api/v1/source returns all four required fields as non-empty strings (BL-539)."""
    resp = client.get("/api/v1/source")
    assert resp.status_code == 200
    data = resp.json()
    for field in ("source_url", "version", "commit", "license"):
        assert isinstance(data.get(field), str), f"field '{field}' missing or not a string"
        assert data[field], f"field '{field}' is empty"


def test_source_openapi_required_fields(client: TestClient) -> None:
    """OpenAPI schema for GET /api/v1/source has required array with all four fields (BL-539)."""
    resp = client.get("/openapi.json")
    schema = resp.json()
    source_schema = schema["paths"]["/api/v1/source"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    ref = source_schema.get("$ref", "")
    if ref:
        component_name = ref.split("/")[-1]
        component = schema["components"]["schemas"][component_name]
        required = component.get("required", [])
    else:
        required = source_schema.get("required", [])
    for field in ("source_url", "version", "commit", "license"):
        assert field in required, f"'{field}' not in OpenAPI required array"
