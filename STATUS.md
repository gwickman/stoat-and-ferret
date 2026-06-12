# Project Status — stoat-and-ferret

**Current version:** v079 (Release 2, Wave 3: Sound Design + v078 Repair Rider)
**Status:** Completed 2026-06-12

## v079 Summary

Release 2, Wave 3 delivers immersive sound-design capabilities (spatial audio, generator clips, tone synthesis, loopable beds, sub-bass and pitch-shift processing) and repairs four v078 correctness items (QC oracle worker path, JobStatus enum rename, render-plan schema alignment, UAT seed extension).

### Delivered

| Theme | Feature | Status | PR |
|-------|---------|--------|----|
| qc-and-agent-surface-repair | qc-worker-path-assertions | ✓ | #565 |
| qc-and-agent-surface-repair | job-status-enum-rename | ✓ | #566 |
| qc-and-agent-surface-repair | render-plan-schema-alignment | ✓ | #567, #568 |
| qc-and-agent-surface-repair | uat-seed-extension | ✓ | #569 |
| spatial-audio | stereo-pan-automation | ✓ | #570 |
| spatial-audio | convolution-reverb | ✓ | #571, #572 |
| sound-design | generator-clip-enabler | ✓ | #574, #575 |
| sound-design | tone-synthesis | ✓ | #576 |
| sound-design | loopable-beds | ✓ | #577 |
| voice-and-bass | sub-bass-layer | ✓ | #577 |
| voice-and-bass | pitch-shift-formant | ✓ | #577 |
| wave-t-coverage | smoke-test-updates | ✓ | #579 |
| wave-t-coverage | harness-guide-update | ✓ | #579 |

### Test Results

- **Test count:** 3010 passed, 52 skipped (2873 baseline → +137)
- **Regressions:** 0
- **FFmpeg-gated (deferred_post_merge):** BL-437 ACs 1-4, BL-438 ACs 1-3, BL-439 ACs 2+4, BL-441 AC-2, BL-488 ACs 3+5

### Key Capabilities Added

- **PanBuilder** (`ffmpeg/spatial.rs`) — stereo pan with static positioning and automation envelope; `eval=frame` enforced; `spatial_correlation` added as 12th QC check
- **ConvolutionReverbBuilder** (`ffmpeg/spatial.rs`) — IR-based reverb via `afir` filter; 3 bundled IRs (`hall_small`, `room_medium`, `plate`)
- **Generator clips** (`clip_type="generator"`) — `ClipCreate` schema validates generator vs. file type; `build_generator_source_filter` dispatch (`aevalsrc`, `sine`) in Rust; `ON DELETE CASCADE` restored on `clips.project_id` FK
- **Tone synthesis** (`generator_params["type"] = "tone"`) — constant frequency, linear chirp sweep (`frequency_end`), binaural beat (`binaural_offset`); all `aevalsrc` with mandatory `eval=frame`
- **Loopable beds** — `build_loop_render_command` for seamless crossfaded loops
- **SubBassBuilder** — sub-bass layer with duck-on-beat ducking schema
- **PitchShiftBuilder** (`ffmpeg/voice_repair.rs`) — formant-preserving pitch shift via `rubberband`
- **QC worker-path assertions** — `RenderService._complete_job` fetches delivery profile and builds `{loudness_integrated, true_peak}` assertions dict for `QCService.run_checks`
- **JobStatus.COMPLETED** — renamed from `COMPLETE` across 68+ occurrences; enum value `"completed"` unchanged

### Deferred (FFmpeg-gated)

- BL-437 ACs 1-4: pan contract tests — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_pan.py -k contract -v`
- BL-438 ACs 1-3: convolution reverb contract test — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_reverb.py::test_convolution_reverb_contract_ffmpeg -v`
- BL-439 AC-4: tone synthesis FFmpeg contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_api/test_tone_synthesis.py -v`
- BL-439 AC-2: automation envelope for tone — `frequency_end` is static; `py_compile_automation` not integrated
- BL-441 AC-2: generator clip render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_api/test_generator_clip.py -k ffmpeg -v`
- BL-488 ACs 3+5: QC worker-path E2E — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_render_service_qc.py::TestWorkerQCContractFFmpeg -v`
