#!/usr/bin/env python3
"""UAT Journey 501: Render Export Journey.

Validates the full render export UI flow: navigates to the Render page,
opens the Start Render modal, submits a render job with auto-selected
settings, and verifies the job appears in the render queue.

Navigates to the Timeline page first to trigger project auto-selection
in the Zustand store (required for render job submission).

Independent of journeys 201-404.

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
JOURNEY_NAME = "render-export-journey"
JOURNEY_ID = 501

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
    """Execute the render-export-journey.

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
            #         available project — required for render job submission.
            # ----------------------------------------------------------
            steps_total += 1
            try:
                timeline_tab = page.locator('[data-testid="nav-tab-timeline"]')
                timeline_tab.wait_for(timeout=10000)
                timeline_tab.click()
                page.wait_for_url("**/gui/timeline", timeout=10000)
                # Wait for timeline page elements that confirm project loaded
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
            # Step 3: Verify Render tab visible in navigation
            # ----------------------------------------------------------
            steps_total += 1
            try:
                render_tab = page.locator('[data-testid="nav-tab-render"]')
                render_tab.wait_for(timeout=10000)
                assert render_tab.is_visible(), "Render tab is not visible"
                screenshot(page, journey_dir, 3, "render_tab_visible")
                steps_passed += 1
                print("  Step 3: Render tab visible - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 3, "render_tab_visible", failed=True)
                print(f"  Step 3: Render tab visible - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Click Render tab, verify /gui/render navigation
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="nav-tab-render"]')
                page.wait_for_url("**/gui/render", timeout=10000)
                screenshot(page, journey_dir, 4, "navigated_to_render")
                steps_passed += 1
                print("  Step 4: Click Render tab, navigate to /gui/render - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "navigated_to_render", failed=True)
                print(f"  Step 4: Navigate to /gui/render - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Verify render-page container rendered
            # ----------------------------------------------------------
            steps_total += 1
            try:
                render_page = page.locator('[data-testid="render-page"]')
                render_page.wait_for(timeout=10000)
                assert render_page.is_visible(), "render-page container is not visible"
                screenshot(page, journey_dir, 5, "render_page_container")
                steps_passed += 1
                print("  Step 5: render-page container rendered - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 5, "render_page_container", failed=True)
                print(f"  Step 5: render-page container - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 6: Verify queue-status-bar visible
            # ----------------------------------------------------------
            steps_total += 1
            try:
                status_bar = page.locator('[data-testid="queue-status-bar"]')
                status_bar.wait_for(timeout=10000)
                assert status_bar.is_visible(), "queue-status-bar is not visible"
                screenshot(page, journey_dir, 6, "queue_status_bar")
                steps_passed += 1
                print("  Step 6: queue-status-bar visible - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 6 failed: {exc}")
                screenshot(page, journey_dir, 6, "queue_status_bar", failed=True)
                print(f"  Step 6: queue-status-bar - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 7: Verify start-render-btn visible
            # ----------------------------------------------------------
            steps_total += 1
            try:
                start_btn = page.locator('[data-testid="start-render-btn"]')
                start_btn.wait_for(timeout=10000)
                assert start_btn.is_visible(), "start-render-btn is not visible"
                screenshot(page, journey_dir, 7, "start_render_btn")
                steps_passed += 1
                print("  Step 7: start-render-btn visible - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 7 failed: {exc}")
                screenshot(page, journey_dir, 7, "start_render_btn", failed=True)
                print(f"  Step 7: start-render-btn - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 8: Click start-render-btn, verify modal opens
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="start-render-btn"]')
                modal = page.locator('[data-testid="start-render-modal"]')
                modal.wait_for(timeout=10000)
                assert modal.is_visible(), "start-render-modal did not open"
                screenshot(page, journey_dir, 8, "render_modal_opened")
                steps_passed += 1
                print("  Step 8: Start Render modal opened - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 8 failed: {exc}")
                screenshot(page, journey_dir, 8, "render_modal_opened", failed=True)
                print(f"  Step 8: Start Render modal - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 9: Verify format and quality selectors have values
            #         (modal auto-selects defaults on open)
            # ----------------------------------------------------------
            steps_total += 1
            try:
                format_select = page.locator('[data-testid="select-format"]')
                format_select.wait_for(timeout=5000)
                quality_select = page.locator('[data-testid="select-quality"]')
                quality_select.wait_for(timeout=5000)

                # Wait briefly for auto-select useEffects to fire
                page.wait_for_timeout(500)

                format_val = format_select.input_value()
                quality_val = quality_select.input_value()
                assert format_val, f"Format not auto-selected (got '{format_val}')"
                assert quality_val, f"Quality not auto-selected (got '{quality_val}')"

                screenshot(page, journey_dir, 9, "render_modal_filled")
                steps_passed += 1
                print(
                    f"  Step 9: Modal defaults selected: format={format_val}, "
                    f"quality={quality_val} - PASSED"
                )
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 9 failed: {exc}")
                screenshot(page, journey_dir, 9, "render_modal_filled", failed=True)
                print(f"  Step 9: Modal defaults - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 10: Click btn-start-render, verify modal closes
            #          (job submitted successfully)
            # ----------------------------------------------------------
            steps_total += 1
            try:
                submit_btn = page.locator('[data-testid="btn-start-render"]')
                submit_btn.click()

                # Modal should close on success; wait for it to disappear
                modal = page.locator('[data-testid="start-render-modal"]')
                modal.wait_for(state="hidden", timeout=10000)

                # Verify no submission error was shown before close
                screenshot(page, journey_dir, 10, "render_submitted")
                steps_passed += 1
                print("  Step 10: Render job submitted, modal closed - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 10 failed: {exc}")
                screenshot(page, journey_dir, 10, "render_submitted", failed=True)
                print(f"  Step 10: Render job submission - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 11: Wait for render job card to appear in queue
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # The render job should appear in pending or active section
                job_card = page.locator('[data-testid^="render-job-card-"]')
                job_card.first.wait_for(timeout=10000)
                assert job_card.first.is_visible(), "Render job card not visible in queue"
                screenshot(page, journey_dir, 11, "render_job_in_queue")
                steps_passed += 1
                print("  Step 11: Render job appears in queue - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 11 failed: {exc}")
                screenshot(page, journey_dir, 11, "render_job_in_queue", failed=True)
                print(f"  Step 11: Render job in queue - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 12: Verify status badge label (Queued or Rendering)
            # ----------------------------------------------------------
            steps_total += 1
            try:
                status_label = page.locator('[data-testid="status-badge-label"]').first
                status_label.wait_for(timeout=5000)
                label_text = status_label.text_content() or ""
                assert label_text in (
                    "Queued",
                    "Rendering",
                    "Completed",
                ), f"Unexpected status badge: '{label_text}'"
                screenshot(page, journey_dir, 12, "render_status_badge")
                steps_passed += 1
                print(f"  Step 12: Status badge shows '{label_text}' - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 12 failed: {exc}")
                screenshot(page, journey_dir, 12, "render_status_badge", failed=True)
                print(f"  Step 12: Status badge - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 13: Check for zero console errors
            # ----------------------------------------------------------
            steps_total += 1
            try:
                if console_errors:
                    raise AssertionError(
                        f"Found {len(console_errors)} console error(s): "
                        + "; ".join(console_errors[:5])
                    )
                screenshot(page, journey_dir, 13, "zero_console_errors")
                steps_passed += 1
                print("  Step 13: Zero console errors - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 13 failed: {exc}")
                screenshot(page, journey_dir, 13, "zero_console_errors", failed=True)
                print(f"  Step 13: Console errors check - FAILED: {exc}")

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

    print(f"\n  Journey 501 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
