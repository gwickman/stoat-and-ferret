"""Chatbot scenario: uc_cap_reverse — apply reverse effect to a clip.

Exercises the full HTTP path:
  POST /api/v1/projects
  POST /api/v1/projects/{id}/clips
  POST /api/v1/projects/{id}/clips/{id}/effects  (effect_type=reverse)
  GET  /api/v1/projects/{id}/clips/{id}/effects  (verify stored)
"""

from __future__ import annotations

from typing import Any

import httpx


async def run_uc_cap_reverse(base_url: str) -> dict[str, Any]:
    """Run the reverse-effect chatbot capability scenario.

    Creates a project and short clip, applies the reverse effect, and
    verifies the stored effect filter string contains 'reverse'.

    Args:
        base_url: Base URL of the running API server (e.g. 'http://127.0.0.1:8765').

    Returns:
        Dict with 'status' ('ok' or 'fail') and diagnostic detail.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={"name": "uc_cap_reverse scenario"},
        )
        if proj_resp.status_code != 201:
            return {"status": "fail", "step": "create_project", "detail": proj_resp.json()}
        project_id = proj_resp.json()["id"]

        # List videos to find a usable source
        videos_resp = await client.get("/api/v1/videos?limit=1")
        if videos_resp.status_code != 200 or not videos_resp.json().get("videos"):
            return {"status": "skip", "reason": "no videos available for scenario"}
        video_id = videos_resp.json()["videos"][0]["id"]

        # Create a short clip (within the 30s default reverse limit)
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video_id,
                "in_point": 0,
                "out_point": 300,  # 10s at 30fps
                "timeline_position": 0,
            },
        )
        if clip_resp.status_code != 201:
            return {"status": "fail", "step": "create_clip", "detail": clip_resp.json()}
        clip_id = clip_resp.json()["id"]

        # Apply reverse effect
        apply_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "reverse", "parameters": {}},
        )
        if apply_resp.status_code != 201:
            return {"status": "fail", "step": "apply_effect", "detail": apply_resp.json()}

        effect = apply_resp.json()
        filter_string = effect.get("filter_string", "")
        if "reverse" not in filter_string:
            return {
                "status": "fail",
                "step": "verify_filter",
                "detail": f"expected 'reverse' in filter_string, got: {filter_string!r}",
            }

        # Verify effect appears in clip effects list
        effects_resp = await client.get(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
        )
        if effects_resp.status_code != 200:
            return {"status": "fail", "step": "list_effects", "detail": effects_resp.json()}

        stored = effects_resp.json()
        if not any("reverse" in e.get("filter_string", "") for e in stored.get("effects", [])):
            return {
                "status": "fail",
                "step": "verify_stored",
                "detail": f"reverse effect not found in stored effects: {stored}",
            }

    return {"status": "ok", "filter_string": filter_string}
