"""UAT Journey 704 — Automation: verify automation lane batch panel visibility."""

from __future__ import annotations

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J704: Navigate to render page, verify batch panel controls visible."""
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await expect(page.locator("[data-testid='batch-panel']")).to_be_visible()
    await page.screenshot(path="j704_automation.png")
