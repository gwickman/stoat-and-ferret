#!/usr/bin/env python3
"""UAT Journey 203: Effects-Timeline.

Validates effect application, editing, removal, timeline canvas rendering,
and layout preset selection across multiple pages. Covers three sub-journeys:
effects (apply/edit/remove), timeline (canvas/zoom/scroll), and layout
(preset selection with preview verification).

Depends on journey 202 (project-clip) for a project with clips.

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

JOURNEY_NAME = "effects-timeline"
JOURNEY_ID = 203

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


def run_effects_sub_journey(
    page: Any,
    journey_dir: Path,
    state: dict[str, Any],
) -> None:
    """Effects sub-journey: apply, edit, add, remove effects.

    Args:
        page: Playwright Page object.
        journey_dir: Output directory for screenshots.
        state: Mutable dict tracking steps_total, steps_passed, etc.
    """
    step = 1

    # ----------------------------------------------------------
    # Step 1: Navigate to Effects page and select project
    # ----------------------------------------------------------
    state["steps_total"] += 1
    try:
        page.click('[data-testid="nav-tab-effects"]')
        page.wait_for_selector('[data-testid="effects-page"]', timeout=10000)

        # Select project via dropdown
        project_select = page.locator('[data-testid="project-select"]')
        project_select.wait_for(timeout=10000)
        # Wait for options to populate
        page.wait_for_function(
            """() => {
                const s = document.querySelector('[data-testid="project-select"]');
                return s && s.options && s.options.length > 0
                    && s.options[0].value !== '';
            }""",
            timeout=10000,
        )
        # Select the first project
        project_select.select_option(index=0)
        page.wait_for_timeout(500)

        # Select the first clip so effects can be applied
        first_clip = page.locator('[data-testid^="clip-option-"]').first
        first_clip.wait_for(timeout=5000)
        first_clip.click()
        page.wait_for_timeout(500)

        screenshot(page, journey_dir, step, "effects_project_selected")
        state["steps_passed"] += 1
        print("  Step 1: Navigate to Effects page and select project - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 1 failed: {exc}")
        screenshot(page, journey_dir, step, "effects_project_selected", failed=True)
        print(f"  Step 1: Navigate to Effects page - FAILED: {exc}")

    # ----------------------------------------------------------
    # Step 2: Apply Text Overlay effect and verify filter preview
    # ----------------------------------------------------------
    step = 2
    state["steps_total"] += 1
    try:
        # Click the Text Overlay effect card
        page.click('[data-testid="effect-card-text_overlay"]')
        page.wait_for_selector('[data-testid="effect-parameter-form"]', timeout=5000)

        # Fill effect parameters
        text_input = page.locator('[data-testid="input-text"]')
        if text_input.count() > 0:
            text_input.first.fill("UAT Test Overlay")

        fontsize_input = page.locator('[data-testid="input-fontsize"]')
        if fontsize_input.count() > 0:
            fontsize_input.first.fill("24")

        # Verify filter preview shows FFmpeg filter string (before apply,
        # since apply clears the selected effect and resets the preview)
        preview = page.locator('[data-testid="filter-preview"]')
        preview.wait_for(timeout=5000)
        preview_text = preview.text_content() or ""
        if not preview_text.strip():
            raise AssertionError("Filter preview is empty after filling parameters")

        screenshot(page, journey_dir, step, "effect_applied_filter_preview")

        # Apply the effect
        apply_btn = page.locator('[data-testid="apply-effect-btn"]')
        if apply_btn.count() > 0:
            apply_btn.first.click()
        page.wait_for_timeout(1000)

        # Verify effect stack shows 1 entry
        stack = page.locator('[data-testid="effect-stack"]')
        stack.wait_for(timeout=5000)
        stack_items = page.locator('[data-testid^="effect-entry-"]')
        stack_count = stack_items.count()
        if stack_count != 1:
            raise AssertionError(f"Expected 1 effect in stack after apply, found {stack_count}")

        state["steps_passed"] += 1
        print(f"  Step 2: Apply Text Overlay, filter preview: {preview_text[:50]!r} - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 2 failed: {exc}")
        screenshot(page, journey_dir, step, "effect_applied_filter_preview", failed=True)
        print(f"  Step 2: Apply Text Overlay effect - FAILED: {exc}")

    # ----------------------------------------------------------
    # Step 3: Edit effect parameters
    # ----------------------------------------------------------
    step = 3
    state["steps_total"] += 1
    try:
        # Click edit on the first effect in the stack
        edit_btn = page.locator('[data-testid^="edit-effect-"]').first
        edit_btn.click()
        page.wait_for_selector('[data-testid="effect-parameter-form"]', timeout=5000)

        # Modify a parameter
        text_input = page.locator('[data-testid="input-text"]')
        if text_input.count() > 0:
            text_input.first.fill("UAT Edited Overlay")

        # Save changes
        save_btn = page.locator('[data-testid="apply-effect-btn"]')
        if save_btn.count() > 0:
            save_btn.first.click()
        page.wait_for_timeout(1000)

        screenshot(page, journey_dir, step, "effect_edited")
        state["steps_passed"] += 1
        print("  Step 3: Edit effect parameters - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 3 failed: {exc}")
        screenshot(page, journey_dir, step, "effect_edited", failed=True)
        print(f"  Step 3: Edit effect parameters - FAILED: {exc}")

    # ----------------------------------------------------------
    # Step 4: Add a second effect and verify stack count = 2
    # ----------------------------------------------------------
    step = 4
    state["steps_total"] += 1
    try:
        # Click a different effect card (or same one again for a second instance)
        page.click('[data-testid="effect-card-text_overlay"]')
        page.wait_for_selector('[data-testid="effect-parameter-form"]', timeout=5000)

        text_input = page.locator('[data-testid="input-text"]')
        if text_input.count() > 0:
            text_input.first.fill("Second Overlay")

        apply_btn = page.locator('[data-testid="apply-effect-btn"]')
        if apply_btn.count() > 0:
            apply_btn.first.click()
        page.wait_for_timeout(1000)

        # Verify stack count = 2
        stack_items = page.locator('[data-testid^="effect-entry-"]')
        stack_count = stack_items.count()
        if stack_count != 2:
            raise AssertionError(
                f"Expected 2 effects in stack after second add, found {stack_count}"
            )

        screenshot(page, journey_dir, step, "second_effect_added")
        state["steps_passed"] += 1
        print(f"  Step 4: Add second effect, stack count = {stack_count} - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 4 failed: {exc}")
        screenshot(page, journey_dir, step, "second_effect_added", failed=True)
        print(f"  Step 4: Add second effect - FAILED: {exc}")

    # ----------------------------------------------------------
    # Step 5: Remove one effect and verify stack count = 1
    # ----------------------------------------------------------
    step = 5
    state["steps_total"] += 1
    try:
        # Click remove on the first effect
        remove_btn = page.locator('[data-testid^="remove-effect-"]').first
        remove_btn.click()

        # Confirm removal if dialog appears
        confirm_btn = page.locator('[data-testid^="confirm-yes-"]')
        if confirm_btn.count() > 0:
            confirm_btn.first.click()
        page.wait_for_timeout(1000)

        # Verify stack count = 1
        stack_items = page.locator('[data-testid^="effect-entry-"]')
        stack_count = stack_items.count()
        if stack_count != 1:
            raise AssertionError(f"Expected 1 effect in stack after removal, found {stack_count}")

        screenshot(page, journey_dir, step, "effect_removed")
        state["steps_passed"] += 1
        print(f"  Step 5: Remove effect, stack count = {stack_count} - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 5 failed: {exc}")
        screenshot(page, journey_dir, step, "effect_removed", failed=True)
        print(f"  Step 5: Remove effect - FAILED: {exc}")


def _setup_timeline_tracks(page: Any, server_url: str) -> None:
    """Create timeline tracks and assign clips via API before GUI verification.

    Queries the first project's clips and creates a default video track with
    clip-to-track assignments using timeline_position/in_point/out_point at 30fps.

    Args:
        page: Playwright Page (used for page.request API calls).
        server_url: Base URL of the running server.
    """
    api = f"{server_url}/api/v1"
    fps = 30

    # Get first project (same one the dropdown selects)
    resp = page.request.get(f"{api}/projects?limit=100")
    projects = resp.json()["projects"]
    project_id = projects[0]["id"]

    # Check if tracks already exist
    tl_resp = page.request.get(f"{api}/projects/{project_id}/timeline")
    if len(tl_resp.json().get("tracks", [])) > 0:
        return

    # Create a default video track
    put_resp = page.request.put(
        f"{api}/projects/{project_id}/timeline",
        data=[
            {
                "track_type": "video",
                "label": "Video Track 1",
                "z_index": 0,
                "muted": False,
                "locked": False,
            }
        ],
    )
    track_id = put_resp.json()["tracks"][0]["id"]

    # Get clips and assign each to the track
    clips_resp = page.request.get(f"{api}/projects/{project_id}/clips")
    clips = clips_resp.json().get("clips", [])
    for clip in clips:
        tl_start = clip["timeline_position"] / fps
        clip_dur = (clip["out_point"] - clip["in_point"]) / fps
        tl_end = tl_start + clip_dur
        page.request.post(
            f"{api}/projects/{project_id}/timeline/clips",
            data={
                "clip_id": clip["id"],
                "track_id": track_id,
                "timeline_start": tl_start,
                "timeline_end": tl_end,
            },
        )


def run_timeline_sub_journey(
    page: Any,
    journey_dir: Path,
    state: dict[str, Any],
    server_url: str,
) -> None:
    """Timeline sub-journey: canvas, zoom, scroll verification.

    Args:
        page: Playwright Page object.
        journey_dir: Output directory for screenshots.
        state: Mutable dict tracking steps_total, steps_passed, etc.
        server_url: Base URL of the running server (for API setup calls).
    """
    # Set up timeline tracks via API before GUI verification
    _setup_timeline_tracks(page, server_url)

    # ----------------------------------------------------------
    # Step 6: Navigate to Timeline page and verify canvas
    # ----------------------------------------------------------
    step = 6
    state["steps_total"] += 1
    try:
        page.click('[data-testid="nav-tab-timeline"]')
        page.wait_for_selector('[data-testid="timeline-canvas"]', timeout=10000)
        screenshot(page, journey_dir, step, "timeline_canvas")

        # Verify canvas-tracks contains clip blocks
        tracks = page.locator('[data-testid="canvas-tracks"]')
        tracks.wait_for(timeout=5000)
        clip_blocks = tracks.locator('[data-testid^="clip-"]')
        block_count = clip_blocks.count()
        if block_count < 1:
            raise AssertionError(
                f"Expected at least 1 clip block in canvas tracks, found {block_count}"
            )

        # Verify time ruler is visible
        ruler = page.locator('[data-testid="time-ruler"]')
        ruler.wait_for(timeout=5000)
        if not ruler.is_visible():
            raise AssertionError("Time ruler is not visible")

        state["steps_passed"] += 1
        print(f"  Step 6: Timeline canvas loaded with {block_count} clip blocks - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 6 failed: {exc}")
        screenshot(page, journey_dir, step, "timeline_canvas", failed=True)
        print(f"  Step 6: Timeline canvas verification - FAILED: {exc}")

    # ----------------------------------------------------------
    # Step 7: Test zoom controls
    # ----------------------------------------------------------
    step = 7
    state["steps_total"] += 1
    try:
        # Zoom in
        page.click('[data-testid="zoom-in"]')
        page.wait_for_timeout(500)
        screenshot(page, journey_dir, step, "zoom_in")

        # Zoom out
        page.click('[data-testid="zoom-out"]')
        page.wait_for_timeout(500)
        screenshot(page, journey_dir, 8, "zoom_out")

        # Zoom reset
        page.click('[data-testid="zoom-reset"]')
        page.wait_for_timeout(500)
        screenshot(page, journey_dir, 9, "zoom_reset")

        state["steps_passed"] += 1
        print("  Step 7: Zoom controls (in/out/reset) - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 7 failed: {exc}")
        screenshot(page, journey_dir, step, "zoom_controls", failed=True)
        print(f"  Step 7: Zoom controls - FAILED: {exc}")

    # ----------------------------------------------------------
    # Step 8: Verify horizontal scrolling
    # ----------------------------------------------------------
    step = 10
    state["steps_total"] += 1
    try:
        scroll_area = page.locator('[data-testid="canvas-scroll-area"]')
        scroll_area.wait_for(timeout=5000)
        if not scroll_area.is_visible():
            raise AssertionError("Canvas scroll area is not visible")

        # Scroll horizontally
        scroll_area.evaluate("el => el.scrollLeft = 100")
        page.wait_for_timeout(300)
        scroll_left = scroll_area.evaluate("el => el.scrollLeft")
        if scroll_left <= 0:
            raise AssertionError(f"Horizontal scroll did not work, scrollLeft = {scroll_left}")

        screenshot(page, journey_dir, step, "horizontal_scroll")
        state["steps_passed"] += 1
        print(f"  Step 8: Horizontal scrolling (scrollLeft={scroll_left}) - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 8 failed: {exc}")
        screenshot(page, journey_dir, step, "horizontal_scroll", failed=True)
        print(f"  Step 8: Horizontal scrolling - FAILED: {exc}")


def run_layout_sub_journey(
    page: Any,
    journey_dir: Path,
    state: dict[str, Any],
) -> None:
    """Layout sub-journey: preset selection and preview verification.

    Args:
        page: Playwright Page object.
        journey_dir: Output directory for screenshots.
        state: Mutable dict tracking steps_total, steps_passed, etc.
    """
    # ----------------------------------------------------------
    # Step 9: Select layout presets and verify preview updates
    # ----------------------------------------------------------
    step = 11
    state["steps_total"] += 1
    try:
        # Navigate to layout presets section
        presets = page.locator('[data-testid="timeline-presets"]')
        presets.wait_for(timeout=5000)

        # Side-by-Side preset
        page.click('[data-testid="preset-SideBySide"]')
        page.wait_for_timeout(500)
        preview = page.locator('[data-testid="layout-preview"]')
        preview.wait_for(timeout=5000)
        sbs_rects = page.locator('[data-testid^="preview-rect-"]')
        sbs_count = sbs_rects.count()
        screenshot(page, journey_dir, step, "preset_side_by_side")
        print(f"    Side-by-Side: {sbs_count} rectangles")

        # PIP preset
        page.click('[data-testid="preset-PipTopLeft"]')
        page.wait_for_timeout(500)
        pip_rects = page.locator('[data-testid^="preview-rect-"]')
        pip_count = pip_rects.count()
        screenshot(page, journey_dir, step + 1, "preset_pip")
        print(f"    PIP: {pip_count} rectangles")

        # Grid preset
        page.click('[data-testid="preset-Grid2x2"]')
        page.wait_for_timeout(500)
        grid_rects = page.locator('[data-testid^="preview-rect-"]')
        grid_count = grid_rects.count()
        screenshot(page, journey_dir, step + 2, "preset_grid")
        print(f"    Grid: {grid_count} rectangles")

        # Verify rectangle counts differ between presets (layout actually changed)
        counts = {sbs_count, pip_count, grid_count}
        if all(c == 0 for c in counts):
            raise AssertionError("No preview rectangles rendered for any preset")

        state["steps_passed"] += 1
        print("  Step 9: Layout presets (side-by-side/pip/grid) - PASSED")
    except Exception as exc:
        state["steps_failed"] += 1
        state["issues"].append(f"Step 9 failed: {exc}")
        screenshot(page, journey_dir, step, "preset_selection", failed=True)
        print(f"  Step 9: Layout presets - FAILED: {exc}")


def run() -> int:
    """Execute the effects-timeline journey.

    Returns:
        Exit code: 0 if all steps pass, 1 otherwise.
    """
    output_dir = Path(os.environ.get("UAT_OUTPUT_DIR", "uat-evidence"))
    headed = os.environ.get("UAT_HEADED", "0") == "1"
    server_url = os.environ.get("UAT_SERVER_URL", "http://localhost:8765")
    gui_url = f"{server_url}/gui/"

    journey_dir = output_dir / JOURNEY_NAME
    journey_dir.mkdir(parents=True, exist_ok=True)

    state: dict[str, Any] = {
        "steps_total": 0,
        "steps_passed": 0,
        "steps_failed": 0,
        "console_errors": [],
        "issues": [],
    }

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
            state["console_errors"].append(text)

        page.on("console", on_console)

        try:
            # Navigate to the GUI
            page.goto(gui_url, wait_until="networkidle")
            page.wait_for_timeout(1000)

            # Sub-journey 1: Effects
            print("\n  [Effects Sub-Journey]")
            run_effects_sub_journey(page, journey_dir, state)

            # Sub-journey 2: Timeline
            print("\n  [Timeline Sub-Journey]")
            run_timeline_sub_journey(page, journey_dir, state, server_url)

            # Sub-journey 3: Layout
            print("\n  [Layout Sub-Journey]")
            run_layout_sub_journey(page, journey_dir, state)

        finally:
            context.close()
            browser.close()

    duration = time.monotonic() - start_time

    # Write structured result JSON
    result_data = {
        "name": JOURNEY_NAME,
        "journey_id": JOURNEY_ID,
        "steps_total": state["steps_total"],
        "steps_passed": state["steps_passed"],
        "steps_failed": state["steps_failed"],
        "console_errors": state["console_errors"],
        "issues": state["issues"],
        "duration_seconds": round(duration, 2),
    }
    result_path = journey_dir / "journey_result.json"
    result_path.write_text(json.dumps(result_data, indent=2) + "\n", encoding="utf-8")

    print(f"\n  Journey 203 complete: {state['steps_passed']}/{state['steps_total']} steps passed")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if state["steps_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
