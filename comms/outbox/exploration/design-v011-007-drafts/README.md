# Design v011 — Document Drafts

Created complete design document drafts for v011 (GUI Usability & Developer Experience): 2 themes, 5 features, covering 5 backlog items (BL-019, BL-070, BL-071, BL-075, BL-076). All documents are individual files under `drafts/` with a `manifest.json` as the single source of truth for numbering and metadata.

## Document Inventory

### Version-Level
- `drafts/manifest.json` — Version metadata, theme/feature numbering, goals
- `drafts/VERSION_DESIGN.md` — Version-level design overview with artifact store references
- `drafts/THEME_INDEX.md` — Machine-parseable theme/feature index

### Theme 1: scan-and-clip-ux (2 features)
- `drafts/scan-and-clip-ux/THEME_DESIGN.md`
- `drafts/scan-and-clip-ux/browse-directory/requirements.md`
- `drafts/scan-and-clip-ux/browse-directory/implementation-plan.md`
- `drafts/scan-and-clip-ux/clip-crud-controls/requirements.md`
- `drafts/scan-and-clip-ux/clip-crud-controls/implementation-plan.md`

### Theme 2: developer-onboarding (3 features)
- `drafts/developer-onboarding/THEME_DESIGN.md`
- `drafts/developer-onboarding/env-example/requirements.md`
- `drafts/developer-onboarding/env-example/implementation-plan.md`
- `drafts/developer-onboarding/windows-dev-guidance/requirements.md`
- `drafts/developer-onboarding/windows-dev-guidance/implementation-plan.md`
- `drafts/developer-onboarding/impact-assessment/requirements.md`
- `drafts/developer-onboarding/impact-assessment/implementation-plan.md`

**Total:** 16 documents (1 manifest + 3 version-level + 2 theme designs + 5 requirements + 5 implementation plans)

## Reference Pattern

All documents are lean and reference the design artifact store rather than duplicating content:
- `comms/outbox/versions/design/v011/004-research/` — for evidence and codebase patterns
- `comms/outbox/versions/design/v011/006-critical-thinking/` — for risk assessments and investigation findings
- `comms/outbox/versions/design/v011/001-environment/` — for version context and constraints

## Completeness Check

All 5 backlog items mapped to features:
- BL-019 → developer-onboarding / windows-dev-guidance
- BL-070 → scan-and-clip-ux / browse-directory
- BL-071 → developer-onboarding / env-example
- BL-075 → scan-and-clip-ux / clip-crud-controls
- BL-076 → developer-onboarding / impact-assessment

All backlog IDs cross-referenced against Task 002 backlog analysis. No mismatches found.

## Format Verification

- THEME_INDEX.md feature lines match regex `- \d{3}-[\w-]+: .+` (e.g., `- 001-browse-directory: Add backend...`)
- No numbered list format (`1.`, `2.`) used for features
- No bold feature identifiers
- No metadata before colon
- All feature entries are single-line

## Path Verification

All "Files to Modify" paths verified via Glob against actual codebase structure:
- Corrected `src/stoat_ferret/main.py` → `src/stoat_ferret/api/app.py` (actual app factory location)
- Corrected `tests/api/test_filesystem.py` → `tests/test_api/test_filesystem.py` (actual test directory)
- All other paths confirmed to exist in codebase
- All "Files to Create" parent directories confirmed to exist
