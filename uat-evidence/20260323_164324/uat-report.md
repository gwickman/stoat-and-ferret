# UAT Report

**Timestamp:** 2026-03-23 16:46:22 UTC
**Mode:** headed
**Duration:** 150.8s
**Result:** 2 passed, 2 failed, 0 skipped

## Journey Summary

| Journey | Status | Steps |
|---------|--------|-------|
| scan-library | PASS | 5/5 |
| project-clip | PASS | 5/5 |
| effects-timeline | FAIL | 2/9 |
| export-render | FAIL | 3/5 |

## Failed Journeys

### effects-timeline

- Step 1 failed: Locator.wait_for: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid^=\"clip-option-\"]").first to be visible

- Step 2 failed: Locator.wait_for: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"effect-stack\"]") to be visible

- Step 3 failed: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-testid^=\"edit-effect-\"]").first

- Step 4 failed: Expected 2 effects in stack after second add, found 0
- Step 5 failed: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-testid^=\"remove-effect-\"]").first

- Step 6 failed: Expected at least 1 clip block in canvas tracks, found 0
- Step 9 failed: Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"preset-side-by-side\"]")


### export-render

- Step 4 failed: Page.wait_for_selector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"timeline-canvas\"]") to be visible

- Step 5 failed: Page.wait_for_selector: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"timeline-canvas\"]") to be visible


