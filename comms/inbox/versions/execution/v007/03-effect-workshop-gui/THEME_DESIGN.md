# Theme: effect-workshop-gui

## Goal

Build the complete Effect Workshop GUI: a catalog for browsing effects, a schema-driven parameter form generator, live FFmpeg filter string preview, and the full effect builder workflow with clip selection, effect stack management, and CRUD operations.

## Design Artifacts

See `comms/outbox/versions/design/v007/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | effect-catalog-ui | BL-048 | Build grid/list view of available effects with search, filter, and AI hint tooltips |
| 002 | dynamic-parameter-forms | BL-049 | Build schema-driven form generator supporting number/range, string, enum, boolean, and color picker inputs with validation |
| 003 | live-filter-preview | BL-050 | Build debounced filter string preview panel with syntax highlighting and copy-to-clipboard |
| 004 | effect-builder-workflow | BL-051 | Compose catalog, form, and preview into full workflow with clip selector, effect stack visualization, and effect CRUD |

## Dependencies

- T02 complete: registry provides effect discovery data, JSON schemas, and builder dispatch
- Existing GET /effects discovery endpoint from v006
- Existing Zustand store pattern (projectStore, libraryStore, activityStore)
- Existing custom hooks pattern (useProjects, useHealth, useDebounce)
- Existing React Router with /gui basename

## Technical Approach

Sequential build-up from simple to complex. Each component is independently testable but builds on the previous:

1. **Catalog** (F001): Grid/list view consuming GET /effects. New `effectCatalogStore` for search/filter/selection state. `useEffects` hook following `useProjects` pattern.
2. **Forms** (F002): Custom lightweight form generator reading JSON schema from registry. Handles number/range, string, enum, boolean, color picker. New `effectFormStore` for parameter/validation state.
3. **Preview** (F003): Debounced API call (300ms) showing filter string in monospace panel. Simple regex-based syntax highlighting for filter names and pad labels. Copy-to-clipboard. New `effectPreviewStore`.
4. **Workflow** (F004): Composes all components. ClipSelector, EffectStack visualization, effect CRUD via PATCH/DELETE by array index. EffectsPage as composition root. New `effectStackStore`.

See `comms/outbox/versions/design/v007/004-research/codebase-patterns.md` for GUI patterns and `004-research/external-research.md` for form generation approach.

## Risks

| Risk | Mitigation |
|------|------------|
| Preview thumbnails deferred | Filter string preview satisfies transparency intent. Placeholder notes future enhancement. See 006-critical-thinking/risk-assessment.md |
| Effect CRUD via array index | Sufficient for single-user v007 scope. UUID-based IDs documented as upgrade path. See 006-critical-thinking/risk-assessment.md |
| Custom form generator vs RJSF | Custom handles 5-6 types. RJSF documented as upgrade path. See 006-critical-thinking/risk-assessment.md |