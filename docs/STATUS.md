# STATUS.md

## v078 — QC Integrity, DSP Correctness & R2 Doc Parity

**Delivered:** 2026-06-11
**PRs:** #550–#562 (13 PRs)
**Tests:** 2852+ passing (smoke tests added in Theme 04)

### Highlights

- QC loudness measurement corrected: ebur128 replaced by loudnorm print_format=json — BL-476
- QCService wired into worker-path renders via RenderService._complete_job() — BL-477
- Deesser frequency normalized Hz→[0,1]; multiband compressor threshold normalized dB→linear — BL-478
- Volume automation eval=frame; effects-preview-automation endpoint wired; preview validation fixed — BL-479/BL-482
- automatable_parameters field added to EffectResponse — BL-481
- librosa added to test extras; pitch stability test unconditionally enabled — BL-435 rider
- Smoke tests for automatable_parameters, worker-path QC, and preview automation — Theme 04
- R2 doc parity: C4 routers updated (9→17 effects, 14 locations), 8 new DSP effects documented — BL-469/BL-483
- QC endpoints documented in api-reference and operator-guide — BL-484
- delivery_profiles CRUD documented; name-vs-UUID distinction explicit — BL-485
- QC-fail GUI surfaces on RenderJobCard; uat_runner and screenshot path fixes — BL-480

### Theme Summary

| Theme | BL Items | PRs | Status |
|-------|----------|-----|--------|
| qc-integrity | BL-476, BL-477 | #550, #551 | merged |
| dsp-correctness | BL-478, BL-479, BL-435 rider | #552, #553, #554 | merged |
| automation-api-ergonomics | BL-481, BL-482 | #553, #555 | merged |
| qa-infrastructure | smoke tests, harness guide | #556, #557 | merged |
| r2-doc-parity | BL-469, BL-483, BL-484, BL-485, BL-480 | #558–#562 | merged |

### AC Status

- All 13 features merged to main
- 5 ACs deferred_post_merge (require `STOAT_TEST_FFMPEG=1` or headed browser)
- All deferred ACs have discharge commands below

### Discharge Commands

| Item | Description | Discharge |
|------|-------------|-----------|
| BL-476-AC-4 | Golden QC fixture | `STOAT_TEST_FFMPEG=1 uv run pytest tests/qc/ -v` |
| BL-477-AC-3 | Worker-path QC acceptance | `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/ -v` |
| BL-478-AC-1/2 | Deesser + multiband FFmpeg | `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` |
| BL-479-AC-1 | Volume automation FFmpeg | `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` |
| BL-480-AC-1 | J703/J704 UAT headed | `python scripts/uat_runner.py --journey 703` and `--journey 704` (headed Chromium, Windows) |

### User Actions Required

1. **BL-476-AC-4** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/qc/ -v` to discharge golden QC fixture against real FFmpeg output
2. **BL-477-AC-3** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/ -v` to discharge worker-path QC acceptance harness with real FFmpeg
3. **BL-478-AC-1/2** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` to discharge deesser (Hz→[0,1]) and multiband (dB→linear) normalization
4. **BL-479-AC-1** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` to discharge volume automation frame-eval correctness
5. **BL-480-AC-1** — Run `python scripts/uat_runner.py --journey 703` and `--journey 704` on Windows with headed Chromium (J703/J704 UAT pass)
