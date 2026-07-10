# Theme 04 Retrospective — Video Effects + Subtitle Editing Discharge (v103)

## Theme Summary

Theme 04 discharged deferred FFmpeg-gated ACs for chromatic aberration (BL-453) and subtitle contract tests (BL-519/520). Partial: BL-444/445/450 carry deferred ACs requiring headed UAT (GUI journeys J-Reverse-Split, J-Razor, J-Grade).

## Features

### BL-453-AC-3 — Chromatic Aberration FFmpeg Contract (PR #793)
Added ChromaticAberrationBuilder FFmpeg contract test confirming the filter chain produces valid video output. AC discharged.

### BL-519/BL-520 — Subtitle Contract Tests (PR #794)
Added FFmpeg contract tests for subtitle rendering edge cases. Both ACs discharged. A ruff fixup commit (f0bcef9a) was required post-merge to fix a trailing-whitespace violation introduced in the PR.

### BL-444-AC-4 — Reverse Clip GUI Preview (deferred)
AC-4 requires headed UAT journey J-Reverse-Split. Cannot be discharged in headless mode. Carried forward.

### BL-445-AC-4 — Razor/Split GUI (deferred)
AC-4 requires headed UAT journey J-Editing. During investigation, `test_uc_cap_split_scenario` was found to regress: AssetRepoDep on `POST /clips` requires `app.state.db` that minimal `create_app()` doesn't supply. Tracked as a test infrastructure defect, candidate for v104.

### BL-450-AC-4 — Color LUT GUI UAT (deferred)
AC-4 requires headed UAT journey J-Grade. Carried forward pending display availability.

## Status

BL-453: discharged. BL-519/520: discharged. BL-444-AC-4 / BL-445-AC-4 / BL-450-AC-4: deferred (headed UAT gated). test_uc_cap_split_scenario regression: candidate for v104.
