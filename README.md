# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v086 (Post-v085 Compliance Riders):** C4 YAML aligned with live OpenAPI on `/api/v1/source`, `SourceResponse`, and `license_info` surfaces (BL-546, PR #648); version metadata unified via `importlib.metadata` (BL-547, PR #648); `check_dependency_licenses.py` subprocess portability fixed (BL-548, PR #649); gitignore guard test updated to strip comments before scanning (BL-549, PR #649); CI stray-ref scan extended to `*.toml` files (BL-550, PR #649); 3320 tests passing. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
