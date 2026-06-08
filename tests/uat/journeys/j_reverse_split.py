"""UAT Journey stub: j_reverse_split.

TODO: Implement full journey for this capability.
"""

from __future__ import annotations

from playwright.async_api import Page


async def run(page: Page, base_url: str) -> None:
    """Stub journey — navigates to app root and exits cleanly."""
    # TODO: implement full j_reverse_split journey
    await page.goto(base_url)
    await page.wait_for_load_state("networkidle")
