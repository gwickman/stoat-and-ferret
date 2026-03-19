#!/usr/bin/env python3
"""UAT Journey 201: Scan Library.

Validates the scan, browse, and FTS5 search workflow against real video data
in the browser. Navigates to the Library tab, triggers a directory scan, verifies
grid population with metadata, and exercises FTS5 search.

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
JOURNEY_NAME = "scan-library"
JOURNEY_ID = 201
VIDEOS_DIR = str((PROJECT_ROOT / "videos").resolve())

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
    """Execute the scan-library journey.

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
            # Step 1: Navigate to Library tab
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.goto(gui_url, wait_until="networkidle")
                page.wait_for_selector('[data-testid="nav-tab-library"]', timeout=15000)
                screenshot(page, journey_dir, 1, "navigation")
                page.click('[data-testid="nav-tab-library"]')
                page.wait_for_selector('[data-testid="library-page"]', timeout=10000)
                steps_passed += 1
                print("  Step 1: Navigate to Library tab - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 1 failed: {exc}")
                screenshot(page, journey_dir, 1, "navigation", failed=True)
                print(f"  Step 1: Navigate to Library tab - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 2: Open scan modal and submit scan
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="scan-button"]')
                page.wait_for_selector('[data-testid="scan-modal-overlay"]', timeout=5000)
                screenshot(page, journey_dir, 2, "scan_modal")

                # Enter directory path
                scan_input = page.locator('[data-testid="scan-directory-input"]')
                scan_input.fill(VIDEOS_DIR)

                # Submit scan
                page.click('[data-testid="scan-submit"]')
                screenshot(page, journey_dir, 3, "scan_progress")
                steps_passed += 1
                print("  Step 2: Open scan modal and submit - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 2 failed: {exc}")
                screenshot(page, journey_dir, 2, "scan_modal", failed=True)
                print(f"  Step 2: Open scan modal and submit - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 3: Wait for scan complete and verify grid
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Wait for scan-complete indicator (30s timeout)
                page.wait_for_selector('[data-testid="scan-complete"]', timeout=90000)

                # Close the scan modal
                page.click('[data-testid="scan-cancel"]')
                page.wait_for_selector(
                    '[data-testid="scan-modal-overlay"]',
                    state="detached",
                    timeout=5000,
                )

                # Wait for grid to load (may still be fetching after modal close)
                page.wait_for_selector('[data-testid="video-grid"]', timeout=10000)

                # Verify at least one video card exists
                cards = page.locator('[data-testid^="video-card-"]')
                card_count = cards.count()
                if card_count < 1:
                    raise AssertionError(f"Expected at least 1 video card, found {card_count}")

                screenshot(page, journey_dir, 4, "grid_populated")
                steps_passed += 1
                print(f"  Step 3: Scan complete, grid has {card_count} cards - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 4, "grid_populated", failed=True)
                print(f"  Step 3: Scan complete and grid verification - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Verify video card metadata
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Check first video card has filename and duration
                first_card = page.locator('[data-testid^="video-card-"]').first
                first_card.wait_for(timeout=5000)

                # Extract the video ID from the card's testid
                card_testid = first_card.get_attribute("data-testid") or ""
                video_id = card_testid.replace("video-card-", "")

                # Verify filename
                filename_el = page.locator(f'[data-testid="video-filename-{video_id}"]')
                filename_text = filename_el.text_content() or ""
                if not filename_text.strip():
                    raise AssertionError("Video filename is empty")

                # Verify duration
                duration_el = page.locator(f'[data-testid="video-duration-{video_id}"]')
                duration_text = duration_el.text_content() or ""
                if not duration_text.strip():
                    raise AssertionError("Video duration is empty")

                steps_passed += 1
                print(
                    f"  Step 4: Metadata verified "
                    f"(filename={filename_text!r}, duration={duration_text!r}) - PASSED"
                )
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                print(f"  Step 4: Video card metadata - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: FTS5 search
            # ----------------------------------------------------------
            steps_total += 1
            try:
                search_bar = page.locator('[data-testid="search-bar"]')
                search_bar.fill("running1")

                # Wait for debounce (300ms) + API response
                page.wait_for_timeout(1000)

                # Wait for grid to reflect search results
                page.wait_for_selector('[data-testid="video-grid"]', timeout=10000)

                # Verify the grid has results
                result_cards = page.locator('[data-testid^="video-card-"]')
                result_count = result_cards.count()
                if result_count < 1:
                    raise AssertionError(
                        f"Search for 'running1' returned {result_count} results, expected >= 1"
                    )

                # Verify at least one result contains "running1" in the filename
                found_match = False
                for i in range(result_count):
                    card = result_cards.nth(i)
                    card_tid = card.get_attribute("data-testid") or ""
                    vid = card_tid.replace("video-card-", "")
                    fn_el = page.locator(f'[data-testid="video-filename-{vid}"]')
                    fn_text = (fn_el.text_content() or "").lower()
                    if "running1" in fn_text:
                        found_match = True
                        break

                if not found_match:
                    raise AssertionError("No search result contains 'running1' in filename")

                screenshot(page, journey_dir, 5, "search_results")
                steps_passed += 1
                print(f"  Step 5: FTS5 search returned {result_count} result(s) - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 5, "search_results", failed=True)
                print(f"  Step 5: FTS5 search - FAILED: {exc}")

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

    print(f"\n  Journey 201 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
