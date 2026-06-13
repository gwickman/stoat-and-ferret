# Project Status — stoat-and-ferret

**Current version:** v081 (Release 2, Wave 5 — Video FX)
**Status:** Completed 2026-06-13

## v081 Summary

Release 2, Wave 5 delivers 11 video effects across three themes: automated video FX (blur, sharpen, opacity, scale, color grading), compositing and stylization (chromakey, colorkey, lens distortion, generators), and test coverage with smoke tests and acceptance harness updates.

### Delivered

| Theme | Feature | Status | PR |
|-------|---------|--------|----|
| automated-video-fx | automation-dispatch-refactor | ✓ | #594 |
| automated-video-fx | blur-sharpen-effects | ✓ | #595 |
| automated-video-fx | opacity-scale-animation | ✓ | #596 |
| automated-video-fx | color-lut-grading | ✓ | #597 |
| compositing-and-stylization | keying-blend-compositing | ✓ | #598 |
| compositing-and-stylization | optical-distortion | ✓ | #599 |
| compositing-and-stylization | procedural-generators | ✓ | #600 |
| test-coverage-and-release-acceptance | video-fx-smoke-tests | ✓ | #601 |
| test-coverage-and-release-acceptance | smoke-harness-guide-update | ✓ | #602 |
| test-coverage-and-release-acceptance | uat-journeys | ✓ | #603 |
| test-coverage-and-release-acceptance | acceptance-harness | ✓ | #604 |

### Test Results

- **Test count:** ~3199 passed (3069 baseline → +130)
- **Regressions:** 0
- **FFmpeg-gated (deferred_post_merge):** BL-450 ACs 3-4, BL-451 AC-4, BL-452 AC-4, BL-453 AC-4, BL-454 AC-4, BL-455 AC-4

### Key Capabilities Added

- **automation_filter_template** — generic `automation_filter_template` on EffectDefinition; `build_automation_filter_string` dispatcher supports all automatable effects
- **BlurBuilder** — gaussian blur (`gblur`) and directional blur (`dblur`) with automatable radius parameter; `automation=True` on effect definition
- **SharpenBuilder** — unsharp mask sharpening with automation support
- **OpacityBuilder** — keyframed opacity envelopes with full automation contract support
- **ScaleBuilder** — video scaling with automatable width/height parameters and envelope keyframes
- **ColorLutBuilder** — 3D LUT-based color grading; 3 bundled presets (`identity`, `calming_teal`, `warm_fade`)
- **ChromaKeyBuilder** — chroma key compositing with configurable thresholds and similarity tolerance
- **ColorKeyBuilder** — color-range keying for selective color removal
- **LensDistortBuilder** — barrel and pincushion distortion correction via `lenscorrection` filter; k1/k2 coefficients
- **GradientGeneratorBuilder** — procedural gradient generation using `gradients` lavfi source
- **NoiseGeneratorBuilder** — procedural noise generation using `cellauto` lavfi source
- **Effect registry expansion** — 27 → 33 effects (+6 effect types, +4 builders with automation support)
- **blend_mode schema** — added to `build_composition_graph` for advanced compositing control

### Deferred (FFmpeg/UAT-gated)

- BL-450 ACs 3-4: blur effect FFmpeg contract tests
- BL-451 AC-4: sharpen effect UAT discharge
- BL-452 AC-4: opacity-scale automation FFmpeg contract
- BL-453 AC-4: color LUT grading FFmpeg contract
- BL-454 AC-4: keying blend compositing FFmpeg contract
- BL-455 AC-4: optical-distortion and generator FFmpeg contract
