# Sole-ownership audit

## Audited revision

- **Repository:** `https://github.com/gwickman/stoat-and-ferret`
- **Commit SHA:** `10c4b4d3eedf272913f2a0665d4fa1faa5d40348`
- **Working tree path:** `C:/Users/grant/Documents/projects/stoat-and-ferret`
- **Audit date:** 2026-06-23

## Audit scope

The audit covers all copyright-bearing material in the working tree at the audited revision:

- Python source under `src/` and `scripts/`, including helper scripts and CLI entry points
- Rust source under `rust/*/src/`
- Alembic migrations under `alembic/`
- Python tests under `tests/` (unit, smoke, contract, UAT journeys)
- Documentation under `docs/` (setup guides, design docs, manuals, agent-facing prompt material)
- Frontend source under `gui/src/` (TypeScript/React + Vitest tests)
- Build, packaging, and CI configuration: `pyproject.toml`, `Cargo.toml`, `Dockerfile`, `docker-compose.yml`, `package.json`, `vite.config.ts`, `.github/workflows/`
- Generated-but-checked-in artefacts: PyO3 `*.pyi` stub files
- Binary / media assets under `videos/` used as project fixtures
- Repository-root content: `README.md`, `AGENTS.md`, `CLAUDE.md`, `LICENSE` (current Apache-2.0 + MIT dual-license), `CHANGELOG.md`, `.gitignore`, root configuration files
- Vendored or copied snippets (none currently identified — see Exceptions)

The audit covers all material whose copyright would travel with the source under any redistribution, irrespective of whether it appears in `git log` author/committer history.

## Method

1. Enumerated every author and committer identity across all branches and tags:

   ```bash
   git log --all --format='%an <%ae>%n%cn <%ce>' | sort -u
   ```

   Result (exactly four identities):

   ```
   GitHub <noreply@github.com>
   Grant Wickman <grant.a.wickman@gmail.com>
   Grant Wickman <gwickman@users.noreply.github.com>
   auto-dev-mcp <auto-dev-mcp@localhost>
   ```

2. Reconciled each identity:

   | Identity | Reconciliation |
   |---|---|
   | `Grant Wickman <grant.a.wickman@gmail.com>` | Grant Wickman (sole human author). |
   | `Grant Wickman <gwickman@users.noreply.github.com>` | Same human; the noreply alias is the GitHub-provided email for Grant's account `gwickman`. |
   | `auto-dev-mcp <auto-dev-mcp@localhost>` | Identity used by Grant's auto-dev-mcp tooling operating under his direction and copyright. All commits authored under this identity were produced by tooling that Grant operates as sole maintainer; the output is work-for-self under Grant's copyright. |
   | `GitHub <noreply@github.com>` | GitHub's own committer identity, used by GitHub when generating merge commits via the web UI or API on Grant's behalf. This identity does not contribute new content; it only records GitHub's role as merge agent. |

3. Inspected non-git-tracked material:
   - Reviewed `videos/` fixture set: assets are project-generated test footage produced by Grant for use as smoke/UAT fixtures.
   - Reviewed documentation for embedded third-party snippets, copyright headers, or attribution notices that would indicate non-Grant material: none identified at the audited revision (the audit is consistent with the current absence of any `THIRD_PARTY_NOTICES.md` or vendored directory).
   - Reviewed dependency declarations (`pyproject.toml`, `Cargo.toml`, `package.json`): these declare third-party dependencies that remain under their own licences and are not redistributed in source form by this repository. Dependency-license inventory is in BL-529 scope and not pre-empted by this audit.
   - Reviewed PyO3 stub files (`*.pyi`): generated from Rust source via `stub_gen`; copyright follows the source.

4. Cross-referenced the `auto-dev-mcp <auto-dev-mcp@localhost>` commits against the working-agreement that the tooling is operated solely by Grant. No anomalies (no foreign machine identities, no other operator handles) appear in `git log --all`.

## Conclusion

All copyright-bearing material in the audited revision is owned by Grant Wickman, either as direct human author or as the operator of tooling acting under his copyright. The repository contains no third-party-authored content that would require a separate licence grant, attribution notice, or contributor copyright assignment.

This conclusion provides the sole-copyright provenance required to proceed with relicensing the audited revision from the current Apache-2.0 + MIT dual-licence to AGPL-3.0-or-later (BL-522).

## Exceptions

None. No material falls outside Grant Wickman's copyright at the audited revision.

If any exception is identified during BL-522 implementation review, the exception (and its resolution — excluded, replaced, or licensed) must be added to this section and the resolution must be in place before BL-522 lands.

## Signer + date

- Signer: Grant Wickman
- Date: 2026-06-23

## Authorisation

I authorise relicensing the audited revision to AGPL-3.0-or-later.
