# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v084 (Post-v083 Compliance Hygiene Wave):** GUI URL scheme validation in StatusBar (BL-537, PR #630); typed `SourceResponse` Pydantic model for `GET /api/v1/source` (BL-539, PR #631); C4 docs updated for source.py compliance router and settings (BL-531, PR #632); SPDX header gate expanded to all tracked `.py`/`.rs` files via `git ls-files` (BL-532, PR #635); dependency license checker now derives inventory from `pyproject.toml` manifest (BL-533, PR #636); bare MIT token detection added to stray-reference grep (BL-538, PR #637); orchestration artifacts removed from repo with `.gitignore` guards (BL-534, PR #638); root `CHANGELOG.md` replaced with redirect stub (BL-535, PR #639); UAT known-failures registry updated with Journey 204 (BL-536, PR #640); 3249 tests passing. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
