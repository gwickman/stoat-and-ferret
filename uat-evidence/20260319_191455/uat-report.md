# UAT Report

**Timestamp:** 2026-03-19 19:16:21 UTC
**Mode:** headed
**Duration:** 61.3s
**Result:** 1 passed, 2 failed, 1 skipped

## Journey Summary

| Journey | Status | Steps |
|---------|--------|-------|
| scan-library | PASS | 5/5 |
| project-clip | FAIL | 3/5 |
| effects-timeline | SKIP | — |
| export-render | FAIL | 2/5 |

## Failed Journeys

### project-clip

- Step 4 failed: Page.wait_for_function: Timeout 10000ms exceeded.
- Step 5 failed: Page.wait_for_selector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"clips-table\"]") to be visible


**Console errors:**
- `Failed to load resource: the server responded with a status of 422 (Unprocessable Content)`

### export-render

- Step 3 failed: Locator.wait_for: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"effect-stack\"]") to be visible

- Step 4 failed: Page.wait_for_selector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"timeline-canvas\"]") to be visible

- Step 5 failed: Page.wait_for_selector: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"timeline-canvas\"]") to be visible


