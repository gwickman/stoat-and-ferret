"""UAT Journey 706 — Grade: select a color LUT preset and verify preview renders."""

from __future__ import annotations

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J706: Open effects page, select color_lut, pick calming_teal preset, verify preview."""
    await page.goto(base_url + "effects")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='effects-page']")).to_be_visible()

    # Select the color LUT effect
    lut_effect = page.locator("[data-testid='effect-color_lut']")
    await expect(lut_effect).to_be_visible()
    await lut_effect.click()

    # Choose a preset
    preset_select = page.locator("[data-testid='preset-select']")
    await expect(preset_select).to_be_visible()
    await preset_select.select_option("calming_teal")

    # Verify preview frame renders
    preview = page.locator("[data-testid='preview-frame']")
    await expect(preview).to_be_visible()

    await page.screenshot(path="screenshots/j706_grade.png")
