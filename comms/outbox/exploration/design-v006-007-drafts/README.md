# Exploration: design-v006-007-drafts

Document drafts for v006 (Effects Engine Foundation): 3 themes, 9 features, covering 7 backlog items (BL-037 through BL-043). All documents are lean and reference the design artifact store at `comms/outbox/versions/design/v006/` for detailed analysis.

## Document Inventory

### Version-Level Documents
- `drafts/manifest.json` — Version metadata, theme/feature numbering, goals (single source of truth for Task 008)
- `drafts/VERSION_DESIGN.md` — Version-level design with constraints, key decisions, theme overview
- `drafts/THEME_INDEX.md` — Machine-parseable theme and feature index

### Theme 01: filter-expression-infrastructure (BL-037, BL-038)
- `drafts/filter-expression-infrastructure/THEME_DESIGN.md`
- `drafts/filter-expression-infrastructure/expression-engine/requirements.md`
- `drafts/filter-expression-infrastructure/expression-engine/implementation-plan.md`
- `drafts/filter-expression-infrastructure/graph-validation/requirements.md`
- `drafts/filter-expression-infrastructure/graph-validation/implementation-plan.md`

### Theme 02: filter-builders-and-composition (BL-039, BL-040, BL-041)
- `drafts/filter-builders-and-composition/THEME_DESIGN.md`
- `drafts/filter-builders-and-composition/filter-composition/requirements.md`
- `drafts/filter-builders-and-composition/filter-composition/implementation-plan.md`
- `drafts/filter-builders-and-composition/drawtext-builder/requirements.md`
- `drafts/filter-builders-and-composition/drawtext-builder/implementation-plan.md`
- `drafts/filter-builders-and-composition/speed-control/requirements.md`
- `drafts/filter-builders-and-composition/speed-control/implementation-plan.md`

### Theme 03: effects-api-layer (BL-042, BL-043)
- `drafts/effects-api-layer/THEME_DESIGN.md`
- `drafts/effects-api-layer/effect-discovery/requirements.md`
- `drafts/effects-api-layer/effect-discovery/implementation-plan.md`
- `drafts/effects-api-layer/clip-effect-model/requirements.md`
- `drafts/effects-api-layer/clip-effect-model/implementation-plan.md`
- `drafts/effects-api-layer/text-overlay-apply/requirements.md`
- `drafts/effects-api-layer/text-overlay-apply/implementation-plan.md`

**Total: 22 documents** (1 manifest + 2 version-level + 3 theme designs + 9 requirements + 9 implementation plans) plus this README and the draft-checklist.

## Reference Pattern

All documents follow a lean reference pattern — they state design decisions and requirements concisely, then reference the artifact store for details:
- Risk analysis: `See comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`
- Research evidence: `See comms/outbox/versions/design/v006/004-research/`
- Test strategy: `See comms/outbox/versions/design/v006/005-logical-design/test-strategy.md`
- Environment context: `See comms/outbox/versions/design/v006/001-environment/version-context.md`

## Completeness Check

All 7 backlog items are covered:

| Backlog ID | Feature(s) | Theme |
|------------|-----------|-------|
| BL-037 | expression-engine | 01-filter-expression-infrastructure |
| BL-038 | graph-validation | 01-filter-expression-infrastructure |
| BL-039 | filter-composition | 02-filter-builders-and-composition |
| BL-040 | drawtext-builder | 02-filter-builders-and-composition |
| BL-041 | speed-control | 02-filter-builders-and-composition |
| BL-042 | effect-discovery | 03-effects-api-layer |
| BL-043 | clip-effect-model + text-overlay-apply | 03-effects-api-layer |

No backlog items deferred. No descoping.

## Format Verification

- THEME_INDEX.md feature lines match parser regex `- (\d+)-([\w-]+):`
- No numbered lists, bold identifiers, or metadata before colon in feature lines
- No theme or feature slug starts with a digit prefix
- manifest.json validates as JSON with all required fields
- All "Files to Modify" paths in implementation plans verified against codebase via Glob
