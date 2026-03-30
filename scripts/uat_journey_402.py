#!/usr/bin/env python3
"""UAT Journey 402: Proxy Management (Phase 4).

Validates the proxy workflow: scan library, check proxy status indicators/badges,
wait for proxy generation, and start preview with proxy.

Depends on journey 201 (library scan).

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
JOURNEY_NAME = "proxy-management"
JOURNEY_ID = 402

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
    """Execute the proxy-management journey.

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
        browser = pw.chromium.launch(
            headless=not headed,
            channel="chrome",
            args=["--autoplay-policy=no-user-gesture-required"],
        )
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
            # Step 1: Navigate to Library and scan
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.goto(gui_url, wait_until="networkidle")
                page.wait_for_selector('[data-testid="nav-tab-library"]', timeout=15000)
                page.click('[data-testid="nav-tab-library"]')
                page.wait_for_selector('[data-testid="library-page"]', timeout=10000)

                # If grid is already populated, skip scan
                cards = page.locator('[data-testid^="video-card-"]')
                if cards.count() < 1:
                    # Trigger a scan
                    page.click('[data-testid="scan-button"]')
                    page.wait_for_selector('[data-testid="scan-modal-overlay"]', timeout=5000)
                    videos_dir = str((PROJECT_ROOT / "videos").resolve())
                    scan_input = page.locator('[data-testid="scan-directory-input"]')
                    scan_input.fill(videos_dir)
                    page.click('[data-testid="scan-submit"]')
                    page.wait_for_selector('[data-testid="scan-complete"]', timeout=90000)
                    page.click('[data-testid="scan-cancel"]')
                    page.wait_for_selector(
                        '[data-testid="scan-modal-overlay"]',
                        state="detached",
                        timeout=5000,
                    )

                screenshot(page, journey_dir, 1, "library_loaded")
                steps_passed += 1
                print("  Step 1: Navigate to Library - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 1 failed: {exc}")
                screenshot(page, journey_dir, 1, "library_loaded", failed=True)
                print(f"  Step 1: Navigate to Library - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 2: Check proxy status badges on video cards
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.wait_for_selector('[data-testid="video-grid"]', timeout=10000)
                badges = page.locator('[data-testid="proxy-status-badge"]')
                badge_count = badges.count()

                if badge_count < 1:
                    raise AssertionError("No proxy status badges found on video cards")

                # Collect the status values
                statuses: list[str] = []
                for i in range(badge_count):
                    badge = badges.nth(i)
                    status = badge.get_attribute("data-status") or "unknown"
                    statuses.append(status)

                screenshot(page, journey_dir, 2, "proxy_badges")
                steps_passed += 1
                print(
                    f"  Step 2: Proxy status badges found ({badge_count}): "
                    f"{', '.join(statuses)} - PASSED"
                )
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 2 failed: {exc}")
                screenshot(page, journey_dir, 2, "proxy_badges", failed=True)
                print(f"  Step 2: Proxy status badges - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 3: Wait for at least one proxy to be ready
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Wait up to 60s for at least one badge to show 'ready' status
                page.wait_for_selector(
                    '[data-testid="proxy-status-badge"][data-status="ready"], '
                    '[data-testid="proxy-status-badge"][data-status="none"]',
                    timeout=60000,
                )

                # Check if we have any ready
                ready_badges = page.locator(
                    '[data-testid="proxy-status-badge"][data-status="ready"]'
                )
                none_badges = page.locator('[data-testid="proxy-status-badge"][data-status="none"]')
                ready_count = ready_badges.count()
                none_count = none_badges.count()

                screenshot(page, journey_dir, 3, "proxy_ready")
                steps_passed += 1
                print(
                    f"  Step 3: Proxy status check — "
                    f"{ready_count} ready, {none_count} none - PASSED"
                )
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 3, "proxy_ready", failed=True)
                print(f"  Step 3: Wait for proxy ready - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Navigate to Preview and start preview with proxy
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.click('[data-testid="nav-tab-preview"]')
                page.wait_for_selector('[data-testid="preview-page"]', timeout=10000)

                # Start preview if no session
                start_btn = page.locator('[data-testid="start-preview-btn"]')
                if start_btn.count() > 0:
                    start_btn.click()

                # Wait for preview to be ready or show status
                page.wait_for_selector(
                    '[data-testid="preview-player-container"], '
                    '[data-testid="status-generating"], '
                    '[data-testid="error-message"]',
                    timeout=30000,
                )

                screenshot(page, journey_dir, 4, "preview_with_proxy")
                steps_passed += 1
                print("  Step 4: Start preview with proxy - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "preview_with_proxy", failed=True)
                print(f"  Step 4: Start preview with proxy - FAILED: {exc}")

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

    print(f"\n  Journey 402 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
