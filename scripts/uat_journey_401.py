#!/usr/bin/env python3
"""UAT Journey 401: Preview Playback (Phase 4).

Validates the full preview playback workflow: start preview, wait for generation,
play video, seek to 50%, pause, and check the quality indicator.

Depends on journey 205 (preview page loads correctly).

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
JOURNEY_NAME = "preview-playback-full"
JOURNEY_ID = 401

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
    """Execute the preview-playback-full journey.

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
            # Step 1: Navigate to Preview page and start preview
            # ----------------------------------------------------------
            steps_total += 1
            try:
                page.goto(gui_url, wait_until="networkidle")
                page.wait_for_selector('[data-testid="nav-tab-preview"]', timeout=15000)
                page.click('[data-testid="nav-tab-preview"]')
                page.wait_for_selector('[data-testid="preview-page"]', timeout=10000)

                # Click Start Preview if the no-session state is shown
                start_btn = page.locator('[data-testid="start-preview-btn"]')
                if start_btn.count() > 0:
                    start_btn.click()

                screenshot(page, journey_dir, 1, "preview_started")
                steps_passed += 1
                print("  Step 1: Navigate and start preview - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 1 failed: {exc}")
                screenshot(page, journey_dir, 1, "preview_started", failed=True)
                print(f"  Step 1: Navigate and start preview - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 2: Wait for generation to complete
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Wait for either the player container (ready) or error
                # Generation may take a while — 60s timeout
                page.wait_for_selector(
                    '[data-testid="preview-player-container"], [data-testid="error-message"]',
                    timeout=60000,
                )

                has_player = page.locator('[data-testid="preview-player-container"]').count() > 0
                if not has_player:
                    raise AssertionError("Preview generation failed — error state shown")

                screenshot(page, journey_dir, 2, "generation_complete")
                steps_passed += 1
                print("  Step 2: Wait for generation complete - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 2 failed: {exc}")
                screenshot(page, journey_dir, 2, "generation_complete", failed=True)
                print(f"  Step 2: Wait for generation - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 3: Play video (verify canplay)
            # ----------------------------------------------------------
            steps_total += 1
            try:
                video = page.locator('[data-testid="preview-player-video"]')
                video.wait_for(timeout=10000)

                # Wait for the video to be ready for playback
                page.wait_for_function(
                    """() => {
                        const v = document.querySelector('[data-testid="preview-player-video"]');
                        return v && v.readyState >= 3;
                    }""",
                    timeout=30000,
                )

                # Click play
                play_btn = page.locator('[data-testid="play-pause-btn"]')
                play_btn.click()

                # Verify video is playing
                page.wait_for_function(
                    """() => {
                        const v = document.querySelector('[data-testid="preview-player-video"]');
                        return v && !v.paused;
                    }""",
                    timeout=10000,
                )

                screenshot(page, journey_dir, 3, "video_playing")
                steps_passed += 1
                print("  Step 3: Play video - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 3 failed: {exc}")
                screenshot(page, journey_dir, 3, "video_playing", failed=True)
                print(f"  Step 3: Play video - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 4: Seek to 50%
            # ----------------------------------------------------------
            steps_total += 1
            try:
                # Click at 50% of the progress bar track
                progress_track = page.locator('[data-testid="progress-bar-track"]')
                progress_track.wait_for(timeout=5000)
                box = progress_track.bounding_box()
                if box is None:
                    raise AssertionError("Could not get progress bar bounding box")

                # Click at the midpoint
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                page.wait_for_timeout(1000)

                # Verify the video currentTime changed to roughly 50%
                at_midpoint = page.evaluate(
                    """() => {
                        const v = document.querySelector('[data-testid="preview-player-video"]');
                        if (!v || !v.duration) return false;
                        const ratio = v.currentTime / v.duration;
                        return ratio > 0.3 && ratio < 0.7;
                    }"""
                )
                if not at_midpoint:
                    raise AssertionError("Video did not seek to approximately 50%")

                screenshot(page, journey_dir, 4, "seek_50_percent")
                steps_passed += 1
                print("  Step 4: Seek to 50% - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 4 failed: {exc}")
                screenshot(page, journey_dir, 4, "seek_50_percent", failed=True)
                print(f"  Step 4: Seek to 50% - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 5: Pause playback
            # ----------------------------------------------------------
            steps_total += 1
            try:
                play_btn = page.locator('[data-testid="play-pause-btn"]')
                play_btn.click()

                page.wait_for_function(
                    """() => {
                        const v = document.querySelector('[data-testid="preview-player-video"]');
                        return v && v.paused;
                    }""",
                    timeout=5000,
                )

                screenshot(page, journey_dir, 5, "video_paused")
                steps_passed += 1
                print("  Step 5: Pause playback - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 5 failed: {exc}")
                screenshot(page, journey_dir, 5, "video_paused", failed=True)
                print(f"  Step 5: Pause playback - FAILED: {exc}")

            # ----------------------------------------------------------
            # Step 6: Check quality indicator
            # ----------------------------------------------------------
            steps_total += 1
            try:
                quality = page.locator('[data-testid="quality-selector"]')
                quality.wait_for(timeout=5000)

                # Verify the quality select dropdown is present and has options
                quality_select = page.locator('[data-testid="quality-select"]')
                has_options = quality_select.count() > 0
                if not has_options:
                    raise AssertionError("Quality select dropdown not found")

                screenshot(page, journey_dir, 6, "quality_indicator")
                steps_passed += 1
                print("  Step 6: Quality indicator present - PASSED")
            except Exception as exc:
                steps_failed += 1
                issues.append(f"Step 6 failed: {exc}")
                screenshot(page, journey_dir, 6, "quality_indicator", failed=True)
                print(f"  Step 6: Quality indicator - FAILED: {exc}")

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

    print(f"\n  Journey 401 complete: {steps_passed}/{steps_total} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
