"""Unit tests for volume automation eval=frame filter string (BL-479)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.effects.definitions import create_default_registry
from tests.factories import make_test_video


@pytest.mark.contract
def test_build_automation_filter_string_contains_eval_frame() -> None:
    """build_automation_filter_string returns volume filter with :eval=frame (BL-479-AC-2)."""
    registry = create_default_registry()
    result = registry.build_automation_filter_string("volume", "0.1+0.08*t")
    assert "eval=frame" in result, f"Expected 'eval=frame' in filter string: {result}"
    assert "volume=" in result, f"Expected 'volume=' in filter string: {result}"


@pytest.mark.contract
def test_build_automation_filter_string_embeds_expression() -> None:
    """build_automation_filter_string wraps the compiled expression in single quotes."""
    registry = create_default_registry()
    expr = "0.1+0.08*t"
    result = registry.build_automation_filter_string("volume", expr)
    assert f"'{expr}'" in result, f"Expected expression quoted in: {result}"


@pytest.mark.contract
def test_build_automation_filter_string_unknown_type_raises() -> None:
    """build_automation_filter_string raises ValueError for non-automatable types."""
    registry = create_default_registry()
    with pytest.raises(ValueError, match="No automation filter string for effect_type"):
        registry.build_automation_filter_string("text_overlay", "some_expr")


@pytest.mark.contract
def test_scalar_volume_filter_has_no_eval_frame() -> None:
    """Scalar volume build_fn does NOT include eval=frame (BL-479-AC-3, static path unchanged)."""
    registry = create_default_registry()
    definition = registry.get("volume")
    assert definition is not None
    filter_str = definition.build_fn({"volume": 0.5})
    assert "eval=frame" not in filter_str, (
        f"eval=frame should not appear in scalar filter string: {filter_str}"
    )


def _make_client_with_clip() -> tuple[TestClient, str, str]:
    """Create a TestClient with a seeded project and clip. Returns (client, project_id, clip_id)."""
    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    video_repo = AsyncInMemoryVideoRepository()

    now = datetime.now(timezone.utc)
    project = Project(
        id="proj-vol-auto",
        name="Test",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    video = make_test_video()
    clip = Clip(
        id="clip-vol-auto",
        project_id="proj-vol-auto",
        source_video_id=video.id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )

    import asyncio

    loop = asyncio.new_event_loop()
    loop.run_until_complete(project_repo.add(project))
    loop.run_until_complete(video_repo.add(video))
    loop.run_until_complete(clip_repo.add(clip))
    loop.close()

    app = create_app(
        project_repository=project_repo,
        clip_repository=clip_repo,
        video_repository=video_repo,
    )
    return TestClient(app), "proj-vol-auto", "clip-vol-auto"


@pytest.mark.api
def test_apply_endpoint_automation_filter_contains_eval_frame() -> None:
    """apply endpoint with automation envelope stores filter_string with :eval=frame.

    BL-479-AC-2.
    """
    with _make_client_with_clip()[0] as client:
        response = client.post(
            "/api/v1/projects/proj-vol-auto/clips/clip-vol-auto/effects",
            json={
                "effect_type": "volume",
                "parameters": {
                    "volume": {
                        "default": 0.1,
                        "keyframes": [
                            {"t": 0.0, "value": 0.1, "curve": "linear"},
                            {"t": 5.0, "value": 0.9, "curve": "linear"},
                        ],
                    }
                },
            },
        )
    assert response.status_code == 201, f"Expected 201: {response.json()}"
    data = response.json()
    assert "eval=frame" in data["filter_string"], (
        f"Expected 'eval=frame' in apply filter_string: {data['filter_string']}"
    )


@pytest.mark.api
def test_update_endpoint_automation_filter_contains_eval_frame() -> None:
    """update endpoint with automation envelope stores filter_string with :eval=frame.

    BL-479-AC-2.
    """
    client_ctx, proj_id, clip_id = _make_client_with_clip()
    with client_ctx as client:
        apply_resp = client.post(
            f"/api/v1/projects/{proj_id}/clips/{clip_id}/effects",
            json={"effect_type": "volume", "parameters": {"volume": 0.5}},
        )
        assert apply_resp.status_code == 201

        update_resp = client.patch(
            f"/api/v1/projects/{proj_id}/clips/{clip_id}/effects/0",
            json={
                "parameters": {
                    "volume": {
                        "default": 0.1,
                        "keyframes": [
                            {"t": 0.0, "value": 0.1, "curve": "linear"},
                            {"t": 5.0, "value": 0.9, "curve": "linear"},
                        ],
                    }
                }
            },
        )
    assert update_resp.status_code == 200, f"Expected 200: {update_resp.json()}"
    data = update_resp.json()
    assert "eval=frame" in data["filter_string"], (
        f"Expected 'eval=frame' in update filter_string: {data['filter_string']}"
    )
