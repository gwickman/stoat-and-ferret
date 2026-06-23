# NOTICE

stoat-and-ferret — Copyright (C) 2026 Grant Wickman
Licensed under the GNU Affero General Public License v3 or later (AGPL-3.0-or-later).
See LICENSE for the full license text.

## Dependency License Inventory

A full transitive dependency scan was performed as part of the v083 release
(see docs/legal/dependency-license-inventory.md). The scan covered:

- 10 Python direct production dependencies (all permissive: MIT, BSD, Apache-2.0)
- 8 Python direct development dependencies (dev-only, not conveyed)
- 4 Rust direct dependencies (all MIT OR Apache-2.0, statically linked)
- 436 Node.js packages (all dev/build tooling, not conveyed in production)
- Notable transitive Python dependencies with non-permissive licenses (see inventory)

No dependencies requiring a separate notice entry were identified in the declared
transitive dependency graph.

## piper-tts Finding

piper-tts (GPL-3.0-or-later, https://github.com/OHF-Voice/piper1-gpl) was found
in the scan environment (`uv run pip-licenses` reports `piper-tts 1.4.2
GPL-3.0-or-later`) but is **not found in the transitive dependency graph** as of
the v083 scan. `pip show piper-tts` confirms `Required-by:` is empty — no declared
snf package depends on it. It is installed in the system Python environment, not via
the snf dependency graph.

stoat-and-ferret does **not** convey piper-tts as a wheel-level dependency in its
declared package graph. This finding is recorded in docs/legal/dependency-license-inventory.md
§ Risk 1.

## PyMuPDF Finding

PyMuPDF (AGPL-3.0-or-later OR Artifex-Commercial) was found in the scan environment
but is **not listed as an snf direct or transitive dependency** in `pyproject.toml`.
stoat-and-ferret does not convey PyMuPDF as a declared dependency. This finding is
recorded in docs/legal/dependency-license-inventory.md § Risk 2.
