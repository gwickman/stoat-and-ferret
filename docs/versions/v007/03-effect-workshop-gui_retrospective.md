# Theme 03: effect-workshop-gui Retrospective

## Summary

Built the complete Effect Workshop GUI: an effect catalog for browsing and selecting effects, a schema-driven parameter form generator, live FFmpeg filter string preview with syntax highlighting, and the full effect builder workflow with clip selection, effect stack management, and CRUD operations. All 4 features shipped with 49/49 acceptance criteria passing and all primary quality gates green. Two features (002, 003) had PRs blocked by a pre-existing flaky E2E test (BL-055) unrelated to the theme.

## Deliverables

| Feature | Status | Acceptance | Quality Gates | Notes |
|---------|--------|------------|---------------|-------|
| 001-effect-catalog-ui | Complete | 14/14 | ruff, mypy, pytest, tsc, vitest — all pass | Grid/list view, search, category filter, AI hint tooltips, selection |
| 002-dynamic-parameter-forms | Complete | 12/12 | ruff, mypy, pytest, tsc, vitest — all pass | Schema-driven form generator with 5 input widget types; CI E2E fail pre-existing |
| 003-live-filter-preview | Complete | 10/10 | ruff, mypy, pytest, tsc, vitest — all pass | Debounced preview API, regex syntax highlighting, copy-to-clipboard; CI E2E fail pre-existing |
| 004-effect-builder-workflow | Complete | 13/13 | ruff, mypy, pytest, tsc, vitest — all pass | Clip selector, effect stack, PATCH/DELETE CRUD endpoints |

## Metrics

- **PRs:** 4 (#87, #88, #89, #90)
- **New frontend components:** 5 (EffectCatalog, EffectParameterForm, FilterPreview, ClipSelector, EffectStack)
- **New Zustand stores:** 4 (effectCatalogStore, effectFormStore, effectPreviewStore, effectStackStore)
- **New backend endpoints:** 3 (POST /effects/preview, PATCH /effects/{index}, DELETE /effects/{index})
- **Frontend tests added:** 52 (16 + 17 + 14 + 11 across vitest — 101 to 143 total)
- **Backend tests added:** 13 (CRUD, contract, golden workflow tests)
- **Total vitest suite:** 143 tests at theme completion
- **Total pytest suite:** 864 passed, 91.45% coverage at theme completion

## Key Decisions

### Schema-driven form generation via dispatcher component
**Context:** The parameter form needed to render different input widgets based on JSON schema property types, supporting number, string, enum, boolean, and color picker inputs.
**Choice:** A `SchemaField` dispatcher component routes each schema property to a typed sub-component based on `type` and `format` fields. The Zustand store holds parameter values, validation errors, and dirty state.
**Outcome:** Clean separation of concerns — adding a new widget type requires only a new sub-component and a case in the dispatcher. Defaults populated from schema `default` values.

### Category derivation from effect_type
**Context:** The API does not include an explicit `category` field on effects, but the catalog UI needs category filtering.
**Choice:** Isolated `deriveCategory()` pure function maps `effect_type` string patterns to categories (audio/video/transition) client-side.
**Outcome:** Avoids API schema changes while providing category filtering. Easy to adjust mapping logic if new effect types are added.

### Debounced preview with dedicated endpoint
**Context:** Live filter string preview requires an API call on every parameter change, which could overwhelm the backend.
**Choice:** 300ms debounce via existing `useDebounce` hook. New `POST /effects/preview` endpoint requires no project/clip context — takes `{effect_type, parameters}` and returns `{filter_string}`.
**Outcome:** Responsive feel without API flooding. The lightweight preview endpoint validates and builds without side effects.

### Array-index-based CRUD for effects
**Context:** Effects are stored as arrays on clips. Need to support edit and remove operations on individual effects.
**Choice:** PATCH/DELETE endpoints use array index as the identifier (`/effects/{index}`). Invalid indices return 404.
**Outcome:** Simple and predictable API. No need for effect UUIDs at this stage since effects are always accessed in the context of their parent clip.

## Learnings

### What Went Well
- Consistent Zustand store pattern (4 new stores) made state management predictable across all features — each store follows the same create/selector/action shape established in earlier themes
- Schema-driven rendering proved highly testable — each widget type is a pure function of its schema definition, enabling isolated unit tests
- Feature composition in 004 was smooth because each prior feature (catalog, form, preview) was designed as a standalone component with clean store interfaces
- Regex-based syntax highlighting for filter strings was a lightweight alternative to pulling in a syntax highlighting library, keeping bundle size small
- Backend parity between PATCH/DELETE endpoints and existing POST pattern (same validation, same error codes) reduced implementation effort and test boilerplate

### What Could Improve
- Pre-existing flaky E2E test (BL-055 — `project-creation.spec.ts`) blocked PR merges for features 002 and 003, adding friction to the workflow. This was investigated across multiple CI retries and timeout increases without resolution
- The EffectsPage component grew into a large orchestrator as features were added sequentially — it could benefit from extracting workflow state into a dedicated hook or splitting into sub-pages
- No visual preview of FFmpeg output yet — the "Visual preview coming in a future version" placeholder is an expected gap but worth tracking

## Technical Debt

### Pre-existing E2E Flaky Test (BL-055)
**Source:** 002, 003 quality-gaps.md
**Issue:** `gui/e2e/project-creation.spec.ts:31` — `toBeHidden` assertion on create-project-modal times out because `POST /api/v1/projects` fails in the CI E2E environment. Fails on `main` as well (run 22188785818). Not a timing issue — increasing timeout to 10s had no effect.
**Impact:** Blocks PR merge for any feature touching the GUI. Does not affect correctness of the effect workshop features.
**Recommendation:** Investigate why the projects POST endpoint fails consistently in the E2E CI environment. May need mock server configuration or environment variable fixes.

### EffectsPage Orchestrator Complexity
**Source:** Theme observation
**Issue:** `gui/src/pages/EffectsPage.tsx` orchestrates catalog, form, preview, clip selector, and effect stack. As more workflow steps are added, this file will become harder to maintain.
**Recommendation:** Consider extracting an `useEffectWorkflow` hook or splitting into sub-route pages (e.g., `/effects/browse`, `/effects/build`).

### Large definitions.py (carried from Theme 02)
**Source:** Theme 02 retrospective
**Issue:** All effect build functions and schemas in a single file. Theme 03 added preview/CRUD endpoints that further depend on this module.
**Recommendation:** Split into domain modules when effect count grows beyond current 9.

## Recommendations

1. **Fix BL-055 before next GUI theme:** The flaky E2E test is a systemic blocker for all GUI PRs. Prioritize investigating the CI project-creation endpoint failure.
2. **EffectsPage refactoring:** Before adding visual preview or more workflow steps, extract the orchestration logic to keep the page component manageable.
3. **Store consolidation opportunity:** With 4 effect-related Zustand stores, consider whether `effectFormStore` and `effectPreviewStore` could be merged since preview depends directly on form state — but only if complexity warrants it.
4. **Visual preview as next milestone:** The placeholder for visual FFmpeg output preview is a natural follow-up. Will likely require a backend render/thumbnail endpoint.
