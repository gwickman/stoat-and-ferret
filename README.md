# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v085 (Post-v084 Compliance Riders):** C4 API YAML updated to AGPL-3.0-or-later with `/api/v1/source` and `SourceResponse` documented (BL-541, PR #642); CI stray-reference scan extended to `*.yaml`/`*.yml` files (BL-541, PR #643); dependency-checker test fixed with `--check` flag and `test_no_arg_prints_usage` added (BL-542, PR #644); `.gitignore` orchestration guard assertion added to test suite (BL-543, PR #645); stray-MIT detector tests rewritten with Python `re` for Windows portability (BL-544, PR #646); 3251 tests passing. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
