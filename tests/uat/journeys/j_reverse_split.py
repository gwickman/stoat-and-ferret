"""UAT Journey 705 — Reverse-Split: verify timeline tracks visible for clip operations."""

from __future__ import annotations

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J705: Navigate to timeline page, verify timeline tracks visible for split/reverse."""
    await page.goto(base_url + "timeline")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='timeline-page']")).to_be_visible()
    await expect(page.locator("[data-testid='timeline-tracks']")).to_be_visible()
    await page.screenshot(path="j705_timeline.png")
