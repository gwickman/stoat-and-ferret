# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey — Unknown Effect Fail-Closed: unknown effect type is rejected at creation time.

Exercises:
  1. Project creation and single-clip setup via HTTP API
  2. Attempt to apply an unknown effect type via POST /projects/{id}/clips/{id}/effects
  3. Assert the API returns 400 EFFECT_NOT_FOUND (fail-closed at creation, not render time)
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from playwright.async_api import Page, expect

_UC_ID = "UC-MEDIA-UNKNOWN-EFFECT-FAILCLOSED"


async def run(page: Page, base_url: str) -> None:
    """Unknown-effect fail-closed UAT journey.

    Creates a project with a clip, then attempts to apply an unknown effect type.
    Asserts the API returns 400 EFFECT_NOT_FOUND — the server definitively rejects
    unknown effects at creation time (fail-closed contract).
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(base_url=api_base, timeout=30.0) as client:
        # Find any video in the library to reference
        videos_resp = await client.get("/api/v1/videos?limit=10")
        videos_resp.raise_for_status()
        videos = videos_resp.json().get("videos", [])

        if not videos:
            await page.goto(base_url + "render")
            await page.wait_for_load_state("networkidle")
            await page.screenshot(path="j_unknown_effect_failclosed.png")
            return

        video = videos[0]
        vid_id = video["id"]
        duration_frames = video.get("duration_frames", 90)

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

        # Add clip (no effects — effects are applied via separate endpoint)
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

        # Attempt to apply an unknown effect — must be rejected 400 EFFECT_NOT_FOUND
        effect_resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "totally_unknown_effect_xyz", "parameters": {}},
        )
        assert effect_resp.status_code == 400, (
            f"Add effect: expected 400 EFFECT_NOT_FOUND, got "
            f"{effect_resp.status_code} {effect_resp.text}"
        )
        detail = effect_resp.json().get("detail", {})
        assert detail.get("code") == "EFFECT_NOT_FOUND", (
            f"Add effect: expected code='EFFECT_NOT_FOUND', got {detail!r}"
        )

    # Navigate to render page for browser screenshot evidence
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j_unknown_effect_failclosed.png")
