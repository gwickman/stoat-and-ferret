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
    for field in ("source_url", "version", "commit", "license"):
        assert field in body, f"Response missing field '{field}'"
        assert isinstance(body[field], str), f"Field '{field}' is not a string"
        assert body[field], f"Field '{field}' is empty"
    assert body["license"] == "AGPL-3.0-or-later"
