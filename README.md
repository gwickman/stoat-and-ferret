# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v078 (R2 Repair — QC Integrity, DSP Correctness & R2 Doc Parity):** Fixed QC loudness measurement (BL-476, PR #550), wired worker-path QC (BL-477, PR #551), fixed deesser/multiband FFmpeg params (BL-478, PR #552), added eval=frame for volume automation (BL-479+BL-482, PR #553); added automatable_parameters to EffectResponse API (BL-481, PR #555); added DSP and QC agent docs, delivery profiles docs, and C4 drift fix (BL-483–485, BL-469, PRs #558–#561); added QC-fail GUI surfaces and UAT journey (BL-480, PR #562). 6 FFmpeg/UAT-gated ACs deferred with discharge plans. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
