"""UAT Journey 703 — QC Failure: verify QC failure state and re-master flow visibility.

Asserts QC panel failure indicator and re-master button are visible when a render
fails the QC gate. Requires a project that produces a QC-failing render.
"""

from __future__ import annotations

from playwright.async_api import Page, expect


async def run(page: Page, base_url: str) -> None:
    """J703: Navigate to QC failure project, assert failure state and re-master reachable.

    Verifies:
    - Render page loads (navigation baseline)
    - QC failure indicator is visible in the QC panel
    - Re-master button is reachable from the failure state

    Depends on J702 (mastering journey establishes delivery profile context).
    """
    await page.goto(base_url + "render")
    await page.wait_for_load_state("networkidle")
    await expect(page.locator("[data-testid='render-page']")).to_be_visible()
    await page.screenshot(path="j703_render.png")
    # Assert QC panel failure indicator (R2 surface: requires a QC-failing render job)
    await expect(page.locator("[data-testid='qc-status-fail']")).to_be_visible()
    # Assert re-master flow is reachable from the QC failure state
    await expect(page.locator("[data-testid='remaster-btn']")).to_be_visible()
    await page.screenshot(path="j703_qc_fail.png")
