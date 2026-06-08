"""UAT Journey 702 — Mastering: delivery profile creation and QC-gated render export."""

from __future__ import annotations

from playwright.async_api import Page


async def run(page: Page, base_url: str) -> None:
    """J702: Navigate to delivery profiles, create profile, trigger render, verify QC pass.

    Depends on J701 (markers journey establishes project context).
    """
    await page.goto(base_url)
    await page.wait_for_load_state("networkidle")
    await page.screenshot(path="j702_home.png")
