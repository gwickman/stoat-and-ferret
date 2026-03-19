# UAT Report

**Timestamp:** 2026-03-19 13:16:29 UTC
**Mode:** headed
**Duration:** 231.1s
**Result:** 0 passed, 2 failed, 2 skipped

## Journey Summary

| Journey | Status | Steps |
|---------|--------|-------|
| scan-library | FAIL | 3/5 |
| project-clip | SKIP | — |
| effects-timeline | SKIP | — |
| export-render | FAIL | — |

## Failed Journeys

### scan-library

- Step 3 failed: Page.wait_for_selector: Timeout 90000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"scan-complete\"]") to be visible

- Step 5 failed: Page.wait_for_selector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator("[data-testid=\"video-grid\"]") to be visible


### export-render

- Seed failed: Seed script failed (exit 1): b.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\grant\Documents\projects\stoat-and-ferret\.venv\Lib\site-packages\httpx\_transports\default.py", line 118, in map_httpcore_exceptions
    raise mapped_exc(message) from exc
httpx.ReadTimeout: timed out


