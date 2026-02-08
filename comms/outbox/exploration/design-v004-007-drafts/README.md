Document drafts created for v004: 5 themes, 15 features. All 13 backlog items (BL-020 through BL-027, BL-009, BL-010, BL-012, BL-014, BL-016) are covered with requirements.md and implementation-plan.md per feature, THEME_DESIGN.md per theme, and VERSION_DESIGN.md + THEME_INDEX.md at the version level.

## Contents

- `drafts/manifest.json` — Version metadata with theme/feature structure
- `drafts/VERSION_DESIGN.md` — Version-level design overview referencing the artifact store
- `drafts/THEME_INDEX.md` — Machine-parseable theme and feature index
- `drafts/{theme-slug}/THEME_DESIGN.md` — Theme-level design (5 themes)
- `drafts/{theme-slug}/{feature-slug}/requirements.md` — Feature requirements (15 features)
- `drafts/{theme-slug}/{feature-slug}/implementation-plan.md` — Feature implementation plans (15 features)
- `draft-checklist.md` — Verification checklist

## Document Counts

| Document Type | Count |
|---------------|-------|
| manifest.json | 1 |
| VERSION_DESIGN.md | 1 |
| THEME_INDEX.md | 1 |
| THEME_DESIGN.md | 5 |
| requirements.md | 15 |
| implementation-plan.md | 15 |
| **Total** | **38** |

## Design Source

All documents reference the centralized artifact store at `comms/outbox/versions/design/v004/`. The primary design source is `006-critical-thinking/refined-logical-design.md` from Task 006.
