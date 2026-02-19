# Logical Design - v007 Effect Workshop GUI

## Version Overview

**Version**: v007
**Title**: Effect Workshop GUI
**Milestones**: M2.4-2.6, M2.8-2.9

**Goals**: Complete remaining effect types (audio mixing, transitions), build the effect registry with JSON schema validation and registry-based dispatch, and construct the full GUI effect workshop with catalog UI, parameter forms, and live preview.

**Scope**: 9 backlog items (BL-044 through BL-052), organized into 4 themes with 11 features total (9 backlog + 2 documentation).

---

## Theme 01: 01-rust-filter-builders

**Goal**: Implement Rust filter builders for audio mixing and video transitions, extending the proven v006 builder pattern to two new effect domains. These builders provide the type-safe foundation that the effect registry and GUI consume.

**Backlog Items**: BL-044, BL-045

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-audio-mixing-builders | Build AmixBuilder, VolumeBuilder, AfadeBuilder, and DuckingPattern in Rust with PyO3 bindings | BL-044 | None (v006 complete) |
| 2 | 002-transition-filter-builders | Build FadeBuilder, XfadeBuilder with TransitionType enum and acrossfade support in Rust with PyO3 bindings | BL-045 | None (v006 complete) |

**Rationale**: Audio first because amix/volume/afade are simpler single-input filters (except amix) that establish the template for the more complex two-input transition builders (LRN-028). Both features follow the identical Rust builder -> PyO3 bindings -> type stubs -> Python tests template validated across 5 v006 features. No dependency between the two features; audio is ordered first per research recommendation.

---

## Theme 02: 02-effect-registry-api

**Goal**: Refactor the effect registry to use builder-protocol dispatch (replacing if/elif), add JSON schema validation, create the transition API endpoint, and document the architectural changes. This theme is the architectural centerpiece connecting Rust builders to the GUI.

**Backlog Items**: BL-046, BL-047

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-effect-registry-refactor | Add build_fn to EffectDefinition, replace _build_filter_string() dispatch with registry lookup, add JSON schema validation and Prometheus metrics | BL-047 | T01 (all Rust builders registered) |
| 2 | 002-transition-api-endpoint | Create POST /effects/transition endpoint with clip adjacency validation and persistent storage | BL-046 | T02-F001 (registry dispatch) |
| 3 | 003-architecture-documentation | Update docs/design/02-architecture.md and 05-api-specification.md to reflect registry refactoring, new endpoints, and effect type additions | None (LRN-030) | T02-F001, T02-F002 |

**Rationale**: Registry refactoring must happen before the transition endpoint so the new endpoint uses registry-based dispatch from the start (avoiding adding to the deprecated if/elif). The documentation feature follows LRN-030 (architecture docs as explicit feature) and reconciles design specs with implementation after the structural changes.

---

## Theme 03: 03-effect-workshop-gui

**Goal**: Build the complete Effect Workshop GUI: a catalog for browsing effects, a schema-driven parameter form generator, live FFmpeg filter string preview, and the full effect builder workflow with clip selection, effect stack management, and CRUD operations.

**Backlog Items**: BL-048, BL-049, BL-050, BL-051

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-effect-catalog-ui | Build grid/list view of available effects with search, filter, and AI hint tooltips | BL-048 | T02 (registry provides effect discovery data) |
| 2 | 002-dynamic-parameter-forms | Build schema-driven form generator supporting number/range, string, enum, boolean, and color picker inputs with validation | BL-049 | T03-F001 (catalog selects an effect) |
| 3 | 003-live-filter-preview | Build debounced filter string preview panel with syntax highlighting and copy-to-clipboard | BL-050 | T03-F002 (form provides parameter values) |
| 4 | 004-effect-builder-workflow | Compose catalog, form, and preview into full workflow with clip selector, effect stack visualization, and effect CRUD (edit/remove) | BL-051 | T03-F001, T03-F002, T03-F003 |

**Rationale**: Sequential build-up from simple to complex. Each component is independently testable but builds on the previous. The catalog is the entry point; forms consume catalog selection; preview consumes form state; workflow composes all three. Effect CRUD endpoints (PATCH/DELETE) needed by F004 are added as part of that feature's backend work. Follows LRN-024 (focused Zustand stores per domain).

---

## Theme 04: 04-quality-validation

**Goal**: Validate the complete effect workshop through end-to-end testing with accessibility compliance, and update API specification documentation to reflect all new endpoints.

**Backlog Items**: BL-052

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-e2e-effect-workshop-tests | E2E tests covering catalog browse, parameter config, preview, apply/edit/remove effects, and WCAG AA accessibility | BL-052 | T03 (all GUI components) |
| 2 | 002-api-specification-update | Update OpenAPI spec and docs/design/05-api-specification.md with transition, preview, and CRUD endpoints | None (impact analysis) | T02, T03-F004 |

**Rationale**: E2E tests require all components to be complete. API documentation consolidates all endpoint additions from themes 02 and 03. Placing docs here ensures they capture the final API surface. Uses existing Playwright + axe-core infrastructure (LRN-022).

---

## Execution Order

### Theme Dependencies

```
T01 (Rust Builders) ──→ T02 (Registry & API) ──→ T03 (GUI Workshop) ──→ T04 (Quality)
```

Strictly sequential. Each theme depends on the previous theme's output:
- T02 needs Rust builders to register in the effect registry
- T03 needs the registry API to drive catalog and form generation
- T04 needs all GUI components for E2E testing

### Feature Dependencies Within Themes

**T01**: F001 (audio) -> F002 (transitions). No hard dependency, but audio first sets the template.

**T02**: F001 (registry) -> F002 (transition API) -> F003 (docs). Sequential — registry dispatch must exist before adding new endpoints; docs capture final state.

**T03**: F001 (catalog) -> F002 (forms) -> F003 (preview) -> F004 (workflow). Sequential build-up; each component consumed by the next.

**T04**: F001 (E2E) and F002 (API docs) are independent; can execute in either order.

### Rationale

This ordering follows the validated infrastructure-first pattern from v006 (LRN-019): Rust infrastructure -> Python orchestration -> Frontend consumption -> Quality validation. v006 achieved 100% first-iteration success with this sequencing.

---

## Research Sources Adopted

| Decision | Source | Reference |
|----------|--------|-----------|
| Audio builder parameters (amix, volume, afade, sidechaincompress) | FFmpeg documentation | `004-research/external-research.md` |
| Transition types (64 xfade variants) | FFmpeg documentation | `004-research/external-research.md` |
| Volume range 0.0-10.0 | Existing validate_volume | `004-research/evidence-log.md` |
| xfade duration 0.0-60.0 | FFmpeg documentation | `004-research/evidence-log.md` |
| Builder pattern reuse (PyRefMut chaining) | v006 template, LRN-001, LRN-028 | `004-research/codebase-patterns.md` |
| Registry refactoring: build_fn on EffectDefinition | v006 tech debt trigger | `004-research/codebase-patterns.md` |
| Custom form generator (not RJSF) | Research evaluation | `004-research/external-research.md` |
| Debounce interval 300ms | Existing useDebounce hook | `004-research/evidence-log.md` |
| Simple regex syntax highlighting (no FFmpeg library) | Research evaluation | `004-research/external-research.md` |
| Effect CRUD via array index | Current storage format | `004-research/evidence-log.md` |
| Focused Zustand stores | LRN-024 | `002-backlog/learnings-summary.md` |
| Prometheus counter naming | Existing metrics convention | `004-research/evidence-log.md` |
| Preview thumbnails deferred | Research recommendation | `004-research/external-research.md` |
