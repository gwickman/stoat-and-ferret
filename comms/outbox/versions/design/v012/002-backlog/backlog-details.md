# Backlog Details — v012

## BL-061: Wire or remove execute_command() Rust-Python FFmpeg bridge

- **Priority:** P2 | **Size:** L | **Status:** open
- **Tags:** wiring-gap, ffmpeg, rust-python

**Description:**
> **Current state:** `execute_command()` was built in v002/04-ffmpeg-integration as the bridge between the Rust command builder and the Python FFmpeg executor. It has zero callers in production code.
>
> **Gap:** The function exists and is tested in isolation but is never used in any render or export workflow.
>
> **Impact:** The Rust-to-Python FFmpeg pipeline has no integration point. Either the bridge needs wiring into a real workflow, or it's dead code that should be removed to reduce maintenance burden.

**Acceptance Criteria:**
1. execute_command() is called by at least one render/export code path connecting Rust command builder output to Python FFmpeg executor
2. Render workflow produces a working output file via the Rust-to-Python bridge
3. If execute_command() is genuinely unnecessary, it is removed along with its tests

**Notes:** None

**Complexity Assessment:** Moderate-to-high. Requires investigation to determine whether the function serves a future purpose or is dead code. If "wire," requires integrating into an existing render/export workflow with end-to-end testing. If "remove," straightforward deletion but must verify no downstream consumers. The decision itself (wire vs remove) carries the main complexity.

---

## BL-066: Add transition support to Effect Workshop GUI

- **Priority:** P3 | **Size:** L | **Status:** open
- **Tags:** wiring-gap, gui, effects, transitions

**Description:**
> **Current state:** `POST /projects/{id}/effects/transition` endpoint is implemented and functional, but the Effect Workshop GUI only handles per-clip effects. There is no GUI surface for the transition API.
>
> **Gap:** The transition API was built in v007/02-effect-registry-api but the Effect Workshop GUI in v007/03 was scoped to per-clip effects only.
>
> **Impact:** Transitions are only accessible via direct API calls. Users have no way to discover or apply transitions through the GUI.

**Acceptance Criteria:**
1. Effect Workshop GUI includes a transition section or mode for applying transitions between clips
2. GUI calls POST /projects/{id}/effects/transition endpoint
3. User can preview and apply at least one transition type through the GUI

**Notes:** None

**Complexity Assessment:** Moderate. The backend endpoint already exists and is functional — this is primarily frontend wiring work. Must follow established Effect Workshop GUI patterns (catalog UI, parameter forms, schema-driven rendering). Complexity comes from transition UX: transitions apply between clips, not to a single clip, requiring a different selection model than per-clip effects.

---

## BL-067: Audit and trim unused PyO3 bindings from v001 (TimeRange ops, input sanitization)

- **Priority:** P3 | **Size:** L | **Status:** open
- **Tags:** dead-code, rust-python, api-surface

**Description:**
> **Current state:** Several Rust functions are exposed via PyO3 but have zero production callers in Python. TimeRange list operations (find_gaps, merge_ranges, total_coverage) are design-ahead code for future timeline editing. Input sanitization functions (validate_crf, validate_speed) overlap with internal Rust validation in FFmpegCommand.build().
>
> **Gap:** Functions were exposed "just in case" in v001 without a consuming code path. They're tested but unused.
>
> **Impact:** Inflated public API surface increases maintenance burden and PyO3 binding complexity. Unclear to consumers which functions are intended for use vs aspirational.

**Acceptance Criteria:**
1. TimeRange list operations (find_gaps, merge_ranges, total_coverage) are either used by a production code path or removed from PyO3 bindings
2. Input sanitization functions (validate_crf, validate_speed, etc.) are either called from Python production code or removed from PyO3 bindings if Rust-internal validation covers the same checks
3. Stub file reflects the final public API surface

**Notes:** None

**Complexity Assessment:** Low-to-moderate. Primarily an investigation and deletion task. Requires auditing Python production code for callers, verifying Rust-internal validation coverage for sanitization functions, and ensuring the Phase 3 Composition Engine (deferred) won't need TimeRange list operations. Stub regeneration is mechanical. Risk: accidentally removing a binding needed by future work.

---

## BL-068: Audit and trim unused PyO3 bindings from v006 filter engine

- **Priority:** P3 | **Size:** L | **Status:** open
- **Tags:** dead-code, rust-python, api-surface

**Description:**
> **Current state:** Three v006 filter engine features (Expression Engine, Graph Validation, Filter Composition) expose Python bindings via PyO3 that are only used in parity tests, never in production code. The Rust code uses these capabilities internally (e.g., DrawtextBuilder uses Expr for alpha fades, DuckingPattern uses composition).
>
> **Gap:** PyO3 bindings were created in v006/01-filter-engine for all three features but no Python production code consumes them. The Rust-internal usage works fine without the Python bindings.
>
> **Impact:** Six unused Python binding functions inflate the public API surface. Maintaining PyO3 wrappers for internally-consumed Rust code adds build complexity without value.

**Acceptance Criteria:**
1. Expression Engine (Expr), Graph Validation (validate, validated_to_string), and Filter Composition (compose_chain, compose_branch, compose_merge) PyO3 bindings are either used by Python production code or removed from the public API
2. If bindings are retained for future use, they are documented as such in the stub file
3. Parity tests are updated to reflect any binding changes

**Notes:** None

**Complexity Assessment:** Low-to-moderate. Similar audit-and-trim pattern as BL-067. Additional consideration: parity tests specifically exercise these bindings, so test updates are required if bindings are removed. Must evaluate whether parity tests (Rust-Python equivalence) remain valuable without the bindings or should be restructured. Depends on BL-061 outcome — the execute_command decision may affect which bindings count as "needed."

---

## BL-079: Fix API spec examples to show realistic progress values for running jobs

- **Priority:** P3 | **Size:** L | **Status:** open
- **Tags:** documentation, api-spec, rca

**Description:**
> The API specification at `docs/design/05-api-specification.md` (lines 280-361) shows `"progress": null` in the running-state job status example. This normalized null progress as the correct behavior for running jobs, making it appear correct to implementors when the field was never actually populated. The spec examples should show realistic values for all states to set correct implementor expectations.

**Acceptance Criteria:**
1. The running-state job example in docs/design/05-api-specification.md shows a realistic progress value (e.g. 0.45) instead of null
2. All job status examples across the spec show realistic field values for their respective states

**Notes:** None

**Complexity Assessment:** Low. Documentation-only change to a single file. Requires reviewing all job status examples in the API spec and ensuring each state shows realistic field values. No code changes, no test impacts. Low risk.
