#!/usr/bin/env python3
"""UAT Journey 503: Render Settings Journey.

Validates the Start Render modal settings interaction: opens the modal,
changes format, quality, and encoder selections, and verifies that the
command-preview updates after each change.

Navigates to the Timeline page first to trigger project auto-selection
in the Zustand store (required for render job submission context).

Independent of journeys 201-404. Depends on J501 (render page accessible).

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
JOURNEY_NAME = "render-settings"
JOURNEY_ID = 503

# Benign console error patterns to ignore
BENIGN_PATTERNS = ["favicon"]

# Time to wait (ms) after a settings change before reading the updated preview.
# Accounts for the 300ms debounce in StartRenderModal plus API round-trip.
PREVIEW_UPDATE_WAIT_MS = 2000


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


def get_select_options(page: Any, testid: str) -> list[str]:
    """Return all option values for a <select> identified by data-testid.

    Args:
        page: Playwright Page object.
        testid: The data-testid attribute value of the select element.

    Returns:
        List of option value strings.
    """
    return page.locator(f'[data-testid="{testid}"]').evaluate(  # type: ignore[no-any-return]
        "el => Array.from(el.options).map(o => o.value)"
    )


def run() -> int:
    """Execute the render-settings-journey.

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
            # Step 1: Navigate to app root, verify shell loads
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.goto(gui_url, wait_until="networkidle")
                page.wait_for_selector("[data-testid^='nav-tab-']", timeout=15000)
                screenshot(page, journey_dir, 1, "shell_loaded")
                steps_passed += 1
                print("  Step 1: Navigate to app root, shell loads - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 1 failed: {exc}")
                screenshot(page, journey_dir, 1, "shell_loaded", failed=True)
                print(f"  Step 1: Navigate to app root - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 2: Navigate to Timeline page to trigger project
            #         auto-selection in the Zustand store. The Timeline
            #         page's useEffect sets selectedProjectId to the first
            #         available project — required for render context.
            # ----------------------------------------------------------
            steps_total += 1
            try:
                timeline_tab = page.locator('[data-testid="nav-tab-timeline"]')
                timeline_tab.wait_for(timeout=10000)
                timeline_tab.click()
                page.wait_for_url("**/gui/timeline", timeout=10000)
                page.wait_for_selector('[data-testid="timeline-page"]', timeout=10000)
                screenshot(page, journey_dir, 2, "timeline_for_project_select")
                steps_passed += 1
                print("  Step 2: Navigate to Timeline for project auto-selection - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 2 failed: {exc}")
                screenshot(page, journey_dir, 2, "timeline_for_project_select", failed=True)
                print(f"  Step 2: Timeline navigation - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 3: Click Render tab, navigate to /gui/render,
            #         verify render-page container
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="nav-tab-render"]')
                page.wait_for_url("**/gui/render", timeout=10000)
                render_page = page.locator('[data-testid="render-page"]')
                render_page.wait_for(timeout=10000)
                assert render_page.is_visible(), "render-page container is not visible"
                screenshot(page, journey_dir, 3, "render_page")
                steps_passed += 1
                print("  Step 3: Navigate to /gui/render - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 3, "render_page", failed=True)
                print(f"  Step 3: Navigate to /gui/render - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Click start-render-btn, verify modal opens
            # ----------------------------------------------------------
            steps_total += 1
            try:
                start_btn = page.locator('[data-testid="start-render-btn"]')
                start_btn.wait_for(timeout=10000)
                start_btn.click()
                modal = page.locator('[data-testid="start-render-modal"]')
                modal.wait_for(timeout=10000)
                assert modal.is_visible(), "start-render-modal did not open"
                screenshot(page, journey_dir, 4, "modal_opened")
                steps_passed += 1
                print("  Step 4: Start Render modal opened - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "modal_opened", failed=True)
                print(f"  Step 4: Start Render modal - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Wait for initial command-preview to appear
            #         (auto-selected defaults trigger a preview fetch)
            # ----------------------------------------------------------
            steps_total += 1
            initial_command: str = ""
            try:
                # Allow time for auto-select useEffects and debounce to fire
                page.wait_for_timeout(500)
                command_preview = page.locator('[data-testid="command-preview"]')
                command_preview.wait_for(timeout=10000)
                initial_command = command_preview.text_content() or ""
                assert initial_command, "Initial command-preview is empty"
                screenshot(page, journey_dir, 5, "initial_preview")
                steps_passed += 1
                print("  Step 5: Initial command-preview visible - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 5, "initial_preview", failed=True)
                print(f"  Step 5: Initial command-preview - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 6: Change format, verify command-preview updates
            # ----------------------------------------------------------
            steps_total += 1
            post_format_command: str = ""
            try:
                format_options = get_select_options(page, "select-format")
                assert len(format_options) >= 2, (
                    f"Expected >=2 format options, got {len(format_options)}: {format_options}"
                )
                # Select the second format (different from auto-selected first)
                new_format = format_options[1]
                page.locator('[data-testid="select-format"]').select_option(value=new_format)

                # Wait for debounce (300ms) + API round-trip + margin
                page.wait_for_timeout(PREVIEW_UPDATE_WAIT_MS)
                command_preview = page.locator('[data-testid="command-preview"]')
                command_preview.wait_for(timeout=8000)
                post_format_command = command_preview.text_content() or ""
                assert post_format_command, "Command preview empty after format change"
                assert post_format_command != initial_command, (
                    f"Command preview did not change after format change to '{new_format}' "
                    f"(still: {post_format_command!r})"
                )
                screenshot(page, journey_dir, 6, f"format_changed_to_{new_format}")
                steps_passed += 1
                print(f"  Step 6: Format changed to '{new_format}', preview updated - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 6 failed: {exc}")
                screenshot(page, journey_dir, 6, "format_change_failed", failed=True)
                print(f"  Step 6: Format change - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 7: Change quality, verify command-preview updates
            # ----------------------------------------------------------
            steps_total += 1
            post_quality_command: str = ""
            try:
                quality_select = page.locator('[data-testid="select-quality"]')
                quality_options = get_select_options(page, "select-quality")
                assert len(quality_options) >= 2, (
                    f"Expected >=2 quality options, got {len(quality_options)}: {quality_options}"
                )
                # Pick a quality different from the currently-selected one
                current_quality = quality_select.input_value()
                other_qualities = [q for q in quality_options if q != current_quality]
                new_quality = other_qualities[0]
                quality_select.select_option(value=new_quality)

                page.wait_for_timeout(PREVIEW_UPDATE_WAIT_MS)
                command_preview = page.locator('[data-testid="command-preview"]')
                command_preview.wait_for(timeout=8000)
                post_quality_command = command_preview.text_content() or ""
                assert post_quality_command, "Command preview empty after quality change"
                assert post_quality_command != post_format_command, (
                    f"Command preview did not change after quality change to '{new_quality}' "
                    f"(still: {post_quality_command!r})"
                )
                screenshot(page, journey_dir, 7, f"quality_changed_to_{new_quality}")
                steps_passed += 1
                print(f"  Step 7: Quality changed to '{new_quality}', preview updated - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 7 failed: {exc}")
                screenshot(page, journey_dir, 7, "quality_change_failed", failed=True)
                print(f"  Step 7: Quality change - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 8: Change encoder (if multiple available),
            #         verify command-preview updates
            # ----------------------------------------------------------
            steps_total += 1
            try:
                encoder_select = page.locator('[data-testid="select-encoder"]')
                encoder_options = get_select_options(page, "select-encoder")
                if len(encoder_options) < 2:
                    # Single encoder available — cannot change to a different value.
                    # Pass with a note; single-encoder environments are valid.
                    screenshot(page, journey_dir, 8, "encoder_single_only")
                    steps_passed += 1
                    print(
                        f"  Step 8: Single encoder available {encoder_options}; "
                        "encoder change not possible - PASSED (note: single encoder)"
                    )
                else:
                    current_encoder = encoder_select.input_value()
                    other_encoders = [e for e in encoder_options if e != current_encoder]
                    new_encoder = other_encoders[0]
                    encoder_select.select_option(value=new_encoder)

                    page.wait_for_timeout(PREVIEW_UPDATE_WAIT_MS)
                    command_preview = page.locator('[data-testid="command-preview"]')
                    command_preview.wait_for(timeout=8000)
                    post_encoder_command = command_preview.text_content() or ""
                    assert post_encoder_command, "Command preview empty after encoder change"
                    assert post_encoder_command != post_quality_command, (
                        f"Command preview did not change after encoder change to '{new_encoder}' "
                        f"(still: {post_encoder_command!r})"
                    )
                    screenshot(page, journey_dir, 8, f"encoder_changed_to_{new_encoder}")
                    steps_passed += 1
                    print(f"  Step 8: Encoder changed to '{new_encoder}', preview updated - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 8 failed: {exc}")
                screenshot(page, journey_dir, 8, "encoder_change_failed", failed=True)
                print(f"  Step 8: Encoder change - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 9: Check for zero console errors
            # ----------------------------------------------------------
            steps_total += 1
            try:
                if console_errors:
                    raise AssertionError(
                        f"Found {len(console_errors)} console error(s): "
                        + "; ".join(console_errors[:5])
                    )
                screenshot(page, journey_dir, 9, "zero_console_errors")
                steps_passed += 1
                print("  Step 9: Zero console errors - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 9 failed: {exc}")
                screenshot(page, journey_dir, 9, "zero_console_errors", failed=True)
                print(f"  Step 9: Console errors check - FAILED: {exc}")

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

    print(f"\n  Journey 503 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
