# stoat-and-ferret

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v100 (Render Reliability, Evidence & Subtitle Hardening):** Multi-clip subtitle `-i` ordering fix (BL-618, PR #758); TTS amix source-audio data-loss fix (BL-578, PR #759); single-clip windowed dispatch gap fixed (BL-616, PR #760); render evidence script + `GET /render/{job_id}/evidence` endpoint (BL-554, PR #762); subtitle filtergraph hardening (BL-586/BL-601, PRs #763/#764); audio builder hardening — DuckingPair SQLite FK, TTS mixer guards, ZoompanBuilder bare-`n` rejection (BL-581/BL-582/BL-603, PRs #765–#767); vacuous test fixes + STATUS.md correction (BL-606/BL-617, PRs #768–#769). (PRs #758–#769.) See [CHANGELOG.md](docs/CHANGELOG.md) for release details.
