# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v102 (QC Gate Correctness + UAT/Acceptance Harness):** Fixed `overall_verdict` aggregation treating null-checks as failures (BL-623, PR #778); fixed tone_presence FFmpeg command missing ametadata (BL-624, PR #779); fixed loudness check tolerance bidirectionality (BL-625, PR #780); fixed decode_integrity using stream-copy instead of null-decode (BL-626, PR #781); fixed OC-6/OC-15/OC-12 QC mapping gap (BL-627, PR #782); fixed `/qc/run` ignoring delivery-profile targets (BL-628, PR #783); discharged BL-457-AC-3 (headed UAT J703/J704, direct commit); BL-459 acceptance harness repair (PR #785); registered J204, J502/J504 in UAT known-failures registry (BL-536/BL-558, direct commits). (PRs #778–#785.) See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
