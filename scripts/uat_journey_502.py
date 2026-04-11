#!/usr/bin/env python3
"""UAT Journey 502: Render Queue Journey.

Validates render queue ordering and concurrency limits by submitting 5 render
jobs through the GUI and verifying that they accumulate in the pending section
while the queue status bar reports the correct capacity (max_concurrent=4).

Since no background render worker processes jobs in this environment, all
submitted jobs remain in QUEUED (pending) state indefinitely — this is the
expected condition for verifying queue saturation behavior.

Navigates to the Timeline page first to trigger project auto-selection in the
Zustand store (required for render job submission).

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
JOURNEY_NAME = "render-queue-journey"
JOURNEY_ID = 502

# Submit more than max_concurrent (4) to create an observable pending backlog
NUM_JOBS = 5

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


def submit_render_job(page: Any) -> None:
    """Open StartRenderModal, wait for auto-selection, and submit one render job.

    Waits for the modal to open, allows auto-select useEffects to fire, submits
    the form, and waits for the modal to close on success.

    Args:
        page: Playwright Page object.

    Raises:
        Exception: If any Playwright interaction or assertion fails.
    """
    page.click('[data-testid="start-render-btn"]')
    modal = page.locator('[data-testid="start-render-modal"]')
    modal.wait_for(timeout=10000)
    # Allow auto-select useEffects to fire (format, quality, encoder)
    page.wait_for_timeout(500)
    page.click('[data-testid="btn-start-render"]')
    modal.wait_for(state="hidden", timeout=10000)


def run() -> int:
    """Execute the render-queue-journey.

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
            # Step 3: Navigate to Render page and verify UI elements
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="nav-tab-render"]')
                page.wait_for_url("**/gui/render", timeout=10000)
                page.locator('[data-testid="render-page"]').wait_for(timeout=10000)
                page.locator('[data-testid="queue-status-bar"]').wait_for(timeout=10000)
                page.locator('[data-testid="start-render-btn"]').wait_for(timeout=10000)
                screenshot(page, journey_dir, 3, "render_page_ready")
                steps_passed += 1
                print("  Step 3: Navigate to Render page, UI elements visible - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 3, "render_page_ready", failed=True)
                print(f"  Step 3: Render page navigation - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Submit NUM_JOBS render jobs via modal to saturate
            #         the queue beyond max_concurrent (4). All jobs remain
            #         in QUEUED (pending) state since no worker processes
            #         them. Captures screenshots after job 1 and job NUM_JOBS.
            # ----------------------------------------------------------
            steps_total += 1
            try:
                for i in range(1, NUM_JOBS + 1):
                    submit_render_job(page)
                    # Brief pause to allow fetchJobs to complete before next submission
                    page.wait_for_timeout(300)
                    if i == 1:
                        screenshot(page, journey_dir, 4, f"after_job_{i}_submitted")
                screenshot(page, journey_dir, 4, f"after_all_{NUM_JOBS}_jobs_submitted")
                steps_passed += 1
                print(f"  Step 4: Submit {NUM_JOBS} render jobs via modal - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "job_submission_failed", failed=True)
                print(f"  Step 4: Render job submission - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Verify queue-status-bar shows max_concurrent capacity
            # ----------------------------------------------------------
            steps_total += 1
            try:
                status_bar = page.locator('[data-testid="queue-status-bar"]')
                status_bar.wait_for(timeout=10000)
                bar_text = status_bar.text_content() or ""
                assert "Capacity:" in bar_text, (
                    f"queue-status-bar missing 'Capacity:' text. Got: '{bar_text}'"
                )
                # Verify max_concurrent is displayed as 4
                assert "4" in bar_text, (
                    f"queue-status-bar does not show capacity=4. Got: '{bar_text}'"
                )
                screenshot(page, journey_dir, 5, "queue_status_bar_capacity")
                steps_passed += 1
                print(f"  Step 5: queue-status-bar shows capacity — '{bar_text.strip()}' - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 5, "queue_status_bar_capacity", failed=True)
                print(f"  Step 5: queue-status-bar capacity - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 6: Verify active-jobs-section shows no active jobs
            #         (no render worker runs in this environment)
            # ----------------------------------------------------------
            steps_total += 1
            try:
                active_section = page.locator('[data-testid="active-jobs-section"]')
                active_section.wait_for(timeout=10000)
                # Active job cards would have data-testid matching render-job-card-*
                active_cards = active_section.locator('[data-testid^="render-job-card-"]')
                active_count = active_cards.count()
                assert active_count == 0, (
                    f"Expected 0 active jobs (no render worker), found {active_count}"
                )
                screenshot(page, journey_dir, 6, "active_section_empty")
                steps_passed += 1
                print("  Step 6: active-jobs-section shows no active jobs - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 6 failed: {exc}")
                screenshot(page, journey_dir, 6, "active_section_empty", failed=True)
                print(f"  Step 6: active-jobs-section - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 7: Verify pending-jobs-section contains NUM_JOBS cards
            # ----------------------------------------------------------
            steps_total += 1
            try:
                pending_section = page.locator('[data-testid="pending-jobs-section"]')
                pending_section.wait_for(timeout=10000)

                # Wait for all NUM_JOBS cards to appear (polling with timeout)
                job_cards = pending_section.locator('[data-testid^="render-job-card-"]')
                job_cards.first.wait_for(timeout=10000)

                # Poll until all expected cards are present
                deadline = time.monotonic() + 10.0
                actual_count = 0
                while time.monotonic() < deadline:
                    actual_count = job_cards.count()
                    if actual_count >= NUM_JOBS:
                        break
                    page.wait_for_timeout(500)

                assert actual_count >= NUM_JOBS, (
                    f"Expected >= {NUM_JOBS} pending jobs, found {actual_count}"
                )
                screenshot(page, journey_dir, 7, f"pending_section_{actual_count}_jobs")
                steps_passed += 1
                print(f"  Step 7: pending-jobs-section shows {actual_count} pending jobs - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 7 failed: {exc}")
                screenshot(page, journey_dir, 7, "pending_section_jobs", failed=True)
                print(f"  Step 7: pending-jobs-section - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 8: Check for zero console errors
            # ----------------------------------------------------------
            steps_total += 1
            try:
                if console_errors:
                    raise AssertionError(
                        f"Found {len(console_errors)} console error(s): "
                        + "; ".join(console_errors[:5])
                    )
                screenshot(page, journey_dir, 8, "zero_console_errors")
                steps_passed += 1
                print("  Step 8: Zero console errors - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 8 failed: {exc}")
                screenshot(page, journey_dir, 8, "zero_console_errors", failed=True)
                print(f"  Step 8: Console errors check - FAILED: {exc}")

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

    print(f"\n  Journey 502 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
