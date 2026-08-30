# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey — Unknown Effect Fail-Closed: unknown effect type causes render job to fail (BL-795).

Exercises:
  1. Project creation and single-clip setup via HTTP API with an unknown effect type
  2. Render submission and poll to terminal state
  3. Assert the render job fails/declines rather than silently succeeding
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

import httpx
from playwright.async_api import Page, expect

_UC_ID = "UC-MEDIA-UNKNOWN-EFFECT-FAILCLOSED"


async def _poll_render_job(
    client: httpx.AsyncClient,
    job_id: str,
    timeout: float = 60.0,
    interval: float = 2.0,
) -> dict:
    """Poll render job until terminal; return final job info dict."""
    terminal = {"completed", "failed", "cancelled", "qc_failed"}
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        resp = await client.get(f"/api/v1/render/{job_id}")
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") in terminal:
            return data  # type: ignore[return-value]
        await asyncio.sleep(interval)
    raise asyncio.TimeoutError(
        f"Render job {job_id} did not reach terminal state within {timeout}s"
    )


async def run(page: Page, base_url: str) -> None:
    """Unknown-effect fail-closed UAT journey.

    Creates a project with a clip referencing an unknown effect type,
    submits a render, and asserts the job fails rather than silently succeeding.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(base_url=api_base, timeout=30.0) as client:
        # Find any video in the library to reference
        videos_resp = await client.get("/api/v1/videos?limit=10")
        videos_resp.raise_for_status()
        videos = videos_resp.json().get("videos", [])

        if not videos:
            # No videos available; navigate to render page and capture screenshot only
            await page.goto(base_url + "render")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path="j_unknown_effect_failclosed.png")
            return

        video = videos[0]
        vid_id = video["id"]
        duration_frames = video.get("duration_frames", 90)

        render_plan = json.dumps(
            {
                "total_duration": 3.0,
                "settings": {
                    "codec": "libx264",
                    "fps": 30.0,
                    "width": 320,
                    "height": 240,
                    "quality_preset": "standard",
                },
            }
        )

        # Create project
        proj_resp = await client.post(
            "/api/v1/projects",
            json={
                "name": f"{_UC_ID} UAT",
                "output_width": 320,
                "output_height": 240,
                "output_fps": 30,
            },
        )
        assert proj_resp.status_code == 201, (
            f"Project creation failed: {proj_resp.status_code} {proj_resp.text}"
        )
        project_id: str = proj_resp.json()["id"]

        # Add clip (no inline effects — two-step creation required)
        clip_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": vid_id,
                "in_point": 0,
                "out_point": min(90, duration_frames),
                "timeline_position": 0,
            },
        )
        assert clip_resp.status_code == 201, (
            f"Clip creation failed: {clip_resp.status_code} {clip_resp.text}"
        )
        clip_id: str = clip_resp.json()["id"]

        # Attach unknown effect type via two-step POST /clips/{id}/effects
        eff_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "totally_unknown_effect_xyz", "parameters": {}},
        )
        assert eff_resp.status_code in (200, 201), (
            f"Add effect failed: {eff_resp.status_code} {eff_resp.text}"
        )

        # Submit render — expect the job to fail (fail-closed contract)
        render_resp = await client.post(
            "/api/v1/render",
            json={"project_id": project_id, "render_plan": render_plan},
        )
        assert render_resp.status_code == 201, (
            f"Render submit failed: {render_resp.status_code} {render_resp.text}"
        )
        job_id: str = render_resp.json()["id"]

        # Poll to terminal state and assert fail-closed outcome
        final_job = await _poll_render_job(client, job_id)
        assert final_job["status"] == "failed", (
            f"Expected render to fail (fail-closed) but got "
            f"status={final_job['status']!r}; unknown effect must not produce silent success"
        )
        assert final_job.get("error_message"), (
            "Render job status=failed but error_message is absent; fail-closed must populate it"
        )

    # Navigate to render page for browser screenshot evidence
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j_unknown_effect_failclosed.png")
