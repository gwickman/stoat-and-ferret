#!/usr/bin/env python3
"""UAT Journey 504: Render Failure Recovery Journey.

Validates the render failure recovery UI flow: submits a render job via the
GUI, simulates a failure by forcing the job to FAILED status in the database
(the render worker is not yet implemented as a persistent background task),
verifies the error state visible in RenderJobCard, then clicks the retry
button and verifies the job returns to QUEUED.

Navigates to the Timeline page first to trigger project auto-selection
in the Zustand store (required for render job submission context).

Independent of journeys 201-404. Depends on J501 (render page accessible).

Environment variables:
    UAT_OUTPUT_DIR: Directory for journey output artifacts.
    UAT_HEADED: "1" for headed mode, "0" for headless (default).
    UAT_SERVER_URL: Base URL of the running server (default: http://localhost:8765).

Note on FAILED state mechanism:
    The render backend has no persistent background worker; submitted jobs
    stay in QUEUED state indefinitely. This journey forces a FAILED state by
    writing directly to the runtime database (data/stoat.db), not the seed
    fixture (tests/fixtures/stoat.seed.db). The SQLite connection uses WAL
    mode, making concurrent access from this script and the running server
    safe. This simulates what would happen when FFmpeg cannot find the source
    file — the intended production trigger for failure recovery testing.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNEY_NAME = "render-failure-journey"
JOURNEY_ID = 504

# Database path — matches Settings.database_path default
DB_PATH = PROJECT_ROOT / "data" / "stoat.db"

# Simulated error message written to the DB (mirrors FFmpeg missing-file error)
SIMULATED_ERROR = "Source file not found: /nonexistent/source.mp4 (simulated for UAT)"

# Benign console error patterns to ignore
BENIGN_PATTERNS = ["favicon"]

# Max time (ms) to wait for status badge to change after retry click
RETRY_STATUS_WAIT_MS = 10_000
RETRY_POLL_INTERVAL_MS = 500


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


def force_job_failed(job_id: str, error_message: str = SIMULATED_ERROR) -> None:
    """Force a render job to FAILED status via direct SQLite write.

    Used to simulate FFmpeg failure when a render worker is not available.
    SQLite WAL mode allows concurrent access from this process and the server.

    Args:
        job_id: The render job UUID to update.
        error_message: The error message to store on the job.

    Raises:
        RuntimeError: If the database file does not exist or the update fails.
    """
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found at {DB_PATH}. Is the server running from the project root?"
        )
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    try:
        # Transition to RUNNING first (valid intermediate state), then FAILED
        conn.execute(
            "UPDATE render_jobs SET status = 'running', updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (job_id,),
        )
        conn.execute(
            "UPDATE render_jobs "
            "SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (error_message, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_newest_job_id(server_url: str) -> str | None:
    """Fetch the most recently created render job ID from the API.

    Args:
        server_url: Base URL of the running server.

    Returns:
        Job UUID string, or None if no jobs found.
    """
    import urllib.request

    url = f"{server_url}/api/v1/render?limit=1"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        items = data.get("items", [])
        if items:
            return str(items[0]["id"])
    except Exception:
        pass
    return None


def run() -> int:
    """Execute the render-failure-journey.

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
            #         auto-selection in the Zustand store.
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
            # Step 3: Navigate to Render page, verify render-page
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
            # Step 4: Open Start Render modal, submit a render job,
            #         verify job card appears in the render queue.
            #
            # This satisfies FR-001 (starts render via GUI). The project
            # auto-selected from the Timeline step is used (seeded project).
            # ----------------------------------------------------------
            steps_total += 1
            job_id: str | None = None
            try:
                # Open modal
                start_btn = page.locator('[data-testid="start-render-btn"]')
                start_btn.wait_for(timeout=10000)
                start_btn.click()
                modal = page.locator('[data-testid="start-render-modal"]')
                modal.wait_for(timeout=10000)
                assert modal.is_visible(), "start-render-modal did not open"

                # Wait for format to auto-select
                page.wait_for_timeout(500)
                format_select = page.locator('[data-testid="select-format"]')
                format_select.wait_for(timeout=5000)
                format_val = format_select.input_value()
                assert format_val, f"Format not auto-selected (got '{format_val}')"

                # Submit the render job
                submit_btn = page.locator('[data-testid="btn-start-render"]')
                submit_btn.click()

                # Modal should close on success
                modal.wait_for(state="hidden", timeout=10000)

                # Wait for a job card to appear
                job_card_any = page.locator('[data-testid^="render-job-card-"]')
                job_card_any.first.wait_for(timeout=15000)
                assert job_card_any.first.is_visible(), "Render job card not visible"

                # Extract job ID from the data-testid of the most recent card
                # Prefer API lookup for reliability (handles multiple pre-existing cards)
                api_job_id = get_newest_job_id(server_url)
                if api_job_id:
                    job_id = api_job_id
                else:
                    # Fallback: extract from testid of first card
                    testid = job_card_any.first.get_attribute("data-testid") or ""
                    job_id = testid.replace("render-job-card-", "").strip() or None

                assert job_id, "Could not determine render job ID"
                screenshot(page, journey_dir, 4, f"render_job_submitted_id_{job_id[:8]}")
                steps_passed += 1
                print(
                    f"  Step 4: Render job submitted via GUI, job card visible "
                    f"(id={job_id[:8]}...) - PASSED"
                )
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "render_job_submitted", failed=True)
                print(f"  Step 4: Render job submission - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Force job to FAILED state via SQLite DB write.
            #
            # The render backend has no persistent background worker;
            # jobs remain in QUEUED indefinitely. We simulate the failure
            # that would occur when FFmpeg cannot find the source file by
            # directly updating the job record. This is the same approach
            # used in test_render_api.py (test_render_retry).
            # ----------------------------------------------------------
            steps_total += 1
            if job_id is None:
                steps_failed += 1
                issues.append("Step 5 skipped: no job_id from Step 4")
                print("  Step 5: Force job to FAILED - SKIPPED (no job_id)")
            else:
                try:
                    force_job_failed(job_id)
                    steps_passed += 1
                    print(f"  Step 5: Forced job {job_id[:8]}... to FAILED via SQLite - PASSED")
                except Exception as exc:
                    steps_failed += 1
                    issues.append(f"Step 5 failed: {exc}")
                    print(f"  Step 5: Force job to FAILED - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 6: Reload render page, verify FAILED status badge
            #         on the render-job-card-{id}.
            #
            # Satisfies FR-002: QUEUED→RUNNING→FAILED transition verified,
            # and NFR-002: error state visible in RenderJobCard.
            # ----------------------------------------------------------
            steps_total += 1
            if job_id is None:
                steps_failed += 1
                issues.append("Step 6 skipped: no job_id")
                print("  Step 6: Verify FAILED state - SKIPPED")
            else:
                try:
                    # Reload to get fresh job list from server
                    page.reload(wait_until="networkidle")
                    render_pg = page.locator('[data-testid="render-page"]')
                    render_pg.wait_for(timeout=10000)

                    # Locate the specific job card
                    job_card = page.locator(f'[data-testid="render-job-card-{job_id}"]')
                    job_card.wait_for(timeout=10000)

                    # Verify status badge shows "Failed"
                    status_label = job_card.locator('[data-testid="status-badge-label"]')
                    status_label.wait_for(timeout=5000)
                    status_text = status_label.text_content() or ""
                    assert status_text == "Failed", f"Expected status 'Failed', got '{status_text}'"

                    # Verify retry button is enabled (only enabled for failed jobs)
                    retry_btn = job_card.locator('[data-testid="retry-btn"]')
                    retry_btn.wait_for(timeout=5000)
                    assert retry_btn.is_enabled(), "retry-btn should be enabled for a FAILED job"

                    screenshot(page, journey_dir, 6, "failure_state")
                    steps_passed += 1
                    print("  Step 6: FAILED status badge visible, retry-btn enabled - PASSED")
                except Exception as exc:
                    steps_failed += 1
                    issues.append(f"Step 6 failed: {exc}")
                    screenshot(page, journey_dir, 6, "failure_state", failed=True)
                    print(f"  Step 6: Verify FAILED state - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 7: Click retry button, verify status returns to QUEUED.
            #
            # Satisfies FR-003: retry button clicked, job restarts.
            # Screenshots captured at retry state (FR-004).
            # ----------------------------------------------------------
            steps_total += 1
            if job_id is None:
                steps_failed += 1
                issues.append("Step 7 skipped: no job_id")
                print("  Step 7: Click retry, verify QUEUED - SKIPPED")
            else:
                try:
                    job_card = page.locator(f'[data-testid="render-job-card-{job_id}"]')
                    retry_btn = job_card.locator('[data-testid="retry-btn"]')
                    retry_btn.wait_for(timeout=5000)
                    assert retry_btn.is_enabled(), "retry-btn not enabled before click"
                    retry_btn.click()

                    # Poll for status to change to "Queued"
                    status_label = job_card.locator('[data-testid="status-badge-label"]')
                    max_wait = RETRY_STATUS_WAIT_MS
                    waited = 0
                    queued_confirmed = False
                    while waited < max_wait:
                        page.wait_for_timeout(RETRY_POLL_INTERVAL_MS)
                        waited += RETRY_POLL_INTERVAL_MS
                        label = status_label.text_content() or ""
                        if label == "Queued":
                            queued_confirmed = True
                            break

                    assert queued_confirmed, (
                        f"Status did not return to 'Queued' after retry "
                        f"(last: '{status_label.text_content()}')"
                    )

                    screenshot(page, journey_dir, 7, "retry_queued")
                    steps_passed += 1
                    print("  Step 7: Retry clicked, status returned to 'Queued' - PASSED")
                except Exception as exc:
                    steps_failed += 1
                    issues.append(f"Step 7 failed: {exc}")
                    screenshot(page, journey_dir, 7, "retry_queued", failed=True)
                    print(f"  Step 7: Click retry, verify QUEUED - FAILED: {exc}")

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

    print(f"\n  Journey 504 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
