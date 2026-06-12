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
