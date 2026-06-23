# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 706 — Grade: verify effects workshop visible for LUT grading."""

from __future__ import annotations

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J706: Navigate to effects page, verify effects workshop tabs visible for grading."""
    await page.goto(base_url + "effects")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='effects-page']")).to_be_visible()
    await expect(page.locator("[data-testid='workshop-tabs']")).to_be_visible()
    await page.screenshot(path="j706_effects.png")
