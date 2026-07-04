# Smoke Test Harness Guide

## Overview

The smoke test suite (`tests/smoke/`) verifies end-to-end behavior across the render, preview, WebSocket event, and library-management subsystems. It is designed to be run by operators after deployment or during release verification — not in CI (which lacks a real FFmpeg environment).

Tests are split into two tiers:

- **FFmpeg-independent**: run in any environment; verify API contracts, WS events, and FK guards.
- **FFmpeg-dependent**: require a working `ffmpeg` binary on PATH; verify actual encode/decode behavior.

Run the FFmpeg-independent tier routinely. Run the full suite (both tiers) when verifying a release or discharging a deferred AC.

## Environment Setup

### STOAT_TEST_FFMPEG

Set `STOAT_TEST_FFMPEG=1` to enable FFmpeg-dependent tests. Without it, those tests are automatically skipped via pytest markers. Requires a working `ffmpeg` binary discoverable on `PATH`.

```bash
# Verify ffmpeg is available
ffmpeg -version
```

### Running the suite

```bash
# FFmpeg-independent tests only (safe in any environment)
uv run pytest tests/smoke/ -v

# Full suite including FFmpeg-dependent tests
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -v

# Single test by keyword
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -k <keyword> -v
```

## Windows-Specific Invocation

On Windows sandbox environments, the standard smoke command may fail for two reasons:

1. **UV cache access denied.** `uv run` attempts to write to the UV cache, which may be blocked in restricted environments. Set `UV_NO_CACHE=1` to bypass cache writes entirely.
2. **Coverage gate rejection.** Running only `tests/smoke/` collects less than the global 80% coverage threshold. Use `--no-cov` to suppress coverage for smoke-only runs.

Combined command for Windows:

```bash
UV_NO_CACHE=1 uv run pytest tests/smoke/ -v --timeout=120 --no-cov
```

If `%TEMP%` is also restricted, add `PYTEST_TMPDIR=<writable-path>` to redirect pytest's temp directory.

## Test Categories

| Category | FFmpeg required | Description |
|---|---|---|
| WS event assertions | No | Verifies `video_deleted`, `clip_deleted`, and render WS events |
| Output path isolation | Yes | Concurrent renders produce distinct, non-overlapping output paths |
| Render completion | Yes | `render_completed` payload contains expected fields |
| FK guard | No | FK enforcement on referenced-resource DELETE returns 409/422 |
| Preview smoke | No (mock) | Preview workflow completes; Python 3.13 asyncio behavior verified separately (see BL-393 below) |
| Cancel partial file | Yes | Mid-encode cancel sets `partial_file_detected=True` on the job |

## Recent Test Additions

| Version | Tests added |
|---------|-------------|
| v073 | `test_preview_smoke.py` — preview workflow smoke coverage |
| v074 | `test_render_contract.py`: settings-absent 422 gate (BL-465); `test_clip_workflow.py`: GET /clips/{cid} and GET /clips/{cid}/effects (BL-409, BL-405); `test_versions.py`: body-less POST auto-snapshot (BL-404); `test_uat_runner.py`: timeout regression guard (BL-398) |
| v079 | `tests/test_api/test_tone_synthesis.py` (BL-441): ToneSynthBuilder; `tests/test_api/test_loopable_beds.py` (BL-440): `build_loop_render_command` crossfade/seek; `tests/test_api/test_pitch_shift.py` (BL-443): `PitchShiftBuilder` formant/quality; `tests/test_api/test_sub_bass_ducking.py` (BL-442): `SubBassBuilder` + `ducking_effect_schema`; `tests/smoke/test_generator_clip.py` (BL-441 AC-4): generator clip API; `tests/smoke/test_qc_oracle.py` (BL-488): QC oracle delivery-profile assertions (FFmpeg-gated) |
| v081 | `tests/smoke/test_effects.py`: 10 new video FX smoke tests — 8 clip-applicable effects (`test_v081_video_fx_effect`) and 2 generator effects (`test_v081_generator_fx_catalog_and_preview`) (BL-450, BL-452, BL-453, BL-454, BL-455) |
| v084 | `tests/smoke/test_source_api.py` updated — asserts `GET /api/v1/source` returns the `SourceResponse` typed Pydantic model with four named string fields (`source_url`, `version`, `commit`, `license`) as non-null strings (BL-539) |
| v090 | `tests/smoke/test_asset_api.py` (BL-515 AC-13 to AC-16): asset lifecycle round-trip, content-hash dedup, soft-delete, oversize/MIME-mismatch security rejections. FFmpeg-independent — no `STOAT_TEST_FFMPEG` required. Referenced-clip delete-protection test (`test_asset_delete_protection_with_clip`) auto-skips until BL-511 (clip_type=image) is merged. |
| v095–v096 | `tests/smoke/test_subtitle_injection.py` — five HTTP-layer smoke tests: three added in v095 verifying BL-595/BL-596 colon/apostrophe option-level rejection via `source_path` and `font_color`, plus valid-input acceptance; two added in v096 verifying BL-599 comma/semicolon filtergraph metacharacter rejection in `font_color` (`test_subtitle_font_color_with_comma_returns_422`, `test_subtitle_font_color_with_semicolon_returns_422`). FFmpeg-independent — no `STOAT_TEST_FFMPEG` required. Reference this file for regression verification of subtitle filter-option and filtergraph-level injection fixes. |

See [docs/setup/smoke-test-harness-guide/smoke-test-key-files.md](../setup/smoke-test-harness-guide/smoke-test-key-files.md) for the full per-file inventory.

## Wave-3 Effect Contract Tests (v079)

Wave-3 adds audio DSP builders — tone synthesis, loopable beds, pitch/formant control, sub-bass isolation, and sidechain ducking. Most unit tests are FFmpeg-independent; FFmpeg-gated tests require a real `ffmpeg` binary on PATH.

### FFmpeg-independent (run in any environment)

```bash
uv run pytest tests/test_api/test_tone_synthesis.py \
              tests/test_api/test_loopable_beds.py \
              tests/test_api/test_pitch_shift.py \
              tests/test_api/test_sub_bass_ducking.py \
              tests/smoke/test_generator_clip.py \
              -x -q
```

### FFmpeg-gated (requires `STOAT_TEST_FFMPEG=1`)

```bash
STOAT_TEST_FFMPEG=1 uv run pytest \
  tests/test_api/test_tone_synthesis.py \
  tests/test_api/test_loopable_beds.py \
  tests/test_api/test_pitch_shift.py \
  -x -q
```

| Builder | Test file | FFmpeg required |
|---------|-----------|-----------------|
| `ToneSynthBuilder` | `tests/test_api/test_tone_synthesis.py` | FFmpeg-gated tests only |
| `build_loop_render_command` | `tests/test_api/test_loopable_beds.py` | FFmpeg-gated tests only |
| `PitchShiftBuilder` | `tests/test_api/test_pitch_shift.py` | FFmpeg-gated tests only |
| `SubBassBuilder` / `ducking_effect_schema` | `tests/test_api/test_sub_bass_ducking.py` | No |
| Generator clip API | `tests/smoke/test_generator_clip.py` | No |

## v081 Video FX Smoke Tests (BL-450, BL-452, BL-453, BL-454, BL-455)

v081 added 10 new video FX effect types to the registry. Their smoke coverage lives in `tests/smoke/test_effects.py` and uses two patterns:

### Clip-application pattern (8 effects)

`test_v081_video_fx_effect` is a parametrized test that:
1. Verifies the effect is present in `GET /effects` catalog
2. Creates a project + clip via `_setup_project_with_clip`
3. POSTs the effect to the clip and asserts `201` + expected FFmpeg filter keyword in `filter_string`
4. GETs the clip list and confirms the effect appears

| Effect type | Parameters | Expected FFmpeg filter |
|-------------|-----------|------------------------|
| `blur` | `{"sigma": 2.0}` | `gblur` |
| `sharpen` | `{"amount": 1.0}` | `unsharp` |
| `opacity` | `{"opacity": 0.5}` | `colorchannelmixer` |
| `scale` | `{"scale": 1.5}` | `scale` |
| `color_lut` | `{"preset": "warm_fade"}` | `lut3d` |
| `chroma_key` | `{"color": "green", "similarity": 0.1}` | `chromakey` |
| `color_key` | `{"color": "white", "similarity": 0.1}` | `colorkey` |
| `lens_distort` | `{"k1": 0.1, "k2": 0.05}` | `lenscorrection` |
| `chromatic_aberration` | `{"rx": 5, "ry": 0, "gx": 0, "gy": 0, "bx": -5, "by": 0}` | `rgbashift` |

### Preview pattern (2 generator effects)

`test_v081_generator_fx_catalog_and_preview` is a parametrized test that:
1. Verifies the effect is in the catalog
2. POSTs to `POST /effects/preview` and asserts `200` + expected filter keyword

Generator effects produce synthetic video output and cannot be applied to a clip directly; they are validated via the preview endpoint.

| Effect type | Parameters | Expected FFmpeg filter | Notes |
|-------------|-----------|------------------------|-------|
| `gradient_generator` | `{"color1": "black", "color2": "white", "duration": 5.0}` | `gradients` | |
| `noise_generator` | `{"duration": 5.0}` | `cellauto` | v082 BL-501 (PR #610): `d=` duration option removed from filter string; duration now controlled via `-t` at command level |

### Running v081 FX tests

These tests are FFmpeg-independent — no `STOAT_TEST_FFMPEG=1` required:

```bash
# Run all v081 video FX smoke tests
uv run pytest tests/smoke/test_effects.py -k "v081" -v

# Run specific effect
uv run pytest tests/smoke/test_effects.py -k "v081_video_fx_effect[blur]" -v
```

---

## QC Oracle Smoke Test (BL-488)

`tests/smoke/test_qc_oracle.py` verifies that a render job submitted with a delivery profile propagates loudness and true-peak targets to the QC report. It requires a running server with a delivery profile fixture and a real FFmpeg encode.

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/test_qc_oracle.py -x -q
```

**Pass criteria:** `GET /api/v1/render/{job_id}/qc` returns `checks.loudness_integrated.target == -16.0` and `checks.true_peak.target == -1.0`.

---

## Deferred AC Discharge Procedures

These ACs are classified `deferred_post_merge` in v072 (DECISION-003 from `docs/design/` risk assessment). They cannot be verified in CI due to environment constraints. Run these procedures in a suitable environment before marking v072 fully verified.

**Two distinct deferral reasons:**

- **Python-version-dependent (BL-393-AC-1, BL-393-AC-2):** Deferred because Python 3.13 asyncio semantics are environment-specific. These do not require real FFmpeg — they require running under Python 3.13.
- **FFmpeg-environment-dependent (BL-415-AC-3, BL-403-AC-3):** Deferred because real FFmpeg is needed to observe actual encode/cancel/concurrency behavior. These require `STOAT_TEST_FFMPEG=1`.

---

### BL-393-AC-1: Python 3.13 asyncio race in async_executor does not occur under real FFmpeg load

**AC text:** Under Python 3.13, a preview render that exercises `async_executor.py` completes without deadlock or stall.

**Deferral reason:** Python-version-dependent. Python 3.13 changed asyncio task scheduling; the race is not reproducible under Python 3.10–3.12.

**Discharge command:**

```bash
uv run pytest tests/smoke/ -k preview_no_deadlock -v
```

**Pass criteria:** Test exits within 30 seconds; no asyncio warnings or `TimeoutError` in stderr.

---

### BL-393-AC-2: Preview smoke test on Python 3.13 completes without asyncio warning

**AC text:** `pytest tests/smoke/` under Python 3.13 emits no `asyncio` `DeprecationWarning` or `RuntimeWarning`.

**Deferral reason:** Python-version-dependent. Warnings are only raised by Python 3.13's stricter asyncio runtime; not observable under earlier versions.

**Discharge command:**

```bash
uv run pytest tests/smoke/ -W error::DeprecationWarning -W error::RuntimeWarning -v
```

**Pass criteria:** Zero warnings from the `asyncio` module. Test suite exits with code 0.

---

### BL-415-AC-3: Partial file detected after mid-encode cancel

**AC text:** Cancelling a render mid-encode sets `partial_file_detected=True` on the job record.

**Deferral reason:** FFmpeg-environment-dependent. Requires a real FFmpeg encode in progress at the moment of cancel; cannot be simulated with a mock.

**Discharge command:**

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -k partial_file_cancel -v
```

**Pass criteria:** `GET /api/v1/jobs/{id}` returns `"partial_file_detected": true` after a cancel is issued during an active encode. Job status must be `cancelled` or `failed`.

---

### BL-403-AC-3: Concurrent renders produce distinct output files

**AC text:** After two concurrent real-mode renders of the same project complete, each job carries a distinct `output_path` value and the file exists on disk.

**Deferral reason:** FFmpeg-environment-dependent. Requires two real concurrent renders to complete successfully; cannot be verified without real FFmpeg.

**Discharge command:**

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -k test_concurrent_renders_have_distinct_output_paths -v
```

**Pass criteria:** Both renders complete with distinct `output_path` values; test passes.
