# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v101 (QC Completion — R2 P1 Cluster):** QC loudness/true-peak parser fixed (BL-476, PR #771); worker-path QC wiring + delivery-profile assertions (BL-477/BL-488, PR #772); five Rust QC measurement parsers with proptest + FFmpeg-gated discharge (BL-423, PR #773); golden fixture determinism test (BL-424-AC-5, PR #774); `verify_render_output.py` default mode fix (BL-620, PR #775); multi-clip TTS amix first-clip-with-audio fix (BL-621, PR #776); TTS validation gaps — duplicate track ID detection + start_s upper bound (BL-622, PR #777). (PRs #771–#777.) See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
