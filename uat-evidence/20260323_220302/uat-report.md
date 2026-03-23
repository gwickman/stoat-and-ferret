# UAT Report

**Timestamp:** 2026-03-23 22:04:12 UTC
**Mode:** headed
**Duration:** 44.5s
**Result:** 3 passed, 1 failed, 0 skipped

## Journey Summary

| Journey | Status | Steps |
|---------|--------|-------|
| scan-library | PASS | 5/5 |
| project-clip | PASS | 5/5 |
| effects-timeline | FAIL | 8/9 |
| export-render | PASS | 5/5 |

## Failed Journeys

### effects-timeline

- Step 2 failed: Locator.wait_for: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"filter-preview\"]") to be visible


