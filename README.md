# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v088 (R3 Wave 2):** Rust `RenderGraphTranslator` converts multi-clip timelines with per-clip effects to FFmpeg `filter_complex` strings; render worker wired to call translator for all submitted projects; `ValueKind` enum and `emit_filter_value` dispatch unify FFmpeg escape handling across effect builders; UAT failure registry extended with J502/J504; Windows smoke command documented with `UV_NO_CACHE=1`; dep-license test skip guard fixed; C4 drift test upgraded to compare against live in-process spec (PRs #662–#669). See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
