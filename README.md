# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v079 (R2 Wave 3 — Sound Design + v078 Repair Rider):** Added PanBuilder for stereo pan automation (BL-437, PR #569), ConvolutionReverbBuilder (BL-438, PR #570), generator clip enabler (BL-441, PR #574), tone synthesis with chirp/binaural/sweep (BL-439, PR #576), sub-bass layer with sidechain ducking (BL-442), loopable beds (BL-440), PitchShiftBuilder with formant control (BL-443, PR #577); restored ON DELETE CASCADE on clips.project_id FK (BL-441, PR #575); wave-T smoke test coverage (PR #579). 6 FFmpeg/UAT-gated ACs deferred with discharge plans. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
