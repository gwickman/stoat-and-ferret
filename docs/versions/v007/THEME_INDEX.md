# v007 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: rust-filter-builders

**Path:** `comms/inbox/versions/execution/v007/01-rust-filter-builders/`
**Goal:** Implement Rust filter builders for audio mixing and video transitions, extending the proven v006 builder pattern (LRN-028) to two new effect domains. These builders provide the type-safe foundation that the effect registry and GUI consume.

**Features:**

- 001-audio-mixing-builders: Build AmixBuilder, VolumeBuilder, AfadeBuilder, and DuckingPattern in Rust with PyO3 bindings
- 002-transition-filter-builders: Build FadeBuilder, XfadeBuilder with TransitionType enum and AcrossfadeBuilder in Rust with PyO3 bindings
### Theme 02: effect-registry-api

**Path:** `comms/inbox/versions/execution/v007/02-effect-registry-api/`
**Goal:** Refactor the effect registry to use builder-protocol dispatch (replacing if/elif), add JSON schema validation, create the transition API endpoint, and document the architectural changes. This theme is the architectural centerpiece connecting Rust builders to the GUI.

**Features:**

- 001-effect-registry-refactor: Add build_fn to EffectDefinition, replace _build_filter_string() dispatch with registry lookup, add JSON schema validation and Prometheus metrics
- 002-transition-api-endpoint: Create POST /effects/transition endpoint with clip adjacency validation and persistent storage
- 003-architecture-documentation: Update docs/design/02-architecture.md and 05-api-specification.md to reflect registry refactoring, new endpoints, and effect type additions
### Theme 03: effect-workshop-gui

**Path:** `comms/inbox/versions/execution/v007/03-effect-workshop-gui/`
**Goal:** Build the complete Effect Workshop GUI: a catalog for browsing effects, a schema-driven parameter form generator, live FFmpeg filter string preview, and the full effect builder workflow with clip selection, effect stack management, and CRUD operations.

**Features:**

- 001-effect-catalog-ui: Build grid/list view of available effects with search, filter, and AI hint tooltips
- 002-dynamic-parameter-forms: Build schema-driven form generator supporting number/range, string, enum, boolean, and color picker inputs with validation
- 003-live-filter-preview: Build debounced filter string preview panel with syntax highlighting and copy-to-clipboard
- 004-effect-builder-workflow: Compose catalog, form, and preview into full workflow with clip selector, effect stack visualization, and effect CRUD (edit/remove)
### Theme 04: quality-validation

**Path:** `comms/inbox/versions/execution/v007/04-quality-validation/`
**Goal:** Validate the complete effect workshop through end-to-end testing with accessibility compliance, and update API specification documentation to reflect all new endpoints added in v007.

**Features:**

- 001-e2e-effect-workshop-tests: E2E tests covering catalog browse, parameter config, preview, apply/edit/remove effects, and WCAG AA accessibility
- 002-api-specification-update: Update OpenAPI spec and docs/design/05-api-specification.md with transition, preview, and CRUD endpoints
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
