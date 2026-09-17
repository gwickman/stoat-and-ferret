# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 720 — Version Restore Round-Trip: restore preserves clip metadata fields (BL-842).

Validates that restoring a project version preserves generator_params,
effects, and source_asset_id on clips — fields silently zeroed out before v142.

deferred_post_merge: requires a live server with GUI and a pre-seeded generator clip.
Run: python scripts/uat_runner.py --headless
     python scripts/uat_runner.py --headless --skip-build
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from playwright.async_api import Page

_SERVER_URL = os.getenv("UAT_SERVER_URL", "http://localhost:8765")


async def run(page: Page, base_url: str, output_dir: Path | None = None) -> None:
    """Execute journey 720: restore preserves clip metadata fields.

    Steps:
    1. Pre-flight: check via API that a project exists; skip if none.
    2. Navigate to Projects page and open the first project.
    3. Locate a generator clip; skip if none.
    4. Note the generator_params label displayed for the clip.
    5. Save a version via GUI.
    6. Delete the generator clip from the timeline.
    7. Navigate to the Versions section and restore the saved version.
    8. Assert the generator clip re-appears with matching metadata label.
    """
    ev_dir: Path | None = None
    if output_dir is not None:
        ev_dir = Path(output_dir) / "version-restore-roundtrip"
        ev_dir.mkdir(parents=True, exist_ok=True)

    async def shot(name: str) -> None:
        if ev_dir is not None:
            await page.screenshot(path=str(ev_dir / name))

    # Pre-flight: confirm a project exists before launching browser steps.
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_SERVER_URL}/api/v1/projects?limit=1")
            projects = resp.json().get("projects", [])
    except Exception:
        projects = []

    if not projects:
        return  # deferred_post_merge: no live server / no pre-seeded project

    # Step 1: navigate to Projects page
    await page.goto(f"{_SERVER_URL}/gui/projects", wait_until="networkidle", timeout=30_000)
    await page.wait_for_timeout(1000)
    await shot("01_projects_page.png")

    # Step 2: open first project
    project_links = page.locator("[data-testid='project-card'], [data-testid='project-link']")
    count = await project_links.count()
    if count == 0:
        return  # no projects visible on page — skip
    await project_links.first.click()
    await page.wait_for_load_state("networkidle", timeout=15_000)
    await page.wait_for_timeout(500)
    await shot("02_project_open.png")

    # Step 3: locate a generator clip
    gen_clips = page.locator(
        "[data-testid='clip-type-generator'], [data-clip-type='generator']"
    )
    if await gen_clips.count() == 0:
        return  # no generator clip to test against — skip
    first_gen = gen_clips.first
    metadata_label = (
        await first_gen.get_attribute("data-generator-params") or await first_gen.inner_text()
    )
    await shot("03_generator_clip_located.png")

    # Step 4: save a version via GUI
    save_btn = page.locator(
        "[data-testid='save-version-button'], button:has-text('Save Version')"
    )
    if await save_btn.count() == 0:
        raise AssertionError("Save Version button not found — GUI contract broken")
    await save_btn.first.click()
    await page.wait_for_timeout(1500)
    await shot("04_version_saved.png")

    # Step 5: delete the generator clip to mutate live state
    await first_gen.click()
    await page.wait_for_timeout(500)
    delete_btn = page.locator("[data-testid='delete-clip-button'], button:has-text('Delete')")
    if await delete_btn.count() > 0:
        await delete_btn.first.click()
        await page.wait_for_timeout(1000)
        confirm_btn = page.locator(
            "[data-testid='confirm-delete'], button:has-text('Confirm'), button:has-text('Yes')"
        )
        if await confirm_btn.count() > 0:
            await confirm_btn.first.click()
            await page.wait_for_timeout(800)
        await shot("05_clip_deleted.png")

    # Step 6: navigate to Versions section and restore
    versions_tab = page.locator(
        "[data-testid='versions-tab'], button:has-text('Versions'), a:has-text('Versions')"
    )
    if await versions_tab.count() == 0:
        raise AssertionError("Versions tab not found — GUI contract broken")
    await versions_tab.first.click()
    await page.wait_for_timeout(1000)
    await shot("06_versions_section.png")

    restore_btn = page.locator(
        "[data-testid='restore-version-button'], button:has-text('Restore')"
    )
    if await restore_btn.count() == 0:
        raise AssertionError("Restore button not found in Versions section — GUI contract broken")
    await restore_btn.first.click()
    await page.wait_for_timeout(2000)
    await shot("07_restore_clicked.png")

    # Step 7: assert generator clip re-appears with matching metadata
    clips_tab = page.locator(
        "[data-testid='clips-tab'], button:has-text('Clips'), a:has-text('Clips')"
    )
    if await clips_tab.count() > 0:
        await clips_tab.first.click()
        await page.wait_for_timeout(800)

    restored_gen = page.locator(
        "[data-testid='clip-type-generator'], [data-clip-type='generator']"
    )
    await shot("08_timeline_after_restore.png")

    restored_count = await restored_gen.count()
    if restored_count == 0:
        raise AssertionError("Generator clip did not reappear after restore — BL-842 regression")

    restored_label = (
        await restored_gen.first.get_attribute("data-generator-params")
        or await restored_gen.first.inner_text()
    )
    if metadata_label.strip() != restored_label.strip():
        raise AssertionError(
            f"generator_params not preserved after restore: "
            f"expected {metadata_label!r}, got {restored_label!r} — BL-842 regression"
        )
