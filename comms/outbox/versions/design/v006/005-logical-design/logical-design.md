# Logical Design Proposal: v006 — Effects Engine Foundation

## Version Overview

**Version:** v006
**Description:** Effects Engine Foundation — Build the Rust filter expression engine, graph validation, filter composition, text overlay builder, speed control, and effect discovery/application API endpoints.

**Goals:**
- Establish a type-safe FFmpeg filter expression DSL in Rust (M2.1)
- Implement graph validation and composition system for complex filter chains (M2.1)
- Build drawtext and speed control filter builders (M2.2, M2.3)
- Bridge Rust effects engine to Python API with discovery and application endpoints

**Scope:** 7 backlog items (BL-037–BL-043), 3 themes, 9 features total.

---

## Theme 01: `01-filter-expression-infrastructure`

**Goal:** Build the foundational Rust infrastructure that all other v006 features depend on — a type-safe expression engine for FFmpeg filter expressions and a graph validation system for verifying filter graph correctness before serialization. These two independent subsystems form the base layer of the effects engine.

**Backlog Items:** BL-037, BL-038

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | `001-expression-engine` | Implement type-safe FFmpeg expression AST with builder API, serialization, and property-based tests | BL-037 | None |
| 2 | `002-graph-validation` | Add pad matching validation, unconnected pad detection, and cycle detection to FilterGraph | BL-038 | None |

**Rationale:** BL-037 and BL-038 are both independent starting points with no upstream dependencies. They are infrastructure consumed by everything else (LRN-019: build infrastructure first). Grouping them lets Theme 01 execute with maximum parallelism — neither feature blocks the other. Both are pure Rust with PyO3 bindings (incremental binding rule).

### Feature 001-expression-engine (BL-037)

**Goal:** Implement a Rust expression AST covering enable, alpha, time, and arithmetic FFmpeg expressions with a fluent builder API (LRN-001: `PyRefMut` chaining), serialization to valid FFmpeg syntax, property-based tests via proptest, and PyO3 bindings with type stubs.

**Key design decisions:**
- Expression function names validated against whitelist of known FFmpeg functions (LRN-003)
- Builder uses `PyRefMut<'_, Self>` for method chaining (LRN-001)
- Rust owns expression construction and validation; Python consumes via bindings (LRN-011)

### Feature 002-graph-validation (BL-038)

**Goal:** Add validation to the existing `FilterGraph` type: pad label matching (output feeds correct input), unconnected pad detection with specific pad names, cycle detection via topological sort, and actionable error messages.

**Key design decisions:**
- Extends existing `FilterGraph` rather than creating a new type
- Validation runs automatically before serialization
- Error messages include guidance on how to fix the graph (per AC4)

---

## Theme 02: `02-filter-builders-and-composition`

**Goal:** Build the concrete filter builders (drawtext for text overlays, speed control for setpts/atempo) and the composition system for chaining, branching, and merging filter graphs. These features consume Theme 01's infrastructure and produce the Rust-side building blocks that the API layer needs.

**Backlog Items:** BL-039, BL-040, BL-041

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | `001-filter-composition` | Build chain/branch/merge composition API with automatic pad management and validation | BL-039 | Theme 01 Feature 002 (graph validation) |
| 2 | `002-drawtext-builder` | Implement drawtext filter builder with position, styling, alpha animation, and contract tests | BL-040 | Theme 01 Feature 001 (expression engine) |
| 3 | `003-speed-control` | Implement setpts/atempo builders with automatic atempo chaining for >2x speeds | BL-041 | None (within theme) |

**Rationale:** These three features all produce Rust filter builders that the API layer (Theme 03) will consume. BL-039 depends on BL-038 (composition needs graph validation). BL-040 depends on BL-037 (drawtext alpha animation uses expression engine). BL-041 is independent — it uses simple PTS expressions, not the expression engine. Grouping keeps all Rust builder work in one theme, with clear intra-theme ordering: composition first (needed by drawtext contract tests), then drawtext and speed control (which can proceed in sequence).

### Feature 001-filter-composition (BL-039)

**Goal:** Implement chain (sequential filters on one stream), branch (split one stream into multiple), and merge (combine streams via overlay/amix/concat) composition modes with automatic pad label management and automatic validation of composed graphs.

**Key design decisions:**
- Composition automatically manages pad labels (no manual label assignment)
- Composed graphs validated automatically via Theme 01's graph validation
- Builder API uses `PyRefMut` chaining pattern (LRN-001)

### Feature 002-drawtext-builder (BL-040)

**Goal:** Build a structured drawtext filter builder supporting absolute/centered/margin-based positioning, font/color/shadow/box styling, fade in/out alpha animation via expression engine, with contract tests verifying generated filters pass `ffmpeg -filter_complex` validation.

**Key design decisions:**
- Alpha animation uses expression engine from Theme 01 Feature 001
- Contract tests leverage record-replay pattern (LRN-008) on single CI matrix entry (LRN-015)
- Builder pattern with PyO3 bindings and type stubs (incremental binding rule)

### Feature 003-speed-control (BL-041)

**Goal:** Implement setpts (video speed) and atempo (audio speed) builders with 0.25x–4.0x range, automatic atempo chaining for >2x factors, audio drop option, and validation of out-of-range values.

**Key design decisions:**
- Atempo auto-chaining: factors >2x decomposed into chained atempo filters (FFmpeg limitation)
- Independent of expression engine (uses simple `PTS/factor` expression)
- Well-bounded scope — medium complexity compared to other features

---

## Theme 03: `03-effects-api-layer`

**Goal:** Bridge the Rust effects engine to the Python API layer. Create the effect discovery endpoint with registry pattern and parameter schemas, and the text overlay application endpoint with clip model extension for effect storage. This theme transitions from Rust-side construction to Python-side orchestration.

**Backlog Items:** BL-042, BL-043

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | `001-effect-discovery` | Create GET /effects endpoint with registry service, parameter JSON schemas, and AI hints | BL-042 | Theme 02 Features 002, 003 (drawtext + speed control registered as effects) |
| 2 | `002-clip-effect-model` | Extend clip data model with effects storage across Python schema, DB repository, and Rust type | BL-043 (partial) | Feature 001 (discovery, for effect registration pattern) |
| 3 | `003-text-overlay-apply` | Create POST endpoint to apply text overlay to clips with validation, persistence, and filter preview | BL-043 (partial) | Feature 002 (clip effects model) |

**Rationale:** BL-042 and BL-043 are the Python-side API features. BL-043 is split into two features because the impact assessment identified clip effects model design as a substantial impact requiring dedicated work (impact #9). Feature 002 handles the multi-layer schema change, and Feature 003 builds the endpoint on top. BL-042 comes first because the effect registry pattern informs how effects are registered and stored. The 3-feature split within this theme keeps each feature focused and testable.

### Feature 001-effect-discovery (BL-042)

**Goal:** Implement `GET /effects` returning available effects with name, description, parameter JSON schemas, and AI hints. Design the effect registry service with DI via `create_app()` kwargs (LRN-005). Register text overlay (from BL-040) and speed control (from BL-041) as discoverable effects. Include Rust-generated filter preview for default parameters.

**Key design decisions:**
- Effect registry as a Python service with DI (substantial impact #13)
- Extensible pattern for v007 effects (designed upfront per impact assessment recommendation)
- JSON schema generation for effect parameters enables dynamic GUI forms
- Server-side sorting for effect listing from the start (per retrospective insight)

### Feature 002-clip-effect-model (BL-043, partial)

**Goal:** Extend the clip data model to support an effects list. Add `effects` field to Python Pydantic schema, DB repository storage, and optionally Rust `Clip` type. Design the effect configuration storage format.

**Key design decisions:**
- Multi-layer schema change: Pydantic model, DB repository, potentially Rust Clip (substantial impact #9)
- Effect configuration format aligned with registry schema from Feature 001
- May need DB migration for persisted clip data

### Feature 003-text-overlay-apply (BL-043, partial)

**Goal:** Implement POST endpoint to apply text overlay parameters to a clip, validate via Rust drawtext builder, store effect configuration in clip model, return generated FFmpeg filter string, and emit WebSocket events.

**Key design decisions:**
- Validation errors from Rust surface as structured API error responses
- Response includes FFmpeg filter string for transparency (architectural principle)
- WebSocket events (`effect.applied`, `effect.removed`) for real-time updates (impact #14)
- Black box test covers apply → verify filter string flow (AC5)

---

## Execution Order

### Theme Dependencies

```
Theme 01 (filter-expression-infrastructure)
    ├── Feature 001-expression-engine ──→ Theme 02 Feature 002 (drawtext)
    └── Feature 002-graph-validation ──→ Theme 02 Feature 001 (composition)

Theme 02 (filter-builders-and-composition)
    ├── Feature 002-drawtext-builder ──→ Theme 03 Feature 001 (discovery)
    └── Feature 003-speed-control ────→ Theme 03 Feature 001 (discovery)

Theme 03 (effects-api-layer)
    ├── Feature 001-effect-discovery
    ├── Feature 002-clip-effect-model (depends on Feature 001)
    └── Feature 003-text-overlay-apply (depends on Feature 002)
```

### Execution Sequence

1. **Theme 01, Feature 001**: expression-engine (BL-037) — no dependencies
2. **Theme 01, Feature 002**: graph-validation (BL-038) — no dependencies (parallel with F001)
3. **Theme 02, Feature 001**: filter-composition (BL-039) — needs Theme 01 F002
4. **Theme 02, Feature 002**: drawtext-builder (BL-040) — needs Theme 01 F001
5. **Theme 02, Feature 003**: speed-control (BL-041) — independent, sequenced after F002 for handoff
6. **Theme 03, Feature 001**: effect-discovery (BL-042) — needs Theme 02 F002 + F003
7. **Theme 03, Feature 002**: clip-effect-model (BL-043 partial) — needs Theme 03 F001
8. **Theme 03, Feature 003**: text-overlay-apply (BL-043 partial) — needs Theme 03 F002

**Rationale:** Follows LRN-019 (infrastructure first). Theme 01 has no internal ordering constraint — both features are independent. Theme 02 sequences composition first (provides composition API that drawtext contract tests may use), then drawtext, then speed control. Theme 03 sequences discovery first (establishes registry pattern), then model extension, then endpoint.

---

## Research Sources Adopted

Task 004 (research) completed partially due to sub-exploration timeout. Design proceeds using Tasks 001-003 outputs and learnings:

| Source | Finding Adopted | Reference |
|--------|----------------|-----------|
| LRN-001 | `PyRefMut<'_, Self>` for fluent builder APIs | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| LRN-003 | Whitelist-based validation for expression function names | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| LRN-005 | `create_app()` constructor DI for effect services | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| LRN-008 | Record-replay pattern for FFmpeg contract tests | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| LRN-011 | Rust=input safety, Python=business logic boundary | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| LRN-012 | Rust justification is correctness, not speed | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| LRN-019 | Infrastructure-first theme ordering | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| LRN-025 | Handoff documents for zero-rework sequencing | `comms/outbox/versions/design/v006/002-backlog/learnings-summary.md` |
| Impact #9 | Clip effects model is substantial, needs dedicated feature | `comms/outbox/versions/design/v006/003-impact-assessment/impact-summary.md` |
| Impact #13 | Effect registry needs upfront design for extensibility | `comms/outbox/versions/design/v006/003-impact-assessment/impact-summary.md` |
| Retrospective | Server-side sorting for new list endpoints | `comms/outbox/versions/design/v006/002-backlog/retrospective-insights.md` |
| Retrospective | Generate quality-gaps.md when debt identified | `comms/outbox/versions/design/v006/002-backlog/retrospective-insights.md` |
