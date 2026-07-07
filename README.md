# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v099 (Image/Generator Clip Types + Windowed Effects):** Per-clip effect params dict fix (BL-615, PR #753); render worker extended to image clip (`-loop 1 -i`) and generator clip routing (BL-511/BL-604, PR #754); `windowed_custom()` factory + WindowSpec database storage (BL-512, PR #756); `RenderGraphTranslator` enable= expression injection for T-capable windowed effects via translate.rs (BL-512, PR #757). BL-511 completed (7/7 ACs). (PRs #753, #754, #756, #757.) See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
