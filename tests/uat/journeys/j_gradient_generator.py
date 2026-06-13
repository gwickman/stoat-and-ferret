"""UAT Journey 710 — Gradient Generator: preview gradient_generator, assert filter returns 200.

Exercises:
  1. Effects preview endpoint for gradient_generator (lavfi source generator)
  2. Assertion that preview returns 200 with a gradients= filter string
  3. Effects page navigation and screenshot
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J710: Call effects/preview for gradient_generator, assert 200 and gradients filter.

    Exercises the gradient_generator lavfi source via the effects preview endpoint
    introduced in v081. Navigates to the effects page for screenshot evidence.
    """
    parsed = urlparse(base_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(base_url=api_base, timeout=30.0) as client:
        # Preview the gradient_generator filter string (no clip required for source generators)
        resp = await client.post(
            "/api/v1/effects/preview",
            json={
                "effect_type": "gradient_generator",
                "parameters": {"color1": "black", "color2": "white", "duration": 5.0},
            },
        )
        assert resp.status_code == 200, (
            f"Effects preview failed: {resp.status_code} {resp.text}"
        )
        preview = resp.json()
        assert "filter_string" in preview, f"Response missing filter_string: {preview}"
        assert "gradients" in preview["filter_string"], (
            f"Expected gradients in filter_string, got: {preview['filter_string']}"
        )

    # Navigate to effects page and capture screenshot evidence
    await page.goto(base_url + "effects")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='effects-page']")).to_be_visible()
    await page.screenshot(path="j710_gradient_generator.png")
