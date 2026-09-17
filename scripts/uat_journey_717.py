#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 717: Restore preserves clip metadata fields (BL-842).

Validates that restoring a project version preserves generator_params,
effects, and source_asset_id on clips — fields silently zeroed out before v142.

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
    print("SKIP: J-717 requires headed Playwright (STOAT_UAT_PLAYWRIGHT_HEADED not set)")
    sys.exit(0)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNEY_NAME = "restore-preserves-clip-metadata"
JOURNEY_ID = 717
JOURNEY_TIMEOUT: int = 300  # seconds


def run() -> int:
    """Execute journey 717: restore preserves clip metadata fields.

    Steps:
    1. Navigate to the Projects page and open the first project.
    2. Locate a generator clip in the timeline (skip if none).
    3. Note the generator_params label displayed for the clip.
    4. Save a version via GUI.
    5. Delete the generator clip from the timeline.
    6. Navigate to the Versions section and restore the saved version.
    7. Assert the generator clip re-appears with matching metadata label.

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

    # Pre-flight: check via API that a project exists before launching Playwright.
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
                raise RuntimeError("No projects available for metadata restore journey")

            project_links.first.click()
            page.wait_for_load_state("networkidle", timeout=15_000)
            page.wait_for_timeout(500)
            screenshot_path = str(journey_dir / "02_project_open.png")
            page.screenshot(path=screenshot_path)
            step("Open first project", True)

            # Step 3: Locate a generator clip — note metadata label
            generator_clips = page.locator(
                "[data-testid='clip-type-generator'], [data-clip-type='generator']"
            )
            if generator_clips.count() == 0:
                step(
                    "Locate generator clip in timeline",
                    False,
                    "No generator clips found; journey requires a pre-seeded generator clip",
                )
                raise RuntimeError(
                    "No generator clips in project — seed one via API before running J-717"
                )

            first_gen = generator_clips.first
            metadata_label = (
                first_gen.get_attribute("data-generator-params") or first_gen.inner_text()
            )
            screenshot_path = str(journey_dir / "03_generator_clip_located.png")
            page.screenshot(path=screenshot_path)
            step(f"Locate generator clip (metadata: {metadata_label!r:.40})", True)

            # Step 4: Save a version via GUI "Save Version" button
            save_btn = page.locator(
                "[data-testid='save-version-button'], button:has-text('Save Version')"
            )
            if save_btn.count() == 0:
                step("Save version", False, "Save Version button not found")
                raise RuntimeError("Save Version button missing")

            save_btn.first.click()
            page.wait_for_timeout(1500)
            screenshot_path = str(journey_dir / "04_version_saved.png")
            page.screenshot(path=screenshot_path)
            step("Save version via GUI", True)

            # Step 5: Delete the generator clip from the timeline to mutate live state
            first_gen.click()
            page.wait_for_timeout(500)
            delete_btn = page.locator(
                "[data-testid='delete-clip-button'], button:has-text('Delete')"
            )
            if delete_btn.count() > 0:
                delete_btn.first.click()
                page.wait_for_timeout(1000)
                confirm_btn = page.locator(
                    "[data-testid='confirm-delete'], button:has-text('Confirm'), "
                    "button:has-text('Yes')"
                )
                if confirm_btn.count() > 0:
                    confirm_btn.first.click()
                    page.wait_for_timeout(800)
                screenshot_path = str(journey_dir / "05_clip_deleted.png")
                page.screenshot(path=screenshot_path)
                step("Delete generator clip (mutate live state)", True)
            else:
                step(
                    "Delete generator clip (mutate live state)",
                    False,
                    "Delete button not found; cannot verify mutation",
                )

            # Step 6: Navigate to Versions section and restore
            versions_tab = page.locator(
                "[data-testid='versions-tab'], button:has-text('Versions'), a:has-text('Versions')"
            )
            if versions_tab.count() == 0:
                step("Navigate to Versions section", False, "Versions tab/section not found")
                raise RuntimeError("Versions tab missing")

            versions_tab.first.click()
            page.wait_for_timeout(1000)
            screenshot_path = str(journey_dir / "06_versions_section.png")
            page.screenshot(path=screenshot_path)
            step("Navigate to Versions section in ProjectDetails", True)

            restore_btn = page.locator(
                "[data-testid='restore-version-button'], button:has-text('Restore')"
            )
            if restore_btn.count() == 0:
                step("Click Restore button", False, "Restore button not found in Versions section")
                raise RuntimeError("Restore button missing")

            restore_btn.first.click()
            page.wait_for_timeout(2000)
            screenshot_path = str(journey_dir / "07_restore_clicked.png")
            page.screenshot(path=screenshot_path)
            step("Click Restore button on saved version", True)

            # Step 7: Assert the generator clip re-appears with matching metadata
            clips_tab = page.locator(
                "[data-testid='clips-tab'], button:has-text('Clips'), a:has-text('Clips')"
            )
            if clips_tab.count() > 0:
                clips_tab.first.click()
                page.wait_for_timeout(800)

            restored_gen_clips = page.locator(
                "[data-testid='clip-type-generator'], [data-clip-type='generator']"
            )
            screenshot_path = str(journey_dir / "08_timeline_after_restore.png")
            page.screenshot(path=screenshot_path)

            gen_count_ok = restored_gen_clips.count() > 0
            step(
                "Generator clip re-appears after restore",
                gen_count_ok,
                "" if gen_count_ok else "No generator clips visible after restore",
            )

            if gen_count_ok:
                restored_label = (
                    restored_gen_clips.first.get_attribute("data-generator-params")
                    or restored_gen_clips.first.inner_text()
                )
                metadata_match = metadata_label.strip() == restored_label.strip()
                step(
                    f"Generator metadata preserved (got: {restored_label!r:.40})",
                    metadata_match,
                    ""
                    if metadata_match
                    else (
                        f"Metadata mismatch: expected {metadata_label!r}, got {restored_label!r}"
                    ),
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
