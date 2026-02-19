# Refined Logical Design - v007 Effect Workshop GUI

## Version Overview

**Version**: v007
**Title**: Effect Workshop GUI
**Milestones**: M2.4-2.6, M2.8-2.9

**Goals**: Complete remaining effect types (audio mixing, transitions), build the effect registry with JSON schema validation and registry-based dispatch, and construct the full GUI effect workshop with catalog UI, parameter forms, and live preview.

**Scope**: 9 backlog items (BL-044 through BL-052), organized into 4 themes with 11 features total (9 backlog + 2 documentation).

**Changes from Task 005**: No structural changes to theme groupings, feature ordering, or execution order. Three design clarifications based on risk investigation (see risk-assessment.md for details).

---

## Theme 01: 01-rust-filter-builders

**Goal**: Implement Rust filter builders for audio mixing and video transitions, extending the proven v006 builder pattern to two new effect domains.

**Backlog Items**: BL-044, BL-045

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-audio-mixing-builders | Build AmixBuilder, VolumeBuilder, AfadeBuilder, and DuckingPattern in Rust with PyO3 bindings | BL-044 | None (v006 complete) |
| 2 | 002-transition-filter-builders | Build FadeBuilder, XfadeBuilder with TransitionType enum and AcrossfadeBuilder in Rust with PyO3 bindings | BL-045 | None (v006 complete) |

**Design clarifications from risk investigation**:
- **DuckingPattern**: Implemented as a builder that constructs a FilterGraph using the composition API (compose_branch for asplit, compose_chain for sidechaincompress, compose_merge for amerge), not a single FilterChain. See risk-assessment.md "Audio Ducking Composite Pattern."
- **Two-input filters** (xfade, acrossfade): Use `FilterChain::new().input(label1).input(label2).filter(...)` pattern, already proven through concat tests. See risk-assessment.md "Two-Input Filter Pattern."
- **Coverage tracking**: Measure Rust coverage before and after T01 to track progress toward 90% target.

---

## Theme 02: 02-effect-registry-api

**Goal**: Refactor the effect registry to use builder-protocol dispatch, add JSON schema validation, create the transition API endpoint, and document architectural changes.

**Backlog Items**: BL-046, BL-047

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-effect-registry-refactor | Add build_fn to EffectDefinition, replace _build_filter_string() dispatch with registry lookup, add JSON schema validation and Prometheus metrics | BL-047 | T01 (all Rust builders registered) |
| 2 | 002-transition-api-endpoint | Create POST /effects/transition endpoint with clip adjacency validation and persistent storage | BL-046 | T02-F001 (registry dispatch) |
| 3 | 003-architecture-documentation | Update docs/design/02-architecture.md and 05-api-specification.md to reflect registry refactoring, new endpoints, and effect type additions | None (LRN-030) | T02-F001, T02-F002 |

**Design clarifications from risk investigation**:
- **Registry refactoring scope**: Only 2 branches in `_build_filter_string()` (text_overlay, speed_control). Add `build_fn: Callable[[dict[str, Any]], str]` to EffectDefinition. Move per-effect build logic into callables. Replace if/elif with `definition.build_fn(parameters)`. See risk-assessment.md "Registry Refactoring Scope."
- **Parity tests**: Required for text_overlay and speed_control filter string output before/after refactoring.
- **mypy baseline**: Run mypy at start of T02-F001, record error count. New code must not increase count.
- **Prometheus counter**: `effect_applications_total` with `["effect_type"]` label, following existing `http_requests_total` pattern.

---

## Theme 03: 03-effect-workshop-gui

**Goal**: Build the complete Effect Workshop GUI: catalog, schema-driven forms, live preview, and full builder workflow.

**Backlog Items**: BL-048, BL-049, BL-050, BL-051

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-effect-catalog-ui | Build grid/list view of available effects with search, filter, and AI hint tooltips | BL-048 | T02 (registry provides effect discovery data) |
| 2 | 002-dynamic-parameter-forms | Build schema-driven form generator supporting number/range, string, enum, boolean, and color picker inputs with validation | BL-049 | T03-F001 (catalog selects an effect) |
| 3 | 003-live-filter-preview | Build debounced filter string preview panel with syntax highlighting and copy-to-clipboard | BL-050 | T03-F002 (form provides parameter values) |
| 4 | 004-effect-builder-workflow | Compose catalog, form, and preview into full workflow with clip selector, effect stack visualization, and effect CRUD (edit/remove) | BL-051 | T03-F001, T03-F002, T03-F003 |

**Design clarifications from risk investigation**:
- **BL-051 AC #3** ("Preview thumbnail"): Implemented as a filter string preview panel showing the generated FFmpeg command, not a rendered thumbnail. This satisfies the transparency intent. Rendered thumbnails documented as future enhancement. See risk-assessment.md "Preview Thumbnails Deferred."
- **Effect CRUD**: PATCH/DELETE endpoints use array index (0-based). Index validated against effects array length; out-of-range returns 404. Sufficient for single-user v007 scope. UUID-based IDs documented as upgrade path.
- **Custom form generator**: Handles 5-6 parameter types (number, string, enum, boolean, color). RJSF documented as upgrade path if complexity grows.

---

## Theme 04: 04-quality-validation

**Goal**: Validate the complete effect workshop through E2E testing with accessibility compliance and update API specification documentation.

**Backlog Items**: BL-052

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-e2e-effect-workshop-tests | E2E tests covering catalog browse, parameter config, preview, apply/edit/remove effects, and WCAG AA accessibility | BL-052 | T03 (all GUI components) |
| 2 | 002-api-specification-update | Update OpenAPI spec and docs/design/05-api-specification.md with transition, preview, and CRUD endpoints | None (impact analysis) | T02, T03-F004 |

**Design clarification from risk investigation**:
- **SPA fallback**: Remains deferred. E2E tests navigate via client-side routing (LRN-023). Document as known limitation in API specification update.

---

## Execution Order

```
T01 (Rust Builders) --> T02 (Registry & API) --> T03 (GUI Workshop) --> T04 (Quality)
```

**No changes from Task 005.** Strictly sequential. The risk investigation confirmed all dependencies are valid and no circular dependencies exist.

---

## Backlog Coverage Verification

All 9 mandatory backlog items mapped:

| Backlog | Theme | Feature | Status |
|---------|-------|---------|--------|
| BL-044 | T01 | F001 audio-mixing-builders | Covered |
| BL-045 | T01 | F002 transition-filter-builders | Covered |
| BL-046 | T02 | F002 transition-api-endpoint | Covered |
| BL-047 | T02 | F001 effect-registry-refactor | Covered |
| BL-048 | T03 | F001 effect-catalog-ui | Covered |
| BL-049 | T03 | F002 dynamic-parameter-forms | Covered |
| BL-050 | T03 | F003 live-filter-preview | Covered |
| BL-051 | T03 | F004 effect-builder-workflow | Covered |
| BL-052 | T04 | F001 e2e-effect-workshop-tests | Covered |

No deferrals. No descoping. All items retained from Task 005.

---

## Test Strategy Updates

Additions from risk investigation:

1. **T01-F001**: Add FilterGraph composition test for DuckingPattern (compose_branch + compose_chain + compose_merge integration)
2. **T02-F001**: Add parity tests comparing filter string output before/after registry refactoring for text_overlay and speed_control
3. **T02-F001**: Add mypy baseline verification (error count must not increase)
4. **T01**: Add Rust coverage measurement before/after theme completion

These additions do not change the test count materially (~4 additional tests across T01 and T02).
