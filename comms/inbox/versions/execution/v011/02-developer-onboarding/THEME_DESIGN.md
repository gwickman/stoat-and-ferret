# Theme: developer-onboarding

## Goal

Reduce onboarding friction and establish project-specific design-time quality checks. Creates the missing .env.example template, documents the Windows /dev/null pitfall, and defines impact assessment checks that catch recurring issue patterns at design time rather than in production.

## Design Artifacts

See `comms/outbox/versions/design/v011/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | env-example | BL-071 | Create .env.example with all Settings fields documented |
| 002 | windows-dev-guidance | BL-019 | Add Windows Git Bash /dev/null guidance to AGENTS.md |
| 003 | impact-assessment | BL-076 | Create IMPACT_ASSESSMENT.md with 4 project-specific design checks |

## Dependencies

- No external dependencies (documentation/configuration features only)
- Intra-theme dependency: 001-env-example must precede 003-impact-assessment (assessment checks for .env.example updates)
- 002-windows-dev-guidance is independent and can run at any point

## Technical Approach

**001-env-example:** Audit the Settings class in `src/stoat_ferret/api/settings.py` (11 fields) and create `.env.example` with all `STOAT_`-prefixed variables grouped by category. Update `docs/setup/02_development-setup.md` and `docs/manual/01_getting-started.md` to reference it. Fix 2-variable gap in `docs/setup/04_configuration.md`. See `004-research/codebase-patterns.md` for Settings field inventory.

**002-windows-dev-guidance:** Add a "Windows (Git Bash)" section to AGENTS.md after the Commands section with correct/incorrect examples for `/dev/null` vs `nul`. The `.gitignore` already has a `nul` entry — no change needed. See `004-research/codebase-patterns.md` for insertion point.

**003-impact-assessment:** Create `docs/auto-dev/IMPACT_ASSESSMENT.md` with 4 structured check sections (async safety, settings documentation, cross-version wiring, GUI input mechanisms). Each check includes what to look for, why it matters, and a concrete project-history example. Format validated as appropriate for auto-dev Task 003 consumption. See `006-critical-thinking/risk-assessment.md` for format confirmation.

## Risks

| Risk | Mitigation |
|------|------------|
| IMPACT_ASSESSMENT.md format not machine-parseable | Format confirmed appropriate by investigation — auto-dev agent interprets markdown headings as check categories — see `006-critical-thinking/risk-assessment.md` |
| Feature 003 depends on feature 001 | Execution order handles this — 001-env-example precedes 003-impact-assessment |