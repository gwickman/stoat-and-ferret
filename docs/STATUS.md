# STATUS.md

## v077 — Release 2 Wave 2: Mastering + Voice Prep

**Delivered:** 2026-06-09
**PRs:** #535–#548 (14 PRs)
**Tests:** 2847 passing, 26 skipped

### Highlights

- 9 new audio DSP effects: noise_reduction, deesser, deplosive, time_stretch (voice repair); mastering_limiter, loudness_normalize, parametric_eq, multiband_compressor, volume automation (mastering)
- Rust/PyO3 builders in voice_repair.rs and mastering.rs; anequalizer, acompressor, alimiter, loudnorm, afftdn, atempo filter chains
- 4-track amix mixdown verification; golden QC regression suite (--update-golden + drift detection)
- UC-MEDIA-MPS-001 acceptance harness (seed-to-master-to-QC, ≥14/17 OC assertions)
- R2 UAT journey dispatch wiring (journeys 701-706)
- Effect registry: 8 effects (v074) → 17 effects (v077)

### AC Status

- 17 ACs supported (verified without FFmpeg)
- 32 ACs deferred_post_merge (require STOAT_TEST_FFMPEG=1 or headed browser)
- All deferred ACs have discharge scripts in source-to-outcome-evidence.json

### Discharge Commands (summary)

| Effect group | Discharge |
|-------------|-----------|
| Voice repair effects | `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/test_voice_repair_ffmpeg.py -v` |
| Mastering effects | `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/test_mastering_ffmpeg.py -v` |
| Mixdown | `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/test_mixdown_ffmpeg.py -v` |
| Golden QC | `STOAT_TEST_FFMPEG=1 uv run pytest tests/qc/test_qc_regression.py -v` |
| Acceptance harness | `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/uc_media_mps_001_harness.py -v` |
| UAT journeys R2 | `STOAT_TEST_UAT=1 python scripts/uat_runner.py --journeys 701-706 --headed` |
