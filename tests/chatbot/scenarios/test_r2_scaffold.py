"""Tests for the R2 chatbot scenario runner hook."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.chatbot.scenarios.r2_scaffold import run_r2_scenario

_UC_MPS_001 = "tests.chatbot.scenarios.r2_scaffold.run_uc_media_mps_001"

_SCAFFOLD_RESULT = {
    "uc_id": "UC-MEDIA-MPS-001",
    "project_id": "proj-test-123",
    "profile_id": "prof-test-456",
    "render_job_id": "job-test-789",
    "qc_report": {},
    "status": "scaffold",
}


async def test_run_r2_scenario_returns_structured_dict() -> None:
    """run_r2_scenario delegates to uc_media_mps_001 and returns its dict."""
    with patch(_UC_MPS_001, new=AsyncMock(return_value=_SCAFFOLD_RESULT)):
        result = await run_r2_scenario("http://localhost:8765")

    assert isinstance(result, dict)
    assert "project_id" in result
    assert "qc_report" in result
    assert "status" in result


async def test_run_r2_scenario_project_id_from_api() -> None:
    """run_r2_scenario returns the project_id from uc_media_mps_001."""
    with patch(_UC_MPS_001, new=AsyncMock(return_value=_SCAFFOLD_RESULT)):
        result = await run_r2_scenario("http://localhost:8765")

    assert result["project_id"] == "proj-test-123"


async def test_run_r2_scenario_uc_id_present() -> None:
    """run_r2_scenario result contains UC-MEDIA-MPS-001 scenario identifier."""
    with patch(_UC_MPS_001, new=AsyncMock(return_value=_SCAFFOLD_RESULT)):
        result = await run_r2_scenario("http://localhost:8765")

    assert result.get("uc_id") == "UC-MEDIA-MPS-001"


async def test_run_r2_scenario_delegates_base_url() -> None:
    """run_r2_scenario passes base_url through to uc_media_mps_001."""
    mock = AsyncMock(return_value=_SCAFFOLD_RESULT)
    with patch(_UC_MPS_001, new=mock):
        await run_r2_scenario("http://localhost:8765")

    mock.assert_called_once_with("http://localhost:8765")
