# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Release 2 skeleton UAT journey — boots app, verifies R2 surface exists or noops."""

from playwright.async_api import Page


async def run(page: Page, base_url: str) -> None:
    """R2 skeleton: navigate to app root, verify no crash, exit cleanly."""
    await page.goto(base_url)
    await page.wait_for_load_state("networkidle")
    # R2 surface not yet implemented — noop pass
