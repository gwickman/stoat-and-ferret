"""Tests for the R2 chatbot scenario runner hook."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.chatbot.scenarios.r2_scaffold import run_r2_scenario

_PATCH_TARGET = "tests.chatbot.scenarios.r2_scaffold.httpx.AsyncClient"


@pytest.fixture
def mock_project_response() -> MagicMock:
    """Mock httpx response for project creation."""
    resp = MagicMock()
    resp.json.return_value = {"id": "proj-test-123"}
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def mock_http_client(mock_project_response: MagicMock) -> AsyncMock:
    """Mock httpx.AsyncClient that returns a stub project response."""
    client = AsyncMock()
    client.post = AsyncMock(return_value=mock_project_response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


async def test_run_r2_scenario_returns_structured_dict(mock_http_client: AsyncMock) -> None:
    """run_r2_scenario drives the REST API and returns a structured dict."""
    with patch(_PATCH_TARGET, return_value=mock_http_client):
        result = await run_r2_scenario("http://localhost:8765")

    assert isinstance(result, dict)
    assert "project_id" in result
    assert "qc_report" in result
    assert "status" in result


async def test_run_r2_scenario_project_id_from_api(mock_http_client: AsyncMock) -> None:
    """run_r2_scenario uses the project id returned by the REST API."""
    with patch(_PATCH_TARGET, return_value=mock_http_client):
        result = await run_r2_scenario("http://localhost:8765")

    assert result["project_id"] == "proj-test-123"


async def test_run_r2_scenario_stub_qc_report(mock_http_client: AsyncMock) -> None:
    """run_r2_scenario returns a stub QC report (empty dict) when QCService unavailable."""
    with patch(_PATCH_TARGET, return_value=mock_http_client):
        result = await run_r2_scenario("http://localhost:8765")

    assert result["qc_report"] == {}
    assert result["status"] == "scaffold"


async def test_run_r2_scenario_calls_projects_endpoint(mock_http_client: AsyncMock) -> None:
    """run_r2_scenario posts to the /api/v1/projects endpoint."""
    with patch(_PATCH_TARGET, return_value=mock_http_client):
        await run_r2_scenario("http://localhost:8765")

    mock_http_client.post.assert_called_once()
    call_args = mock_http_client.post.call_args
    assert call_args[0][0] == "/api/v1/projects"
