# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
from __future__ import annotations

import httpx


async def test_source_endpoint_returns_200(smoke_client: httpx.AsyncClient) -> None:
    resp = await smoke_client.get("/api/v1/source")
    assert resp.status_code == 200


async def test_source_endpoint_response_structure(smoke_client: httpx.AsyncClient) -> None:
    resp = await smoke_client.get("/api/v1/source")
    body = resp.json()
    assert "source_url" in body
    assert "version" in body
    assert "commit" in body
    assert body["license"] == "AGPL-3.0-or-later"
