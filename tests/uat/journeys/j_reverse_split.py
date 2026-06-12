"""UAT Journey 705 — Reverse-Split: API-exercising journey for reverse effect and clip split.

Exercises:
  1. Project and generator clip creation via API
  2. Reverse effect application via POST /clips/{id}/effects
  3. Clip split via POST /clips/{id}/split
  4. Assertion that clip_a.out_point == split_frame and clip_b.in_point == split_frame
  5. Timeline page navigation and screenshot
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J705: Create project+clip via API, apply reverse, split, assert correct split points.

    Uses a generator clip (no video file required) to exercise the reverse and split
    API endpoints introduced in v080. Navigates to the timeline page for screenshot evidence.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(base_url=api_base, timeout=30.0) as client:
        # Step 1: Create project
        resp = await client.post(
            "/api/v1/projects",
            json={"name": "J705 Reverse-Split UAT", "output_fps": 30},
        )
        assert resp.status_code == 201, f"Create project failed: {resp.status_code} {resp.text}"
        project_id = resp.json()["id"]

        # Step 2: Create generator clip (90 frames at 30fps = 3s, well under reverse_max_duration_s)
        resp = await client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "generator",
                "generator_params": {"type": "silence", "duration_frames": 90},
                "in_point": 0,
                "out_point": 90,
                "timeline_position": 0,
            },
        )
        assert resp.status_code == 201, f"Create clip failed: {resp.status_code} {resp.text}"
        clip_id = resp.json()["id"]

        # Step 3: Apply reverse effect via POST /effects (no parameters required)
        resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "reverse", "parameters": {}},
        )
        assert resp.status_code == 201, f"Apply reverse failed: {resp.status_code} {resp.text}"
        assert resp.json()["effect_type"] == "reverse"

        # Step 4: Split clip at midpoint (must be strictly between in_point and out_point)
        mid_frame = 45
        resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/split",
            json={"split_frame": mid_frame},
        )
        assert resp.status_code == 200, f"Split clip failed: {resp.status_code} {resp.text}"
        split = resp.json()
        assert split["clip_a"]["out_point"] == mid_frame, (
            f"clip_a.out_point expected {mid_frame}, got {split['clip_a']['out_point']}"
        )
        assert split["clip_b"]["in_point"] == mid_frame, (
            f"clip_b.in_point expected {mid_frame}, got {split['clip_b']['in_point']}"
        )

    # Step 5: Navigate to timeline page and capture screenshot evidence
    await page.goto(base_url + "timeline")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='timeline-page']")).to_be_visible()
    await expect(page.locator("[data-testid='timeline-tracks']")).to_be_visible()
    await page.screenshot(path="j705_reverse_split.png")
