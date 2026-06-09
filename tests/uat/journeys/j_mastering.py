"""UAT Journey 702 — Mastering: delivery profile creation and QC-gated render export."""

from __future__ import annotations

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J702: Navigate to render page, verify render controls and start-render button visible.

    Depends on J701 (markers journey establishes project context).
    """
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await expect(page.locator("[data-testid='start-render-btn']")).to_be_visible()
    await page.screenshot(path="j702_render.png")
