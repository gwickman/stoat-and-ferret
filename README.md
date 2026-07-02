# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v093 (API Correctness & Rust Quality):** Render correctness hotfixes — soft subtitle stream map repair (BL-583), image-clip asset validation at creation time (BL-574), `TrackCreate` finite IEEE 754 validation (BL-579); API test coverage — TTS and DuckingPair HTTP layer CRUD test suites (BL-580, BL-581), ducking quiet-window discharge test (BL-588), TTS speech energy placement test (BL-589); documentation drift repair — `generated_asset_id` → `audio_path` cleanup (BL-587), UAT baseline cleanup (BL-565), smoke skip message update (BL-576); Rust quality — `WrongArity` variant in `ProceduralParserError` (BL-575), `BurnedSubtitleBuilder` migrated to `emit_filter_value` dispatch (BL-555). (PRs #701–#715.) See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
