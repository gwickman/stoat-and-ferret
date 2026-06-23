# Dependency License Inventory

<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

## Header

- **Date**: 2026-06-23
- **Scan commit SHA**: b2dd821a22d4d2ec5ad72bb7d3386e16c771c6ae
- **Scan tools**: pip-licenses (Python), cargo metadata (Rust), npx license-checker (Node.js)
- **SPDX canonical names**: All license expressions use SPDX identifiers per https://spdx.org/licenses/
- **piper-tts finding**: `piper-tts 1.4.2 GPL-3.0-or-later` is **FOUND** in the environment scan
  (`uv run pip-licenses` output). It is NOT declared as a direct or transitive dependency in
  `pyproject.toml` or `Cargo.toml`. The `Required-by:` field in `pip show piper-tts` is empty,
  confirming no declared snf package depends on it. It appears to be installed separately in the
  system Python environment. BL-527-AC-3 asserts snf "conveys Piper as a wheel-level dependency"
  — this assertion requires operator verification. Recorded in Risks section below.

---

## Python Direct Production Dependencies

Source: `pyproject.toml` `[project.dependencies]`

| name | version | declared license (SPDX) | conveyance | classification | AGPL-3.0-or-later compat | notice-required |
|------|---------|------------------------|------------|----------------|--------------------------|-----------------|
| `alembic` | 1.18.4 | MIT | wheel | permissive | compatible | no |
| `aiosqlite` | 0.22.1 | MIT | wheel | permissive | compatible | no |
| `fastapi` | 0.128.0 | MIT | wheel | permissive | compatible | no |
| `jsonschema` | 4.26.0 | MIT | wheel | permissive | compatible | no |
| `pillow` | 12.1.0 | MIT-CMU | wheel | permissive | compatible | no |
| `prometheus-client` | 0.24.1 | Apache-2.0 AND BSD-2-Clause | wheel | permissive | compatible | no |
| `pydantic-settings` | 2.12.0 | MIT | wheel | permissive | compatible | no |
| `python-dotenv` | 1.2.2 | BSD-3-Clause | wheel | permissive | compatible | no |
| `structlog` | 25.5.0 | MIT OR Apache-2.0 | wheel | permissive | compatible | no |
| `uvicorn` | 0.40.0 | BSD-3-Clause | wheel | permissive | compatible | no |

---

## Python Direct Development Dependencies

Source: `pyproject.toml` `[dependency-groups.dev]`

Development dependencies are not conveyed in production builds. AGPL-3.0-or-later compatibility
verdict applies to the development environment only.

| name | version | declared license (SPDX) | conveyance | classification | AGPL-3.0-or-later compat | notice-required |
|------|---------|------------------------|------------|----------------|--------------------------|-----------------|
| `coverage` | 7.13.2 | Apache-2.0 | dev-only | permissive | compatible | no |
| `httpx` | 0.28.1 | BSD-3-Clause | dev-only | permissive | compatible | no |
| `hypothesis` | 6.152.1 | MPL-2.0 | dev-only | weak-copyleft | compatible (dev-only; not conveyed) | no |
| `maturin` | 1.11.5 | MIT OR Apache-2.0 | dev-only | permissive | compatible | no |
| `mypy` | 1.19.1 | MIT | dev-only | permissive | compatible | no |
| `pytest` | 9.0.2 | MIT | dev-only | permissive | compatible | no |
| `pytest-cov` | 7.0.0 | MIT | dev-only | permissive | compatible | no |
| `ruff` | 0.14.14 | MIT | dev-only | permissive | compatible | no |

---

## Rust Direct Dependencies

Source: `rust/stoat_ferret_core/Cargo.toml` `[dependencies]`

Rust deps are statically linked into `stoat_ferret_core.so` / `.pyd` — they are conveyed
as compiled binary inside the wheel.

| name | version | declared license (SPDX) | conveyance | classification | AGPL-3.0-or-later compat | notice-required |
|------|---------|------------------------|------------|----------------|--------------------------|-----------------|
| `pyo3` | 0.26.0 | MIT OR Apache-2.0 | static-link | permissive | compatible | no |
| `pyo3-stub-gen` | 0.17.2 | MIT OR Apache-2.0 | dev-only | permissive | compatible | no |
| `regex` | 1.12.3 | MIT OR Apache-2.0 | static-link | permissive | compatible | no |
| `serde_json` | 1.0.149 | MIT OR Apache-2.0 | static-link | permissive | compatible | no |

### Rust Transitive Dependencies

Full transitive Rust dependency graph is MIT OR Apache-2.0 throughout, with three exceptions
identified by `cargo metadata` inspection:

| name | version | declared license (SPDX) | note |
|------|---------|------------------------|------|
| `r-efi` | 5.3.0 | MIT OR Apache-2.0 OR LGPL-2.1-or-later | LGPL-2.1 option present but MIT/Apache-2.0 can be chosen; compatible |
| `tiny-keccak` | 2.0.2 | CC0-1.0 | Public domain dedication; fully compatible |
| `unicode-ident` | 1.0.22 | (MIT OR Apache-2.0) AND Unicode-3.0 | Unicode-3.0 is permissive; compatible |

No GPL/AGPL/LGPL-only dependencies found in Rust transitive graph.

---

## Node.js Dependencies (GUI)

Source: `gui/package.json` — 436 packages scanned via `npx license-checker`

All Node.js packages are devDependencies (TypeScript build tooling, Vite, Vitest). They are
NOT conveyed in production — the GUI ships as compiled JS/CSS static assets from `gui/dist/`.

Notable license hits from `npx license-checker`:

| name | version | declared license (SPDX) | note |
|------|---------|------------------------|------|
| `@axe-core/playwright` | 4.11.1 | MPL-2.0 | Accessibility testing dev dep; not conveyed |
| `axe-core` | 4.11.1 | MPL-2.0 | Accessibility testing dev dep; not conveyed |
| `lightningcss` | 1.30.2 | MPL-2.0 | CSS minifier used at build time; not in dist bundle |
| `lightningcss-win32-x64-msvc` | 1.30.2 | MPL-2.0 | Platform binary for above; not conveyed |

All remaining 432 Node packages are MIT, BSD-2/3-Clause, ISC, Apache-2.0, or 0BSD.
No GPL/LGPL/EPL/CDDL hits found.

---

## Notable Transitive Python Dependencies Survey

Survey of notable transitive deps with weak or strong copyleft licenses (per
`uv run pip-licenses` on the snf environment, 155 packages scanned).

| name | version | declared license (SPDX) | role | conveyance | AGPL-3.0-or-later compat | notice-required |
|------|---------|------------------------|------|------------|--------------------------|-----------------|
| `certifi` | 2026.1.4 | MPL-2.0 | TLS CA bundle, transitive via httpx (dev) | dev-only | compatible (dev-only) | no |
| `chardet` | 6.0.0.post1 | LGPL-2.1-or-later | Charset detection, transitive | transitive | compatible (LGPL-2.1-or-later + AGPL OK) | no |
| `CairoSVG` | 2.9.0 | LGPL-3.0-or-later | SVG rendering, transitive | transitive | compatible (LGPL library use) | no |
| `fpdf2` | 2.8.7 | LGPL-3.0-only | PDF generation, transitive | transitive | compatible (LGPL library use) | no |
| `hypothesis` | 6.152.1 | MPL-2.0 | Property-based testing (dev dep) | dev-only | compatible (dev-only, not conveyed) | no |
| `orjson` | 3.11.6 | MPL-2.0 AND (Apache-2.0 OR MIT) | JSON library, transitive | transitive | compatible (Apache-2.0 OR MIT option available) | no |
| `pathspec` | 1.0.4 | MPL-2.0 | Path pattern matching, transitive | transitive | compatible (MPL-2.0 file-level copyleft) | no |
| `piper-tts` | 1.4.2 | GPL-3.0-or-later | TTS engine | see Risks | see Risks | **yes — see Risks** |
| `PyMuPDF` | 1.27.2 | AGPL-3.0-or-later OR Artifex-Commercial | PDF processing, transitive | transitive | compatible if used under AGPL option | **yes** |
| `tqdm` | 4.67.1 | MIT AND MPL-2.0 | Progress bars, transitive | transitive | compatible (MIT option available) | no |

**UNKNOWN license packages found in environment scan:**

| name | version | note |
|------|---------|------|
| `ai-framework` | 0.1.0 | MCP tooling package; NOT an snf dep; UNKNOWN license |
| `auto-dev-mcp` | 0.1.0 | MCP orchestration package; NOT an snf dep; UNKNOWN license |

These two UNKNOWN-license packages are external tool packages installed in the development
environment, not snf production or dev dependencies. They are recorded here for completeness
per NFR-002. No resolution action required for snf licensing.

---

## Risks

### Risk 1: piper-tts (GPL-3.0-or-later) — Conveyance Status Unclear

| Field | Value |
|-------|-------|
| Package | piper-tts 1.4.2 |
| License | GPL-3.0-or-later |
| URL | http://github.com/OHF-voice/piper1-gpl |
| Classification | strong-copyleft |
| AGPL-3.0-or-later compat | compatible (GPL-3.0+ and AGPL-3.0 are mutually compatible under the GNU terms) |
| notice-required | **yes** — if conveyed |
| Status | **TBD** — conveyance status requires operator verification |

**Finding**: `piper-tts 1.4.2` is present in the scanned snf environment. However:
- It is NOT listed in `pyproject.toml` or `Cargo.toml` as a direct dependency.
- `pip show piper-tts` shows `Required-by:` is empty — no declared snf package depends on it.
- It is installed in the system Python environment (`C:\Users\grant\AppData\Local\Programs\Python\Python312`), not as a transitive dep of any snf package.

**Design assertion**: BL-527-AC-3 asserts snf "conveys Piper as a wheel-level dependency."
This assertion is based on prior research (BL-DRAFT-bl516-tts.md). The current transitive
scan does NOT confirm piper-tts as a snf transitive dependency from declared deps.

**Proposed resolution**: Operator must verify whether snf intends to convey piper-tts:
- If YES: add piper-tts as an explicit optional dependency in pyproject.toml and add it to NOTICE.md.
- If NO: document that piper-tts is NOT conveyed by snf in NOTICE.md and remove it from scope.
- Either way: record the final finding in NOTICE.md (BL-527-AC-3).

### Risk 2: PyMuPDF (AGPL-3.0-or-later OR Artifex-Commercial) — Notice Required if Conveyed

| Field | Value |
|-------|-------|
| Package | PyMuPDF 1.27.2 |
| License | AGPL-3.0-or-later OR Artifex-Commercial |
| Classification | strong-copyleft (AGPL option) |
| AGPL-3.0-or-later compat | compatible if used under AGPL-3.0-or-later option |
| notice-required | yes — if conveyed under AGPL option |
| Status | **TBD** — operator to confirm if PyMuPDF is an intentional snf dep |

**Finding**: PyMuPDF is present in the scan environment but is NOT listed as an snf direct
dependency in `pyproject.toml`. Likely installed transitively via a dev/test package.

**Proposed resolution**: If PyMuPDF is intended to be conveyed: add explicit dep, include in
NOTICE.md. If not: document as non-conveyed.

---

## Inventory Completeness Note

This inventory covers:
- All declared direct Python production dependencies (10 packages)
- All declared direct Python dev dependencies (8 packages sampled)
- All declared direct Rust dependencies (4 packages)
- All Node.js packages (436 packages scanned, notable licenses listed)
- All notable transitive Python deps with non-permissive licenses from full environment scan

No deps are flagged `incompatible` with AGPL-3.0-or-later. Two deps (`piper-tts`, `PyMuPDF`)
are flagged `TBD` pending operator resolution on conveyance status.
