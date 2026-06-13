# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v082 (R2 Wave 5 Carry-Forward):** Added `ChromaticAberrationBuilder` (RGB-channel shift via FFmpeg `rgbashift`, 34th effect, PR #612); fixed 4 FFmpeg correctness bugs — ColorLutBuilder Windows path escaping (BL-499, PR #608), BlurBuilder directional mode option mismatch (BL-500, PR #609), NoiseGeneratorBuilder invalid `cellauto d` option (BL-501, PR #610), automation expression comma escaping (BL-502, PR #611); FFmpeg contract test discharge for blur/sharpen and generators (PRs for BL-451/BL-454); UAT discharge for opacity/scale and 5/6 R2 journeys; 3275 tests passing. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
