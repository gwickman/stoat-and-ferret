# Historical License Reconciliation — stoat-and-ferret

## Pre-v083 Distribution History

| Release Identifier | Distribution Channel | LICENSE Content | pyproject.toml Declaration | Conveyed License | Reconciliation Verdict |
|-------------------|---------------------|-----------------|---------------------------|------------------|----------------------|
| (none) | (none) | Apache-2.0 (full text) | MIT (`license = { text = "MIT" }`) | N/A (not distributed) | No distributed artefacts pre-v083 |

## Contradictory Declarations (Source-Form Only)

The pre-v083 source tree carried contradictory license declarations:

- `LICENSE` file: verbatim Apache License 2.0 text
- `pyproject.toml`: `license = { text = "MIT" }` (line 7 in all pre-v083 commits)
- `rust/stoat_ferret_core/Cargo.toml`: no `license` field (field absent entirely)

No releases were distributed via any channel prior to v083:

- `git tag --list` returns empty — no git tags exist
- `gh release list` returns empty — no GitHub releases exist
- No PyPI uploads confirmed — `pyproject.toml` contains no `[tool.hatch.publish]` or equivalent
  publish configuration, and no distribution records exist

Verified at commit `10c4b4d3` (2026-06-23) via `git tag --list` and `gh release list`.

## Reconciliation Verdict

**BL-530-AC-4 case applies**: No distributed artefacts pre-v083 exist; in-source licence terms
apply to any source-form use.

Defensive interpretation: consumers of any pre-v083 source snapshot may treat the code under
Apache-2.0 or MIT at their option. The contradictory declaration is recorded here so consumers
have full information; the maintainer does not retroactively assert either as the definitive
historical licence.

This wording deliberately does NOT assert "Apache-only" for prior source snapshots — the
contradictory Apache-2.0 LICENSE file alongside the MIT `pyproject.toml` declaration prevents
any single-licence assertion from being accurate.

## Reference in CHANGELOG

This document is referenced from the CHANGELOG v083 entry (`docs/CHANGELOG.md`) in the
non-retroactivity wording for the relicense to AGPL-3.0-or-later.

## Preparation Date

2026-06-23 (v083 execution phase; verified via `git tag --list` and `gh release list` at
commit `10c4b4d3`).
