# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v103 (R2/R3 Effect-Umbrella Triage and Discharge):** Clamped tone synthesis frequency to [20, 20000] Hz (BL-494, PR #788); wired `Automation` type into tone generator frequency (BL-495, PR #789); added `_escape_filter_option_path()` helper for Windows LUT path colon escaping in `lut3d` filter (BL-563, PR #790); 13+ audio/video effect ACs discharged via `STOAT_TEST_FFMPEG=1` (BL-430/431/434/435/437/438/444/445/446/449/450/453/516/517/519/520, PRs #791–#794). See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
