# Requirements: env-example

## Goal

Create .env.example documenting all environment configuration variables so new developers can set up the project without reverse-engineering Settings from source code.

## Background

Backlog Item: BL-071 — Add .env.example file for environment configuration template.

The project has no .env.example file. Anyone setting up the project must read `src/stoat_ferret/api/settings.py` to discover which environment variables are needed. This is a common onboarding friction point. The Settings class has 11 fields (10 configurable + `allowed_scan_roots`), but `docs/setup/04_configuration.md` only documents 9 (missing `log_backup_count` and `log_max_bytes`).

## Functional Requirements

**FR-001: .env.example file**
- `.env.example` exists in the project root with all 11 Settings fields
- Each variable uses the `STOAT_` prefix matching the Settings class `env_prefix`
- Acceptance: File contains all 11 variables with `STOAT_` prefix

**FR-002: Documentation comments**
- Each variable includes a comment explaining its purpose and acceptable values
- Acceptance: Every variable line is preceded by a descriptive comment

**FR-003: Sensible defaults**
- Contains default values matching the Settings class (not real secrets)
- Acceptance: Values match `settings.py` defaults; no real secrets present

**FR-004: Category grouping**
- Variables grouped by category: database, API server, logging, security, frontend
- Acceptance: Clear section headers separate variable groups

**FR-005: Development setup reference**
- `docs/setup/02_development-setup.md` references .env.example in setup steps
- Acceptance: Setup docs include `cp .env.example .env` instruction

**FR-006: Getting started reference**
- `docs/manual/01_getting-started.md` references .env.example
- Acceptance: Getting started guide mentions .env.example

**FR-007: Configuration docs completeness**
- `docs/setup/04_configuration.md` updated to document all 11 variables (adds `log_backup_count` and `log_max_bytes`)
- Acceptance: Configuration docs cover all 11 Settings fields

## Non-Functional Requirements

**NFR-001: Completeness**
- Every Settings field in `settings.py` has a corresponding entry in `.env.example`
- Metric: Count of .env.example variables matches count of Settings fields (11)

## Out of Scope

- Automated validation that .env.example stays in sync with Settings class (deferred — could be a CI check)
- Docker/container-specific environment configuration
- Secret management tooling

## Test Requirements

**Manual verification:**
- `cp .env.example .env` then application starts with default settings
- All 11 Settings fields present with `STOAT_` prefix
- Docs references render correctly in markdown

## Reference

See `comms/outbox/versions/design/v011/004-research/` for supporting evidence:
- `codebase-patterns.md` — Settings class field inventory (11 fields with types, defaults, env vars)
- `evidence-log.md` — Settings field count confirmation