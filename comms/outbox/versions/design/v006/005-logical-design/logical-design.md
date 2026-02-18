# Logical Design — v006 Effects Engine Foundation

## Version Overview

- **Version:** v006
- **Description:** Effects Engine Foundation
- **Roadmap:** Phase 2, Milestones M2.1–M2.3
- **Goal:** Build a greenfield Rust filter expression engine with graph validation, composition system, text overlay builder, speed control builders, effect discovery API, and clip effect application endpoint.
- **Scope:** 7 backlog items (BL-037 through BL-043), organized into 3 themes with 8 features total (7 backlog + 1 documentation feature from impact assessment).

---

## Theme 01: `01-filter-engine`

**Goal:** Build the foundational Rust filter infrastructure — expression type system, filter graph validation, and composition API. These are the building blocks that all downstream filter builders and API endpoints depend on. Corresponds to M2.1 (Filter Expression Engine).

**Backlog Items:** BL-037, BL-038, BL-039

**Rationale:** These three items form the core filter engine that all other v006 work depends on. BL-037 (expressions) is the leaf dependency for BL-040 and BL-041. BL-038 (validation) is the prerequisite for BL-039 (composition). Grouping them ensures the infrastructure is solid before consumers are built. Per LRN-019, infrastructure-first sequencing is proven to eliminate rework.

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | `001-expression-engine` | Type-safe Rust expression builder for FFmpeg filter expressions with proptest validation | BL-037 | None |
| 2 | `002-graph-validation` | Validate FilterGraph pad matching, detect unconnected pads and cycles using Kahn's algorithm | BL-038 | None |
| 3 | `003-filter-composition` | Programmatic chain, branch, and merge composition with automatic pad label management | BL-039 | `002-graph-validation` |

---

## Theme 02: `02-filter-builders`

**Goal:** Implement concrete filter builders for text overlay and speed control using the expression engine and composition system from Theme 01. These are the user-facing effect implementations that the API layer will expose. Corresponds to M2.2 (Text Overlay) and M2.3 (Speed Control).

**Backlog Items:** BL-040, BL-041

**Rationale:** Both items are concrete filter builders that consume the expression engine (BL-037) from Theme 01. They are independent of each other (drawtext and speed are unrelated filter types) but both must complete before Theme 03's discovery API can register them. Grouping them together enables parallel development within the theme.

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | `001-drawtext-builder` | Type-safe drawtext filter builder with position presets, styling, and alpha animation via expression engine | BL-040 | Theme 01 `001-expression-engine` |
| 2 | `002-speed-builders` | setpts and atempo filter builders with automatic atempo chaining for speeds above 2.0x | BL-041 | Theme 01 `001-expression-engine` |

---

## Theme 03: `03-effects-api`

**Goal:** Create the Python-side effect registry, discovery API endpoint, clip effect application endpoint, and update architecture documentation. This bridges the Rust filter engine with the REST API and data model. Corresponds to M2.2–M2.3 API integration.

**Backlog Items:** BL-042, BL-043, plus impact assessment #2 (02-architecture.md update)

**Rationale:** BL-042 (discovery) and BL-043 (clip application) are the API layer that exposes the Rust filter builders to clients. They require both filter builder types (drawtext, speed) to be complete for registration. The architecture documentation update (impact #2, classified as substantial/feature-scope) belongs here because it should reflect the final implementation. Per LRN-011, Python owns business policy, API routing, and effect registration; Rust owns filter generation.

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | `001-effect-discovery` | Effect registry with parameter schemas, AI hints, and GET /effects endpoint | BL-042 | Theme 02 `001-drawtext-builder`, Theme 02 `002-speed-builders` |
| 2 | `002-clip-effect-api` | POST endpoint to apply text overlay to clips with effect storage in clip model | BL-043 | `001-effect-discovery`, Theme 02 `001-drawtext-builder` |
| 3 | `003-architecture-docs` | Update 02-architecture.md with new Rust modules, Effects Service, and clip model extension | Impact #2 | `001-effect-discovery`, `002-clip-effect-api` |

---

## Execution Order

### Theme Dependencies

```
Theme 01 (filter-engine) ──→ Theme 02 (filter-builders) ──→ Theme 03 (effects-api)
```

Strictly sequential. Theme 02 consumes Theme 01's expression engine. Theme 03 registers Theme 02's builders and bridges to the API.

### Feature Dependencies (detailed)

```
T1-001 (expression-engine) ──┬──→ T2-001 (drawtext) ──┬──→ T3-001 (discovery) ──→ T3-002 (clip-effect-api) ──→ T3-003 (architecture-docs)
                              │                         │
T1-002 (graph-validation) ──→ T1-003 (composition)     │
                                                        │
                              └──→ T2-002 (speed) ──────┘
```

Within Theme 01, features 001 and 002 are independent and could run in parallel. Feature 003 depends on 002. Within Theme 02, features are independent. Within Theme 03, features are strictly sequential.

### Rationale

1. **Infrastructure first (LRN-019):** Expression engine and graph validation are foundation; building them first is proven by v004/v005 success.
2. **Handoff chain (LRN-025):** Each feature documents what it provides for downstream consumers. The T1→T2→T3 chain relies on clear handoff of expression types, builder APIs, and registration interfaces.
3. **Parallel opportunities:** T1-001 and T1-002 have no dependency; T2-001 and T2-002 have no mutual dependency. Auto-dev executes features sequentially within themes, but the design allows future parallelization.

---

## Research Sources Adopted

### Expression Engine Type Hierarchy (BL-037)
- **Decision:** Model as `Expr` enum with `Const`, `Var`, `BinaryOp`, `UnaryOp`, `Func`, `If` variants
- **Source:** `comms/outbox/versions/design/v006/004-research/external-research.md` (Section 1) and `004-research/README.md` (Recommendations #1)
- **Core functions (v006):** `between`, `if`, `lt`, `gt`, `eq`, `gte`, `lte`, `clip`, `abs`, `min`, `max`, `mod`, `not` — 13 of 40 total FFmpeg expression functions

### Graph Validation Algorithm (BL-038)
- **Decision:** Kahn's algorithm implemented inline (no petgraph dependency)
- **Source:** `004-research/external-research.md` (Section 5) and `004-research/README.md` (Recommendations #2)
- **Rationale:** FilterGraph <20 nodes; ~30 lines of code; domain-specific error messages favor inline over generic library

### atempo Chaining Strategy (BL-041)
- **Decision:** Chain instances within [0.5, 2.0] using log2 decomposition
- **Source:** `004-research/evidence-log.md` (atempo Quality Threshold, Speed Range entries) and `004-research/external-research.md` (Section 3)
- **Formula:** `N = floor(log2(speed))` stages of 2.0 + remainder

### drawtext Builder Pattern (BL-040)
- **Decision:** Extend existing builder pattern with typed methods; delegate alpha animation to expression engine
- **Source:** `004-research/codebase-patterns.md` (Existing Filter System) and `004-research/README.md` (Recommendations #5)

### PyO3 Builder Pattern (all Rust features)
- **Decision:** `PyRefMut<'_, Self>` return for method chaining across all builders
- **Source:** `004-research/codebase-patterns.md` (PyO3 Builder Pattern) — verified in 14 methods across `command.rs` and `filter.rs`

### DI Pattern for Effect Registry (BL-042)
- **Decision:** Add `effect_registry` kwarg to `create_app()` following existing DI pattern
- **Source:** `004-research/codebase-patterns.md` (DI / create_app Pattern) and LRN-005

### Error Pattern for Validation (BL-038)
- **Decision:** Extend `BoundsError` enum pattern with `UnconnectedPad`, `CycleDetected`, `DuplicateLabel` variants
- **Source:** `004-research/codebase-patterns.md` (Error Pattern)

### Proptest Strategy (BL-037)
- **Decision:** Manual strategies with `prop_oneof!` and `prop_compose!` (no proptest-derive)
- **Source:** `004-research/codebase-patterns.md` (Proptest Usage) and `004-research/external-research.md` (Section 4)

---

## Small Impacts (sub-tasks attached to features)

Per `003-impact-assessment/impact-summary.md`:

| Impact | Owning Feature | Action |
|--------|---------------|--------|
| #1 AGENTS.md module listing | T1-001 `001-expression-engine` | Add new Rust submodule names to Project Structure |
| #3 API spec reconciliation | T3-002 `002-clip-effect-api` | Reconcile 05-api-specification.md after implementation |
| #4 Type stub regeneration | T1-001, T1-003, T2-001, T2-002 | Run stub_gen after each Rust feature with PyO3 bindings |
| #5 PLAN.md status update | Version-level bookkeeping | Update during execution start and close |
| #7 Roadmap checkboxes | Version close | Check off M2.1-2.3 items |

---

## Risks and Unknowns

See `005-logical-design/risks-and-unknowns.md` for full detail. Summary:

1. **Clip effect model design** (high) — BL-043 requires extending clip model with effects field; no prior art in codebase
2. **FilterGraph backward compatibility** (medium) — BL-038 validation must not break existing FilterGraph consumers
3. **Rust coverage ratchet** (medium) — Current 75% vs 90% target; v006 adds significant Rust code
4. **Font file platform dependency** (low) — drawtext `fontfile` parameter is platform-dependent
5. **boxborderw FFmpeg version** (low) — Multi-value syntax requires FFmpeg 5.0+; minimum version policy undefined
