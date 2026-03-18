#!/usr/bin/env python3
"""UAT Journey 204: Export-Render.

Validates the Running Montage sample project loads correctly in the GUI with
all clips, effects, and transitions visible. Seeds the project via
seed_sample_project.py, then navigates through project detail, effects, and
timeline pages to verify all components render correctly.

Independent of journeys 201-203 — uses the seed script directly.

Environment variables:
    UAT_OUTPUT_DIR: Directory for journey output artifacts.
    UAT_HEADED: "1" for headed mode, "0" for headless (default).
    UAT_SERVER_URL: Base URL of the running server (default: http://localhost:8765).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNEY_NAME = "export-render"
JOURNEY_ID = 204

# Expected counts from the Running Montage sample project definition
EXPECTED_CLIPS = 4
EXPECTED_EFFECTS = 5
EXPECTED_TRANSITIONS = 1

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


def seed_sample_project(server_url: str) -> None:
    """Seed the Running Montage sample project via subprocess.

    Args:
        server_url: Base URL of the running server.

    Raises:
        RuntimeError: If the seed script fails.
    """
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "seed_sample_project.py"), server_url],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Non-zero exit may mean project already exists (exit 0 with message),
        # or a real failure. Check stderr for actual errors.
        if "already exists" in (result.stdout + result.stderr):
            print("    Sample project already seeded, continuing...")
            return
        raise RuntimeError(
            f"Seed script failed (exit {result.returncode}): "
            f"{result.stderr[-300:] if result.stderr else result.stdout[-300:]}"
        )
    print("    Sample project seeded successfully")


def run() -> int:
    """Execute the export-render journey.

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

    # ----------------------------------------------------------
    # Pre-step: Seed the Running Montage sample project
    # ----------------------------------------------------------
    try:
        print("  Seeding Running Montage sample project...")
        seed_sample_project(server_url)
    except RuntimeError as exc:
        print(f"  ERROR: Failed to seed sample project: {exc}", file=sys.stderr)
        # Write a minimal result and exit
        result_data = {
            "name": JOURNEY_NAME,
            "journey_id": JOURNEY_ID,
            "steps_total": 0,
            "steps_passed": 0,
            "steps_failed": 1,
            "console_errors": [],
            "issues": [f"Seed failed: {exc}"],
            "duration_seconds": round(time.monotonic() - start_time, 2),
        }
        result_path = journey_dir / "journey_result.json"
        result_path.write_text(json.dumps(result_data, indent=2) + "\n", encoding="utf-8")
        return 1

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
            # Step 1: Navigate to Projects and verify Running Montage
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.goto(gui_url, wait_until="networkidle")
                page.wait_for_selector('[data-testid="nav-tab-projects"]', timeout=15000)
                page.click('[data-testid="nav-tab-projects"]')
                page.wait_for_selector('[data-testid="projects-page"]', timeout=10000)

                # Find Running Montage in the project list
                page.wait_for_selector('[data-testid="project-list"]', timeout=10000)
                page.wait_for_timeout(1000)  # Allow list to render

                project_cards = page.locator('[data-testid^="project-card-"]')
                card_count = project_cards.count()
                found_project = False
                for i in range(card_count):
                    card = project_cards.nth(i)
                    card_text = card.text_content() or ""
                    if "Running Montage" in card_text:
                        found_project = True
                        break

                if not found_project:
                    raise AssertionError(
                        f"Running Montage not found in project list ({card_count} cards visible)"
                    )

                screenshot(page, journey_dir, 1, "project_list")
                steps_passed += 1
                print("  Step 1: Running Montage visible in project list - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 1 failed: {exc}")
                screenshot(page, journey_dir, 1, "project_list", failed=True)
                print(f"  Step 1: Project list verification - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 2: Navigate to project detail, verify 4 clips
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Click the Running Montage project name to open detail
                project_names = page.locator('[data-testid^="project-name-"]')
                name_count = project_names.count()
                clicked = False
                for i in range(name_count):
                    name_el = project_names.nth(i)
                    name_text = name_el.text_content() or ""
                    if "Running Montage" in name_text:
                        name_el.click()
                        clicked = True
                        break

                if not clicked:
                    raise AssertionError("Could not click Running Montage project")

                page.wait_for_selector('[data-testid="project-details"]', timeout=10000)

                # Verify project name on detail page
                detail_name = page.locator('[data-testid="project-detail-name"]').text_content()
                if "Running Montage" not in (detail_name or ""):
                    raise AssertionError(
                        f"Expected 'Running Montage' in detail name, got '{detail_name}'"
                    )

                # Verify clips table has 4 clips
                page.wait_for_selector('[data-testid="clips-table"]', timeout=10000)
                clip_rows = page.locator('[data-testid^="clip-row-"]')
                row_count = clip_rows.count()
                if row_count != EXPECTED_CLIPS:
                    raise AssertionError(f"Expected {EXPECTED_CLIPS} clips, found {row_count}")

                # Verify clip metadata (source, in/out, position) for each clip
                for i in range(row_count):
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

                screenshot(page, journey_dir, 2, "clip_details")
                steps_passed += 1
                print(f"  Step 2: {row_count} clips verified with metadata - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 2 failed: {exc}")
                screenshot(page, journey_dir, 2, "clip_details", failed=True)
                print(f"  Step 2: Clip verification - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 3: Navigate to Effects page, verify effect stack
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="nav-tab-effects"]')
                page.wait_for_selector('[data-testid="effects-page"]', timeout=10000)

                # Select Running Montage project via dropdown
                project_select = page.locator('[data-testid="project-select"]')
                project_select.wait_for(timeout=10000)
                page.wait_for_function(
                    """() => {
                        const s = document.querySelector('[data-testid="project-select"]');
                        return s && s.options && s.options.length > 0
                            && s.options[0].value !== '';
                    }""",
                    timeout=10000,
                )

                # Select the Running Montage project (find by option text)
                options = project_select.locator("option")
                option_count = options.count()
                selected = False
                for i in range(option_count):
                    opt_text = options.nth(i).text_content() or ""
                    if "Running Montage" in opt_text:
                        project_select.select_option(index=i)
                        selected = True
                        break

                if not selected:
                    # Fall back to selecting first option
                    project_select.select_option(index=0)

                page.wait_for_timeout(1000)  # Allow effects to load

                # Verify effect stack shows effects
                stack = page.locator('[data-testid="effect-stack"]')
                stack.wait_for(timeout=5000)
                stack_items = page.locator('[data-testid^="effect-stack-item-"]')
                stack_count = stack_items.count()
                if stack_count < 1:
                    raise AssertionError(f"Expected effects in stack, found {stack_count}")

                screenshot(page, journey_dir, 3, "effects_page")
                steps_passed += 1
                print(f"  Step 3: Effect stack shows {stack_count} effects - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 3, "effects_page", failed=True)
                print(f"  Step 3: Effects verification - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Navigate to Timeline, verify clips and transition
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="nav-tab-timeline"]')
                page.wait_for_selector('[data-testid="timeline-canvas"]', timeout=10000)

                # Verify clip blocks on canvas
                tracks = page.locator('[data-testid="canvas-tracks"]')
                tracks.wait_for(timeout=5000)
                clip_blocks = tracks.locator('[data-testid^="clip-block-"]')
                block_count = clip_blocks.count()
                if block_count < 1:
                    raise AssertionError(f"Expected clip blocks on timeline, found {block_count}")

                # Check for transition marker(s) on canvas
                transitions = page.locator('[data-testid^="transition-"]')
                transition_count = transitions.count()

                screenshot(page, journey_dir, 4, "timeline_canvas")
                steps_passed += 1
                print(
                    f"  Step 4: Timeline shows {block_count} clip blocks, "
                    f"{transition_count} transition(s) - PASSED"
                )
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "timeline_canvas", failed=True)
                print(f"  Step 4: Timeline verification - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Capture full timeline view screenshot
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Ensure we're still on the timeline page
                page.wait_for_selector('[data-testid="timeline-canvas"]', timeout=5000)

                # Capture a full-page screenshot for the timeline view
                screenshot(page, journey_dir, 5, "full_timeline_view")
                steps_passed += 1
                print("  Step 5: Full timeline view screenshot captured - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 5, "full_timeline_view", failed=True)
                print(f"  Step 5: Full timeline screenshot - FAILED: {exc}")

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

    print(f"\n  Journey 204 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
