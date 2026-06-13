# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v081 (R2 Wave 5 — Video FX):** Added 6 new video FX effects — `ColorLutBuilder` with 3D LUT and bundled presets (BL-450, PR #597), `BlurBuilder`/`SharpenBuilder` with keyframable radius (BL-451, PR #595), `ChromaKeyBuilder`/`ColorKeyBuilder`/`BlendModeBuilder` with 10 blend modes (BL-452, PR #598), `LensDistortBuilder` for barrel/pincushion distortion (BL-453, PR #599), `GradientGeneratorBuilder`/`NoiseGeneratorBuilder` via lavfi (BL-454, PR #600), `OpacityBuilder`/`ScaleBuilder` with keyframed envelopes (BL-455); generic `automation_filter_template` dispatch refactor (PR #594); 10 new smoke tests, smoke-test harness guide update, UAT journeys J706–J710, acceptance harness (PRs #601–#604); effect registry 27→33; 3199 tests passing. 6 FFmpeg-gated ACs deferred with discharge plans. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
