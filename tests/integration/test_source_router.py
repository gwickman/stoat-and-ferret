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
