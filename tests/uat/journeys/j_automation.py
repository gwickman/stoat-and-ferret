"""UAT Journey 704 — Automation: verify automation lane batch panel visibility."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str, output_dir: Path | None = None) -> None:
    """J704: Navigate to render page, verify batch panel controls visible."""
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await expect(page.locator("[data-testid='batch-panel']")).to_be_visible()

    screenshot_dir = output_dir / "r2-automation" if output_dir else None
    if screenshot_dir:
        screenshot_dir.mkdir(parents=True, exist_ok=True)

    if screenshot_dir:
        await page.screenshot(path=str(screenshot_dir / "01_automation.png"))
    else:
        await page.screenshot(path="j704_automation.png")
