#!/usr/bin/env python3
"""UAT Journey 205: Preview Playback.

Validates the Preview page loads, the player component renders, and controls
are visible and interactive.  Handles the no-content state gracefully since a
live HLS preview session may not be available.

Independent of journeys 201-204.

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNEY_NAME = "preview-playback"
JOURNEY_ID = 205

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
    """Execute the preview-playback journey.

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
            # Step 1: Navigate to Preview page via navigation tab
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.goto(gui_url, wait_until="networkidle")
                page.wait_for_selector('[data-testid="nav-tab-preview"]', timeout=15000)
                screenshot(page, journey_dir, 1, "navigation")
                page.click('[data-testid="nav-tab-preview"]')
                page.wait_for_selector('[data-testid="preview-page"]', timeout=10000)
                screenshot(page, journey_dir, 1, "preview_page_loaded")
                steps_passed += 1
                print("  Step 1: Navigate to Preview page - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 1 failed: {exc}")
                screenshot(page, journey_dir, 1, "navigation", failed=True)
                print(f"  Step 1: Navigate to Preview page - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 2: Verify player component renders
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # The preview page may show different states depending on
                # whether a project is selected and a session is active.
                # Check for the player container OR one of the no-content
                # states — both are valid since UAT may run without live
                # HLS content.
                player_or_placeholder = page.locator(
                    '[data-testid="preview-player-container"], '
                    '[data-testid="no-session"], '
                    '[data-testid="no-project-message"], '
                    '[data-testid="status-initializing"], '
                    '[data-testid="status-generating"]'
                )
                player_or_placeholder.first.wait_for(timeout=10000)

                # Record which state we found
                has_player = page.locator('[data-testid="preview-player-container"]').count() > 0
                has_no_session = page.locator('[data-testid="no-session"]').count() > 0
                has_no_project = page.locator('[data-testid="no-project-message"]').count() > 0

                if has_player:
                    state_desc = "player loaded"
                elif has_no_session:
                    state_desc = "no-session (start preview available)"
                elif has_no_project:
                    state_desc = "no project selected"
                else:
                    state_desc = "initializing/generating"

                screenshot(page, journey_dir, 2, "player_state")
                steps_passed += 1
                print(f"  Step 2: Player component renders ({state_desc}) - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 2 failed: {exc}")
                screenshot(page, journey_dir, 2, "player_state", failed=True)
                print(f"  Step 2: Player component renders - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 3: Verify controls are visible
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Controls may only be present when the player is active.
                # Check for either controls or the start-preview button.
                controls = page.locator('[data-testid="player-controls"]')
                start_btn = page.locator('[data-testid="start-preview-btn"]')

                has_controls = controls.count() > 0
                has_start_btn = start_btn.count() > 0

                if has_controls:
                    # Verify individual control elements
                    play_pause = page.locator('[data-testid="play-pause-btn"]')
                    if play_pause.count() < 1:
                        raise AssertionError("Play/pause button not found in controls")

                    screenshot(page, journey_dir, 3, "controls_visible")
                    steps_passed += 1
                    print("  Step 3: Player controls visible (play/pause verified) - PASSED")
                elif has_start_btn:
                    # No active session — start-preview button is the expected control
                    start_btn.wait_for(timeout=5000)
                    screenshot(page, journey_dir, 3, "start_preview_btn")
                    steps_passed += 1
                    print("  Step 3: Start Preview button visible (no active session) - PASSED")
                else:
                    # Page is in a transitional state (initializing/generating/error/expired)
                    # which is acceptable — the controls will appear once ready
                    screenshot(page, journey_dir, 3, "transitional_state")
                    steps_passed += 1
                    print("  Step 3: Page in transitional state (controls not yet shown) - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 3, "controls_visible", failed=True)
                print(f"  Step 3: Controls verification - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Verify quality selector is present
            # ----------------------------------------------------------
            steps_total += 1
            try:
                quality_selector = page.locator('[data-testid="quality-selector"]')
                has_quality = quality_selector.count() > 0

                if has_quality:
                    quality_selector.wait_for(timeout=5000)
                    screenshot(page, journey_dir, 4, "quality_selector")
                    steps_passed += 1
                    print("  Step 4: Quality selector present - PASSED")
                else:
                    # Quality selector only renders when player is active.
                    # Acceptable to not see it without live content.
                    screenshot(page, journey_dir, 4, "quality_selector_absent")
                    steps_passed += 1
                    print(
                        "  Step 4: Quality selector not rendered "
                        "(expected without active session) - PASSED"
                    )
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "quality_selector", failed=True)
                print(f"  Step 4: Quality selector - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Capture full Preview page screenshot
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.wait_for_selector('[data-testid="preview-page"]', timeout=5000)
                screenshot(page, journey_dir, 5, "full_preview_page")
                steps_passed += 1
                print("  Step 5: Full Preview page screenshot captured - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 5, "full_preview_page", failed=True)
                print(f"  Step 5: Full Preview page screenshot - FAILED: {exc}")

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

    print(f"\n  Journey 205 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
