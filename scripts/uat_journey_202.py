#!/usr/bin/env python3
"""UAT Journey 202: Project Clip.

Validates project creation, clip addition, and Rust-calculated timeline position
display through the GUI. Creates a project, adds 3 clips with in/out points and
timeline positions, then verifies all clips render correctly in the clips table.

Depends on journey 201 (scan-library) for scanned video data.

Environment variables:
    UAT_OUTPUT_DIR: Directory for journey output artifacts.
    UAT_HEADED: "1" for headed mode, "0" for headless (default).
    UAT_SERVER_URL: Base URL of the running server (default: http://localhost:8765).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

JOURNEY_NAME = "project-clip"
JOURNEY_ID = 202

# Test data for clip creation
TEST_PROJECT_NAME = "UAT Test Project 202"
TEST_RESOLUTION = "1280x720"
TEST_FPS = "30"

CLIP_DATA = [
    {"in_point": "0", "out_point": "90", "timeline_position": "0"},
    {"in_point": "30", "out_point": "150", "timeline_position": "90"},
    {"in_point": "60", "out_point": "180", "timeline_position": "240"},
]

# Benign console error patterns to ignore
BENIGN_PATTERNS = ["favicon"]


def screenshot(
    page: Any,
    journey_dir: Path,
    step: int,
    description: str,
    *,
    failed: bool = False,
) -> Path:
    """Capture a screenshot with structured naming.

    Args:
        page: Playwright Page object.
        journey_dir: Output directory for this journey.
        step: Step number.
        description: Brief description for the filename.
        failed: If True, prefix description with FAIL_.

    Returns:
        Path to the saved screenshot.
    """
    prefix = "FAIL_" if failed else ""
    filename = f"{step:02d}_{prefix}{description}.png"
    path = journey_dir / filename
    page.screenshot(path=str(path))
    return path


def run() -> int:
    """Execute the project-clip journey.

    Returns:
        Exit code: 0 if all steps pass, 1 otherwise.
    """
    output_dir = Path(os.environ.get("UAT_OUTPUT_DIR", "uat-evidence"))
    headed = os.environ.get("UAT_HEADED", "0") == "1"
    server_url = os.environ.get("UAT_SERVER_URL", "http://localhost:8765")
    gui_url = f"{server_url}/gui/"

    journey_dir = output_dir / JOURNEY_NAME
    journey_dir.mkdir(parents=True, exist_ok=True)

    steps_total = 0
    steps_passed = 0
    steps_failed = 0
    console_errors: list[str] = []
    issues: list[str] = []

    start_time = time.monotonic()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        # Collect console errors, filtering benign patterns
        def on_console(msg: Any) -> None:
            if msg.type != "error":
                return
            text: str = msg.text
            if any(pat in text.lower() for pat in BENIGN_PATTERNS):
                return
            console_errors.append(text)

        page.on("console", on_console)

        try:
            # ----------------------------------------------------------
            # Step 1: Navigate to Projects tab
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.goto(gui_url, wait_until="networkidle")
                page.wait_for_selector('[data-testid="nav-tab-projects"]', timeout=15000)
                screenshot(page, journey_dir, 1, "navigation")
                page.click('[data-testid="nav-tab-projects"]')
                page.wait_for_selector('[data-testid="projects-page"]', timeout=10000)
                screenshot(page, journey_dir, 2, "projects_page")
                steps_passed += 1
                print("  Step 1: Navigate to Projects tab - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 1 failed: {exc}")
                screenshot(page, journey_dir, 1, "navigation", failed=True)
                print(f"  Step 1: Navigate to Projects tab - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 2: Create a new project
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="btn-new-project"]')
                page.wait_for_selector('[data-testid="create-project-modal"]', timeout=5000)
                screenshot(page, journey_dir, 3, "create_modal")

                # Fill project fields
                name_input = page.locator('[data-testid="input-project-name"]')
                name_input.fill(TEST_PROJECT_NAME)

                res_input = page.locator('[data-testid="input-resolution"]')
                res_input.fill("")
                res_input.fill(TEST_RESOLUTION)

                fps_input = page.locator('[data-testid="input-fps"]')
                fps_input.fill("")
                fps_input.fill(TEST_FPS)

                # Submit
                page.click('[data-testid="btn-create"]')

                # Wait for modal to close and project list to refresh
                page.wait_for_selector(
                    '[data-testid="create-project-modal"]',
                    state="detached",
                    timeout=10000,
                )

                # Verify project appears in the list
                page.wait_for_selector('[data-testid="project-list"]', timeout=10000)
                page.wait_for_timeout(1000)  # Allow list to re-render
                screenshot(page, journey_dir, 4, "project_created")

                # Find the new project card by name
                project_cards = page.locator('[data-testid^="project-card-"]')
                card_count = project_cards.count()
                found_project = False
                for i in range(card_count):
                    card = project_cards.nth(i)
                    card_text = card.text_content() or ""
                    if TEST_PROJECT_NAME in card_text:
                        found_project = True
                        break

                if not found_project:
                    raise AssertionError(f"Project '{TEST_PROJECT_NAME}' not found in project list")

                steps_passed += 1
                print("  Step 2: Create project - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 2 failed: {exc}")
                screenshot(page, journey_dir, 3, "create_modal", failed=True)
                print(f"  Step 2: Create project - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 3: Navigate to project detail page
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Click the project name to navigate to detail
                project_cards = page.locator('[data-testid^="project-name-"]')
                card_count = project_cards.count()
                clicked = False
                for i in range(card_count):
                    card = project_cards.nth(i)
                    card_text = card.text_content() or ""
                    if TEST_PROJECT_NAME in card_text:
                        card.click()
                        clicked = True
                        break

                if not clicked:
                    raise AssertionError(f"Could not click project '{TEST_PROJECT_NAME}'")

                page.wait_for_selector('[data-testid="project-details"]', timeout=10000)

                # Verify project name on detail page
                detail_name = page.locator('[data-testid="project-detail-name"]').text_content()
                if TEST_PROJECT_NAME not in (detail_name or ""):
                    raise AssertionError(
                        f"Expected project name '{TEST_PROJECT_NAME}', got '{detail_name}'"
                    )

                screenshot(page, journey_dir, 5, "project_detail")
                steps_passed += 1
                print("  Step 3: Navigate to project detail - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 5, "project_detail", failed=True)
                print(f"  Step 3: Navigate to project detail - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Add 3 clips
            # ----------------------------------------------------------
            steps_total += 1
            try:
                for clip_idx, clip in enumerate(CLIP_DATA):
                    clip_num = clip_idx + 1

                    # Click Add Clip
                    page.click('[data-testid="btn-add-clip"]')
                    page.wait_for_selector('[data-testid="clip-form-modal"]', timeout=5000)

                    # Wait for videos dropdown to load
                    select = page.locator('[data-testid="select-source-video"]')
                    select.wait_for(timeout=10000)
                    # Wait until at least one option is available
                    page.wait_for_function(
                        """() => {
                            const s = document.querySelector(
                                '[data-testid="select-source-video"]'
                            );
                            return s && s.options && s.options.length > 0
                                && s.options[0].value !== '';
                        }""",
                        timeout=10000,
                    )

                    # Select the first available source video (default)
                    # Fill in/out points and timeline position
                    in_input = page.locator('[data-testid="input-in-point"]')
                    in_input.fill(clip["in_point"])

                    out_input = page.locator('[data-testid="input-out-point"]')
                    out_input.fill(clip["out_point"])

                    pos_input = page.locator('[data-testid="input-timeline-position"]')
                    pos_input.fill(clip["timeline_position"])

                    screenshot(page, journey_dir, 5 + clip_num, f"clip_{clip_num}_form")

                    # Save clip
                    page.click('[data-testid="btn-clip-save"]')

                    # Wait for modal to close
                    page.wait_for_selector(
                        '[data-testid="clip-form-modal"]',
                        state="detached",
                        timeout=10000,
                    )

                    # Wait for clip to appear in table
                    page.wait_for_timeout(1000)  # Allow table to re-render

                    screenshot(page, journey_dir, 8 + clip_num, f"clip_{clip_num}_added")
                    print(f"    Clip {clip_num} added successfully")

                # Verify all 3 clips are in the table
                page.wait_for_selector('[data-testid="clips-table"]', timeout=10000)
                clip_rows = page.locator('[data-testid^="clip-row-"]')
                row_count = clip_rows.count()
                if row_count < 3:
                    raise AssertionError(f"Expected at least 3 clips in table, found {row_count}")

                steps_passed += 1
                print(f"  Step 4: Add 3 clips ({row_count} in table) - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 11, "clip_addition", failed=True)
                print(f"  Step 4: Add 3 clips - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Verify clip metadata in table
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.wait_for_selector('[data-testid="clips-table"]', timeout=10000)
                clip_rows = page.locator('[data-testid^="clip-row-"]')
                row_count = clip_rows.count()

                if row_count < 3:
                    raise AssertionError(f"Expected at least 3 clips, found {row_count}")

                # Verify each clip row has position, in, and out data
                for i in range(min(row_count, 3)):
                    row = clip_rows.nth(i)
                    row_testid = row.get_attribute("data-testid") or ""
                    clip_id = row_testid.replace("clip-row-", "")

                    pos_el = page.locator(f'[data-testid="clip-position-{clip_id}"]')
                    pos_text = pos_el.text_content() or ""
                    if not pos_text.strip():
                        raise AssertionError(f"Clip {i + 1} timeline position is empty")

                    in_el = page.locator(f'[data-testid="clip-in-{clip_id}"]')
                    in_text = in_el.text_content() or ""
                    if not in_text.strip():
                        raise AssertionError(f"Clip {i + 1} in point is empty")

                    out_el = page.locator(f'[data-testid="clip-out-{clip_id}"]')
                    out_text = out_el.text_content() or ""
                    if not out_text.strip():
                        raise AssertionError(f"Clip {i + 1} out point is empty")

                    print(f"    Clip {i + 1}: pos={pos_text}, in={in_text}, out={out_text}")

                screenshot(page, journey_dir, 12, "final_clips_table")
                steps_passed += 1
                print(f"  Step 5: Verify clip metadata ({row_count} clips verified) - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 12, "final_clips_table", failed=True)
                print(f"  Step 5: Verify clip metadata - FAILED: {exc}")

        finally:
            context.close()
            browser.close()

    duration = time.monotonic() - start_time

    # Write structured result JSON
    result_data = {
        "name": JOURNEY_NAME,
        "journey_id": JOURNEY_ID,
        "steps_total": steps_total,
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "console_errors": console_errors,
        "issues": issues,
        "duration_seconds": round(duration, 2),
    }
    result_path = journey_dir / "journey_result.json"
    result_path.write_text(json.dumps(result_data, indent=2) + "\n", encoding="utf-8")

    print(f"\n  Journey 202 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
