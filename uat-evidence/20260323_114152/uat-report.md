# UAT Report

**Timestamp:** 2026-03-23 11:45:36 UTC
**Mode:** headed
**Duration:** 191.0s
**Result:** 2 passed, 2 failed, 0 skipped

## Journey Summary

| Journey | Status | Steps |
|---------|--------|-------|
| scan-library | PASS | 5/5 |
| project-clip | PASS | 5/5 |
| effects-timeline | FAIL | 1/9 |
| export-render | FAIL | 3/5 |

## Failed Journeys

### effects-timeline

- Step 2 failed: Locator.wait_for: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"filter-preview\"]") to be visible

- Step 3 failed: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-testid^=\"edit-effect-\"]").first

- Step 4 failed: Expected 2 effects in stack after second add, found 0
- Step 5 failed: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-testid^=\"remove-effect-\"]").first

- Step 6 failed: Page.wait_for_selector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"timeline-canvas\"]") to be visible

- Step 7 failed: Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"zoom-in\"]")

- Step 8 failed: Locator.wait_for: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"canvas-scroll-area\"]") to be visible

- Step 9 failed: Page.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"preset-side-by-side\"]")


**Console errors:**
- `Failed to load resource: the server responded with a status of 400 (Bad Request)`

### export-render

- Step 4 failed: Page.wait_for_selector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"timeline-canvas\"]") to be visible

- Step 5 failed: Page.wait_for_selector: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"timeline-canvas\"]") to be visible


