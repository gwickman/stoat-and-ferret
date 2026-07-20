## Naming Convention

All `STOAT_TEST_FFMPEG=1`-gated test functions in `tests/test_effects_*.py` must use the
`_ffmpeg_contract` suffix. Examples:

```
test_color_lut_ffmpeg_contract
test_blur_gaussian_ffmpeg_contract
test_lens_distort_ffmpeg_contract
```

A conformance assertion in `tests/test_hygiene.py::test_ffmpeg_contract_test_naming_convention`
enforces this at CI time — any non-conforming test name causes a CI failure.

## Definition-of-Done Policy

Every new effect builder **MUST ship with at least one `STOAT_TEST_FFMPEG=1`-gated contract
test in the same PR as the builder registration**, before the builder is registered.
A builder merged without a gated contract test is a DoD violation. The gated-coverage guard
test in `tests/test_contract/test_effect_gated_coverage.py` enforces this structurally;
the `STOAT_TEST_FFMPEG=1` CI lane (BL-607) enforces it behaviorally.

See also: `AGENTS.md` §Smoke Test Harness for the full DoD expectation.

## DSP Contract Tests (FFmpeg-Gated)

v077 adds FFmpeg-gated contract tests in `tests/effects/` that verify the DSP effect pipeline end-to-end using a real FFmpeg binary. These tests are separate from the standard API smoke suite because they require FFmpeg to be installed on the host.

### Why separate from the standard smoke suite

The API smoke tests (`tests/test_api/`) validate API contracts and schema correctness without executing FFmpeg. The DSP contract tests in `tests/effects/` go one level deeper: they exercise the actual FFmpeg filter graphs for mastering and voice-repair effects, verifying that the filter strings produce correct audio output. Because they require a real FFmpeg binary, they are gated with the `STOAT_TEST_FFMPEG=1` environment variable and skipped in standard CI runs.

### Run DSP contract tests

```bash
# Run all DSP contract tests (requires FFmpeg)
STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v

# Run mastering effects only
STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/test_mastering_ffmpeg.py -v

# Run voice repair effects only
STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/test_voice_repair_ffmpeg.py -v

# Run without FFmpeg (all gated tests skip)
uv run pytest tests/effects/ -v
```

### v077 DSP effect coverage

All 9 v077 effect types have FFmpeg-gated contract tests:

| Effect | Type string | Test file |
|--------|-------------|-----------|
| Mastering limiter | `limiter` | `tests/effects/test_mastering_ffmpeg.py` |
| LUFS loudness normalize | `loudness_normalize` | `tests/effects/test_mastering_ffmpeg.py` |
| Volume automation | `volume` | `tests/effects/test_mastering_ffmpeg.py` |
| Parametric EQ | `parametric_eq` | `tests/effects/test_mastering_ffmpeg.py` |
| Multiband compressor | `multiband_compressor` | `tests/effects/test_mastering_ffmpeg.py` |
| Noise reduction | `noise_reduction` | `tests/effects/test_voice_repair_ffmpeg.py` |
| De-esser | `deesser` | `tests/effects/test_voice_repair_ffmpeg.py` |
| De-plosive | `deplosive` | `tests/effects/test_voice_repair_ffmpeg.py` |
| Time-stretch | `time_stretch` | `tests/effects/test_voice_repair_ffmpeg.py` |

### v078: eval=frame requirement for volume automation

v078 (PR #553, BL-479) changed the volume effect filter to include `eval=frame` so that keyframe automation envelopes are evaluated per-frame rather than at filter init. The FFmpeg-gated contract test in `test_mastering_ffmpeg.py` covers this effect; any future update to volume filter generation that removes `eval=frame` will break keyframe-driven automation. See also `tests/smoke/test_effects.py::test_preview_accepts_automation_envelope` (BL-482) for the API-level smoke regression.

### EXPECTED_EFFECT_TYPES completeness check

`tests/test_api/test_effects.py` contains a constant `EXPECTED_EFFECT_TYPES` — the authoritative set of registered effect type strings. This set must include every effect type registered in the Rust core. When a new effect type is added, the corresponding type string must be added to `EXPECTED_EFFECT_TYPES`; failure to do so causes the effects catalog test to raise a missing-registration error.

All 9 v077 DSP effect types listed above are included in `EXPECTED_EFFECT_TYPES` as of PR #544.

### v080 Effect Types

The following effect types were added in v080 and require `STOAT_TEST_FFMPEG=1` for smoke discharge:

| Effect Type | Smoke Test | FFmpeg Required |
|---|---|---|
| `reverse` | `tests/smoke/test_effects.py::test_smoke_reverse_effect` | Yes |
| `variable_speed` | `tests/smoke/test_effects.py::test_smoke_variable_speed_effect` | Yes |
| `framerate_convert` | `tests/smoke/test_effects.py::test_smoke_framerate_convert_effect` | Yes |
| `freeze_frame` | `tests/smoke/test_effects.py::test_smoke_freeze_frame_effect` | Yes |

Discharge command:
```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/test_effects.py -k "smoke_reverse or smoke_variable_speed or smoke_framerate_convert or smoke_freeze_frame" -v
```

### Split Endpoint (v080)

The split endpoint smoke test does NOT require FFmpeg — it is pure database arithmetic:

```bash
uv run pytest tests/smoke/test_clip_workflow.py::test_smoke_split_clip -v
```

### STOAT_REVERSE_MAX_DURATION_S Discharge

Buffer-limit rejection tests for the `reverse` effect use this env var (default: `30.0` s).
To test with a lower limit:

```bash
STOAT_REVERSE_MAX_DURATION_S=5.0 STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/test_effects.py::test_smoke_reverse_effect -v
```

### v089 Wave 3a Effect Types

v089 (Wave 3a) adds 4 new effect types, expanding `EXPECTED_EFFECT_TYPES` from 34 to 38 entries. The smoke tests for these types live in `tests/smoke/test_effects.py`.

| Effect Type | Smoke Tests | timeline_T_capable | FFmpeg Required |
|---|---|---|---|
| `zoompan` | `test_zoompan_in_effect_catalog`, `test_zoompan_preview_generation` | False | Yes (preview generation) |
| `curves` | `test_curves_in_effect_catalog`, `test_curves_preview_generation` | True | Yes (preview generation) |
| `vignette` | `test_vignette_in_effect_catalog`, `test_vignette_preview_generation` | True | Yes (preview generation) |
| `hue_rotation` | `test_hue_rotation_in_effect_catalog`, `test_hue_rotation_preview_generation` | True | Yes (preview generation) |

The catalog tests (`test_*_in_effect_catalog`) do not require FFmpeg — they validate API catalog registration only. The preview generation tests (`test_*_preview_generation`) exercise the full filter-string generation path and require a real video file in `videos/demo/`.

#### timeline_T_capable=True Behavior

`timeline_T_capable=True` on an `EffectDefinition` means the effect builder supports FFmpeg's `enable=` timeline windowing when a `WindowSpec` is provided on the effect. When windowed, these effects emit an `enable='between(t,<start>,<end>)'` expression that activates the effect only within the specified time window — without splitting the clip.

Three Wave 3a builders have `timeline_T_capable=True`: **curves**, **vignette**, and **hue_rotation**.

`zoompan` is `timeline_T_capable=False`. Windowed zoompan application routes through the split/trim/concat fallback (BL-512, shipped in v110 F009).

#### Wave 3a smoke discharge command

```bash
uv run pytest tests/smoke/test_effects.py -k "zoompan or curves or vignette or hue_rotation" -v --no-cov
```

The catalog tests run without FFmpeg. The preview generation tests require `videos/demo/` to be present — they will fail (not skip) if the directory is missing.

### Windowed Non-T Effect Fallback (BL-512)

Filters that do not support the FFmpeg `enable=` T flag (e.g., `zoompan`, `scale`, `subtitles`)
cannot use `enable='between(t,start,end)'` for time-window gating. Instead, the stoat_ferret_core
translator routes them through a **split/trim/concat fallback**:

1. Split the clip at `window_start` and `window_end` using `trim` filters.
2. Apply the effect to the middle segment.
3. Concatenate the three segments with `concat=n=3:v=1:a=0`.
4. Each segment junction adds `format=yuv420p` to ensure pixel format consistency.

The non-T condition is: `defn.timeline_T_capable=False` AND a `WindowSpec` is present on the
effect. Effects with `timeline_T_capable=True` continue to use `enable='between(t,...)'`
without splitting the clip.

**Smoke tests** (added in v110, BL-512):

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/test_smoke_windowed_non_t.py -v
```

Tests confirm:
- The effect is visibly present inside the window and absent outside it (frame comparison).
- Output `pix_fmt` is `yuv420p` (ffprobe assertion).
