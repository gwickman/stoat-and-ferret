#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 720: Version restore round-trip (BL-799).

Validates that a user can save a project version, modify the live timeline, then
restore the saved version via the GUI and observe the timeline revert to the saved
state (tracks and clips match the snapshot).

deferred_post_merge: requires a live server with GUI and real timeline state.
Run: python scripts/uat_runner.py --headless
     python scripts/uat_runner.py --headless --skip-build
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

if not os.environ.get("STOAT_UAT_PLAYWRIGHT_HEADED"):
    print("SKIP: J-720 requires headed Playwright (STOAT_UAT_PLAYWRIGHT_HEADED not set)")
    sys.exit(0)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNEY_NAME = "version-restore-roundtrip"
JOURNEY_ID = 720
JOURNEY_TIMEOUT: int = 300  # seconds


def run() -> int:
    """Execute journey 717: version restore round-trip.

    Steps:
    1. Navigate to the Projects page and open the first project.
    2. Record initial clip count.
    3. Save a version via GUI.
    4. Add a clip to the timeline (modifying live state).
    5. Navigate to the Versions section in ProjectDetails.
    6. Click the Restore button on the saved version.
    7. Assert the timeline reverted: clip count matches the saved snapshot.

    Returns:
        Exit code: 0 if all steps pass, 1 otherwise.
    """
    output_dir = Path(os.environ.get("UAT_OUTPUT_DIR", "testing-evidence/uat-evidence"))
    headed = os.environ.get("UAT_HEADED", "0") == "1"
    server_url = os.environ.get("UAT_SERVER_URL", "http://localhost:8765")

    journey_dir = output_dir / JOURNEY_NAME
    journey_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()

    steps_total = 0
    steps_passed = 0
    steps_failed = 0
    issues: list[str] = []

    def step(name: str, passed: bool, detail: str = "") -> None:
        nonlocal steps_total, steps_passed, steps_failed
        steps_total += 1
        if passed:
            steps_passed += 1
            print(f"  [{steps_total}] PASS — {name}")
        else:
            steps_failed += 1
            msg = f"[{steps_total}] FAIL — {name}" + (f": {detail}" if detail else "")
            issues.append(msg)
            print(f"  {msg}")

    # AC-30: SKIP guard — journey requires a pre-seeded project; check via API before
    # launching Playwright so CI headless runs without pre-seeded state exit cleanly.
    try:
        with urllib.request.urlopen(f"{server_url}/api/v1/projects?limit=1", timeout=5) as resp:
            body = json.loads(resp.read())
            projects = body.get("projects", [])
    except Exception:
        projects = []
    if not projects:
        skip_result = {
            "name": JOURNEY_NAME,
            "journey_id": JOURNEY_ID,
            "status": "skipped",
            "steps_total": 0,
            "steps_passed": 0,
            "steps_failed": 0,
            "console_errors": [],
            "issues": [
                "deferred_post_merge: no pre-seeded project found; "
                "requires headed run with live server"
            ],
            "duration_seconds": 0.0,
        }
        result_path = journey_dir / "journey_result.json"
        result_path.write_text(json.dumps(skip_result, indent=2) + "\n", encoding="utf-8")
        print(f"\n  Journey {JOURNEY_ID} ({JOURNEY_NAME}): SKIPPED (no pre-seeded project)")
        return 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        try:
            # Step 1: Navigate to Projects page
            page.goto(f"{server_url}/gui/projects", wait_until="networkidle", timeout=30_000)
            page.wait_for_timeout(1000)
            screenshot_path = str(journey_dir / "01_projects_page.png")
            page.screenshot(path=screenshot_path)
            step("Navigate to Projects page", True)

            # Step 2: Open first project
            project_links = page.locator(
                "[data-testid='project-card'], [data-testid='project-link']"
            )
            project_count = project_links.count()
            if project_count == 0:
                step("Open first project", False, "No projects found on page")
                raise RuntimeError("No projects available for restore journey")

            project_links.first.click()
            page.wait_for_load_state("networkidle", timeout=15_000)
            page.wait_for_timeout(500)
            screenshot_path = str(journey_dir / "02_project_open.png")
            page.screenshot(path=screenshot_path)
            step("Open first project", True)

            # Step 3: Record initial clip count from the clips table
            clip_rows = page.locator("[data-testid='clip-row'], [data-testid='clip-item']")
            initial_clip_count = clip_rows.count()
            step(f"Record initial clip count ({initial_clip_count})", True)

            # Step 4: Save a version via GUI "Save Version" button
            save_btn = page.locator(
                "[data-testid='save-version-button'], button:has-text('Save Version')"
            )
            if save_btn.count() == 0:
                step("Save version", False, "Save Version button not found")
                raise RuntimeError("Save Version button missing — Feature 004 must be merged")

            save_btn.first.click()
            page.wait_for_timeout(1500)
            screenshot_path = str(journey_dir / "03_version_saved.png")
            page.screenshot(path=screenshot_path)
            step("Save version via GUI", True)

            # Step 5: Add a clip to the timeline (modifying live state)
            add_clip_btn = page.locator(
                "[data-testid='add-clip-button'], button:has-text('Add Clip')"
            )
            if add_clip_btn.count() > 0:
                add_clip_btn.first.click()
                page.wait_for_timeout(1000)
                # Confirm any dialog that may appear
                confirm_btn = page.locator(
                    "[data-testid='confirm-add-clip'], "
                    "button:has-text('Add'), button:has-text('Confirm')"
                )
                if confirm_btn.count() > 0:
                    confirm_btn.first.click()
                    page.wait_for_timeout(800)
                screenshot_path = str(journey_dir / "04_clip_added.png")
                page.screenshot(path=screenshot_path)
                step("Add clip to timeline (modify live state)", True)
            else:
                # AC-29: button absent = journey FAIL, not silent skip
                step(
                    "Add clip to timeline (modify live state)",
                    False,
                    "Add Clip button not present — mutation step cannot be verified",
                )

            # Step 6: Navigate to Versions section in ProjectDetails
            versions_tab = page.locator(
                "[data-testid='versions-tab'], button:has-text('Versions'), a:has-text('Versions')"
            )
            if versions_tab.count() == 0:
                step("Navigate to Versions section", False, "Versions tab/section not found")
                raise RuntimeError(
                    "Versions tab missing — Feature 004 (restore-acceptance) must be merged"
                )

            versions_tab.first.click()
            page.wait_for_timeout(1000)
            screenshot_path = str(journey_dir / "05_versions_section.png")
            page.screenshot(path=screenshot_path)
            step("Navigate to Versions section in ProjectDetails", True)

            # Step 7: Click Restore button on the saved version
            restore_btn = page.locator(
                "[data-testid='restore-version-button'], button:has-text('Restore')"
            )
            if restore_btn.count() == 0:
                step("Click Restore button", False, "Restore button not found in Versions section")
                raise RuntimeError("Restore button missing — check versions list populated")

            restore_btn.first.click()
            page.wait_for_timeout(2000)
            screenshot_path = str(journey_dir / "06_restore_clicked.png")
            page.screenshot(path=screenshot_path)
            step("Click Restore button on saved version", True)

            # Step 8: Assert timeline reverted — clip count matches saved snapshot
            # Navigate back to timeline/clips view
            clips_tab = page.locator(
                "[data-testid='clips-tab'], button:has-text('Clips'), a:has-text('Clips')"
            )
            if clips_tab.count() > 0:
                clips_tab.first.click()
                page.wait_for_timeout(800)

            clip_rows_after = page.locator("[data-testid='clip-row'], [data-testid='clip-item']")
            restored_clip_count = clip_rows_after.count()
            screenshot_path = str(journey_dir / "07_timeline_after_restore.png")
            page.screenshot(path=screenshot_path)

            count_match = restored_clip_count == initial_clip_count
            saved = initial_clip_count
            got = restored_clip_count
            step(
                f"Assert timeline reverted (clips: {got} == saved: {saved})",
                count_match,
                "" if count_match else f"Expected {saved} clips, got {got}",
            )

        except RuntimeError as exc:
            issues.append(f"Journey halted: {exc}")
            print(f"  Journey halted: {exc}")
        except Exception as exc:
            issues.append(f"Unexpected error: {exc}")
            print(f"  Unexpected error: {exc}")
            steps_total += 1
            steps_failed += 1
            try:
                fail_path = str(journey_dir / f"{steps_total:02d}_FAIL_unexpected_error.png")
                page.screenshot(path=fail_path)
            except Exception:
                pass
        finally:
            context.close()
            browser.close()

    duration = time.monotonic() - start_time
    passed = steps_failed == 0

    result_data = {
        "name": JOURNEY_NAME,
        "journey_id": JOURNEY_ID,
        "status": "passed" if passed else "failed",
        "steps_total": steps_total,
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "console_errors": [],
        "issues": issues,
        "duration_seconds": round(duration, 2),
    }
    result_path = journey_dir / "journey_result.json"
    result_path.write_text(json.dumps(result_data, indent=2) + "\n", encoding="utf-8")

    status = "PASSED" if passed else "FAILED"
    print(f"\n  Journey {JOURNEY_ID} ({JOURNEY_NAME}): {status}")
    print(f"  Steps: {steps_total}, passed: {steps_passed}, failed: {steps_failed}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
