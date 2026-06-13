"""UAT Journey 709 — Lens Distort: apply lens distortion to a generator clip, assert lenscorrection.

Exercises:
  1. Project and generator clip creation via API
  2. Lens distort effect application via POST /clips/{id}/effects with k1/k2 coefficients
  3. Assertion that filter_string contains lenscorrection
  4. Effects page navigation and screenshot
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J709: Create project+clip via API, apply lens_distort, assert lenscorrection.

    Uses a generator clip (no video file required) to exercise the lens distortion effect
    API endpoint introduced in v081. Navigates to the effects page for screenshot evidence.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(base_url=api_base, timeout=30.0) as client:
        # Step 1: Create project
        resp = await client.post(
            "/api/v1/projects",
            json={"name": "J709 Lens Distort UAT", "output_fps": 30},
        )
        assert resp.status_code == 201, f"Create project failed: {resp.status_code} {resp.text}"
        project_id = resp.json()["id"]

        # Step 2: Create generator clip (90 frames at 30fps = 3s)
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

        # Step 3: Apply lens distort effect (barrel distortion with k1=k2=0.3)
        resp = await client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "lens_distort", "parameters": {"k1": 0.3, "k2": 0.3}},
        )
        assert resp.status_code == 201, f"Apply lens_distort failed: {resp.status_code} {resp.text}"
        effect = resp.json()
        assert "filter_string" in effect, f"Response missing filter_string: {effect}"
        assert "lenscorrection" in effect["filter_string"], (
            f"Expected lenscorrection in filter_string, got: {effect['filter_string']}"
        )

    # Step 4: Navigate to effects page and capture screenshot evidence
    await page.goto(base_url + "effects")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='effects-page']")).to_be_visible()
    await page.screenshot(path="j709_lens_distort.png")
