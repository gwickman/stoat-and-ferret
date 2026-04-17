# UAT Report

**Timestamp:** 2026-04-15 15:41:36 UTC
**Mode:** headed
**Duration:** 0.3s
**Result:** 0 passed, 6 failed, 7 skipped

## Journey Summary

| Journey | Status | Steps |
|---------|--------|-------|
| scan-library | FAIL | — |
| project-clip | SKIP | — |
| effects-timeline | SKIP | — |
| export-render | FAIL | — |
| preview-playback | FAIL | — |
| preview-playback-full | SKIP | — |
| proxy-management | SKIP | — |
| theater-mode | FAIL | — |
| timeline-sync | FAIL | — |
| render-export-journey | FAIL | — |
| render-queue-journey | SKIP | — |
| render-settings-journey | SKIP | — |
| render-failure-journey | SKIP | — |

## Failed Journeys

### scan-library

- Exit code 1: in <module>
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'playwright'


### export-render

- Exit code 1: in <module>
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'playwright'


### preview-playback

- Exit code 1: in <module>
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'playwright'


### theater-mode

- Exit code 1: in <module>
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'playwright'


### timeline-sync

- Exit code 1: in <module>
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'playwright'


### render-export-journey

- Exit code 1: in <module>
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'playwright'


