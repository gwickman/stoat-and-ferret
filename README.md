# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v090 (R3 Wave 3b+G):** User asset library REST API (upload/list/download/soft-delete with Pillow magic-bytes validation and SHA-256 deduplication); image clip support (`clip_type=image` schema with `source_asset_id` persistence); `GenericProceduralImageBuilder` PyO3 class backed by a Rust recursive-descent expression parser; IEEE 754 NaN/inf guards across CurvesBuilder, VignetteBuilder, and shape generators; empty-expression guards for HueRotation/Zoompan; ZoompanBuilder i64 integer promotion (PRs #680–#686). See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
