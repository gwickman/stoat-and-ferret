"""Smoke tests for batch render quality field enum validation.

Verifies that BatchJobConfig.quality enforces Literal["draft","standard","high"]:
- valid values return HTTP 202
- invalid values (medium, invalid) return HTTP 422 with enum violation
- omitting quality applies default "standard"
"""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.parametrize("quality", ["draft", "standard", "high"])
async def test_batch_quality_valid_values(
    smoke_client: httpx.AsyncClient,
    quality: str,
) -> None:
    """POST /api/v1/render/batch with valid quality values returns 202."""
    resp = await smoke_client.post(
        "/api/v1/render/batch",
        json={"jobs": [{"project_id": "proj-1", "output_path": "/out/1.mp4", "quality": quality}]},
    )
    assert resp.status_code == 202, f"Expected 202 for quality={quality!r}, got {resp.status_code}"


@pytest.mark.parametrize("quality", ["medium", "invalid", "", "HIGH", "Draft"])
async def test_batch_quality_invalid_values(
    smoke_client: httpx.AsyncClient,
    quality: str,
) -> None:
    """POST /api/v1/render/batch with invalid quality values returns 422."""
    resp = await smoke_client.post(
        "/api/v1/render/batch",
        json={"jobs": [{"project_id": "proj-1", "output_path": "/out/1.mp4", "quality": quality}]},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for quality={quality!r}, got {resp.status_code}; body={resp.json()}"
    )
    body = resp.json()
    assert "detail" in body
    detail = body["detail"]
    assert isinstance(detail, list), f"Expected Pydantic list detail, got {type(detail)}"
    error_text = str(detail)
    valid_values = {"draft", "standard", "high"}
    assert any(v in error_text for v in valid_values), (
        f"422 detail should name valid values, got: {detail}"
    )


async def test_batch_quality_default_is_standard(
    smoke_client: httpx.AsyncClient,
) -> None:
    """Omitting quality field defaults to 'standard' (not 'medium')."""
    resp = await smoke_client.post(
        "/api/v1/render/batch",
        json={"jobs": [{"project_id": "proj-1", "output_path": "/out/1.mp4"}]},
    )
    assert resp.status_code == 202
    batch_id = resp.json()["batch_id"]

    progress_resp = await smoke_client.get(f"/api/v1/render/batch/{batch_id}")
    assert progress_resp.status_code == 200
    jobs = progress_resp.json()["jobs"]
    assert len(jobs) == 1
