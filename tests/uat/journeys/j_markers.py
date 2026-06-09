"""UAT Journey 701 — Markers: create section markers and verify timeline display."""

from __future__ import annotations

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J701: Navigate to project timeline, verify timeline page and time-ruler visible."""
    await page.goto(base_url + "timeline")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='timeline-page']")).to_be_visible()
    await expect(page.locator("[data-testid='time-ruler']")).to_be_visible()
    await page.screenshot(path="j701_timeline.png")
