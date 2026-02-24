# Logical Design — v012 API Surface & Bindings Cleanup

## Version Overview

- **Version**: v012
- **Description**: API Surface & Bindings Cleanup
- **Goal**: Reduce technical debt in the Rust-Python boundary by removing dead code, wire remaining GUI gaps, and correct documentation inconsistencies.
- **Backlog items**: 5 (BL-061, BL-066, BL-067, BL-068, BL-079)
- **Themes**: 2 themes, 5 features total

## Theme 01: rust-bindings-cleanup

**Goal**: Resolve the execute_command() wiring gap and remove unused PyO3 bindings from v001 and v006 that have zero production callers. This reduces the public API surface, lowers maintenance burden, and clarifies which Rust functions are intended for Python consumption. The execute_command decision must come first because it determines what counts as "unused" in subsequent audits.

**Backlog Items**: BL-061, BL-067, BL-068

**Features**:

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-execute-command-removal | Remove the dead execute_command() bridge function and its supporting code | BL-061 | None |
| 2 | 002-v001-bindings-trim | Remove 5 unused v001 PyO3 bindings (TimeRange ops, sanitization) and associated tests | BL-067 | 001-execute-command-removal |
| 3 | 003-v006-bindings-trim | Remove 6 unused v006 PyO3 bindings (Expr, graph validation, composition) and associated parity tests | BL-068 | 001-execute-command-removal |

### Feature 001-execute-command-removal

**Goal**: Remove the dead `execute_command()` function and `CommandExecutionError` class from the FFmpeg integration module.

**Backlog**: BL-061

**Dependencies**: None — this is the first feature in the version.

**Scope**:
- Remove `execute_command()` from `src/stoat_ferret/ffmpeg/integration.py`
- Remove `CommandExecutionError` from the same module
- Update `src/stoat_ferret/ffmpeg/__init__.py` to remove exports
- Remove `tests/test_integration.py` (entire file — all 13 tests are for execute_command)
- Document removal with upgrade trigger: re-add if Phase 3 Composition Engine or any future render/export endpoint needs Rust command building (LRN-029)

**Acceptance Criteria**:
1. `execute_command` and `CommandExecutionError` are removed from `src/stoat_ferret/ffmpeg/integration.py`
2. `src/stoat_ferret/ffmpeg/__init__.py` no longer exports execute_command or CommandExecutionError
3. `tests/test_integration.py` is removed (all 13 test methods covered execute_command exclusively)
4. All existing tests pass (no other code depends on execute_command — evidence: `comms/outbox/versions/design/v012/004-research/evidence-log.md`)
5. A removal note is added to `docs/CHANGELOG.md` documenting what was removed and the re-add trigger

### Feature 002-v001-bindings-trim

**Goal**: Remove 5 unused v001 PyO3 bindings that have zero production callers.

**Backlog**: BL-067

**Dependencies**: 001-execute-command-removal (the execute_command decision finalizes what counts as "unused")

**Scope**:
- Remove `#[pyfunction]` wrappers from `range.rs` (find_gaps, merge_ranges, total_coverage) and `sanitize/mod.rs` (validate_crf, validate_speed)
- Remove PyO3 module registrations from `lib.rs`
- Update `src/stoat_ferret_core/__init__.py` — remove 5 imports, fallback stubs, __all__ entries
- Regenerate `stubs/stoat_ferret_core/_core.pyi`
- Remove ~22 parity tests from `tests/test_pyo3_bindings.py` (TestRangeListOperations: 15 tests, TestSanitization crf/speed: 4 tests, plus related)
- Remove `benchmarks/bench_ranges.py`
- Update `docs/design/09-security-audit.md` and `10-performance-benchmarks.md`
- Document removals with upgrade triggers per LRN-029

**Acceptance Criteria**:
1. `find_gaps`, `merge_ranges`, `total_coverage` PyO3 wrappers are removed from `range.rs`
2. `validate_crf`, `validate_speed` PyO3 wrappers are removed from `sanitize/mod.rs`
3. All 5 functions are removed from `lib.rs` PyO3 module registration
4. `src/stoat_ferret_core/__init__.py` no longer imports or exports these 5 functions
5. Stub file (`_core.pyi`) is regenerated and reflects the reduced API surface
6. Parity tests for removed bindings are deleted from `test_pyo3_bindings.py`
7. `benchmarks/bench_ranges.py` is removed
8. All remaining tests pass — Rust-internal usage of these functions is unaffected
9. `docs/CHANGELOG.md` documents removals with re-add triggers (TimeRange ops: Phase 3 Composition Engine; sanitization: Python-level standalone validation need)

### Feature 003-v006-bindings-trim

**Goal**: Remove 6 unused v006 PyO3 bindings that have zero production callers and are only exercised in parity tests.

**Backlog**: BL-068

**Dependencies**: 001-execute-command-removal (the execute_command decision finalizes what counts as "unused")

**Scope**:
- Remove `PyExpr` wrapper from `expression.rs`
- Remove `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge` PyO3 wrappers from `filter.rs`
- Remove PyO3 module registrations from `lib.rs`
- Update `src/stoat_ferret_core/__init__.py` — remove 6+ imports
- Regenerate `stubs/stoat_ferret_core/_core.pyi` (removes ~157 lines for Expr class + FilterGraph compose methods)
- Remove ~31 parity tests from `test_pyo3_bindings.py` (TestExpr: 16 tests, composition: ~15 tests)
- Verify Rust-internal usage (DrawtextBuilder, DuckingPattern) is unaffected — these use native Rust, not PyO3 wrappers
- Document removals with upgrade triggers per LRN-029

**Acceptance Criteria**:
1. `Expr` (PyExpr) PyO3 wrapper is removed from `expression.rs`
2. `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge` PyO3 wrappers are removed from `filter.rs`
3. All 6 bindings are removed from `lib.rs` PyO3 module registration
4. `src/stoat_ferret_core/__init__.py` no longer imports or exports these bindings
5. Stub file (`_core.pyi`) is regenerated and reflects the reduced API surface
6. Parity tests for removed bindings are deleted from `test_pyo3_bindings.py`
7. Rust-internal usage (DrawtextBuilder, DuckingPattern) continues to work — verified by `cargo test`
8. All remaining Python and Rust tests pass
9. `docs/CHANGELOG.md` documents removals with re-add triggers (Expr: Python-level expression building; compose: Python-level filter graph composition)

## Theme 02: workshop-and-docs-polish

**Goal**: Close remaining polish gaps by wiring the transition API into the Effect Workshop GUI and correcting API specification documentation that shows misleading example values. These items have no dependency on Theme 01 and address frontend and documentation gaps respectively.

**Backlog Items**: BL-066, BL-079

**Features**:

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-transition-gui | Wire transition effects into the Effect Workshop GUI via the existing backend endpoint | BL-066 | None |
| 2 | 002-api-spec-corrections | Fix 5 documentation inconsistencies in API spec and manual for job status examples | BL-079 | None |

### Feature 001-transition-gui

**Goal**: Enable users to discover and apply transition effects between adjacent clips through the Effect Workshop GUI.

**Backlog**: BL-066

**Dependencies**: None — the backend endpoint already exists and is functional (evidence: `comms/outbox/versions/design/v012/004-research/codebase-patterns.md`)

**Scope**:
- Create `useTransitionStore` Zustand store following the slices pattern (source/target clip selection, adjacency state)
- Create `ClipPairSelector` component for selecting two adjacent clips (different from existing single-clip `ClipSelector`)
- Create `TransitionPanel` component integrating clip-pair selection, transition type catalog, parameter form, and preview
- Modify `gui/src/pages/EffectsPage.tsx` to add a transition tab/mode alongside existing per-clip effects
- Follow schema-driven pattern: transition parameter schemas already exist in effect definitions (LRN-032)
- Backend adjacency validation already enforces correctness at `effects.py:556-566` — GUI provides UX convenience only

**Acceptance Criteria**:
1. Effect Workshop GUI includes a "Transitions" tab or mode distinct from per-clip effects
2. User can select two adjacent clips via the ClipPairSelector component
3. GUI displays available transition types (xfade, acrossfade) from the existing effect catalog
4. GUI renders parameter forms for selected transition type using the schema-driven pattern
5. Submitting a transition calls `POST /projects/{id}/effects/transition` and the transition is stored on the project
6. User receives appropriate error feedback when selecting non-adjacent clips (backend returns 400 NOT_ADJACENT)
7. End-to-end: User can open the Effect Workshop, switch to Transitions tab, select two adjacent clips, choose a transition type, configure parameters, and apply — the transition appears in the project's transition list

### Feature 002-api-spec-corrections

**Goal**: Fix 5 documentation inconsistencies in the API specification and manual so examples show realistic values matching actual code behavior.

**Backlog**: BL-079

**Dependencies**: None — documentation-only change.

**Scope**:
- Fix running-state job example: `progress: null` → `progress: 0.45` (`05-api-specification.md:295-302`)
- Fix complete-state job example: `progress: null` → `progress: 1.0` (`05-api-specification.md:306-319`)
- Fix cancel response: `status: "pending"` → `status: "cancelled"` (`05-api-specification.md:374-382`)
- Fix manual progress description: "0-100" → "0.0-1.0" (`03_api-reference.md:984`)
- Add "cancelled" to status enum in spec (currently missing)
- Values based on research: `comms/outbox/versions/design/v012/004-research/external-research.md`

**Acceptance Criteria**:
1. Running-state job example shows `"progress": 0.45` instead of `null`
2. Complete-state job example shows `"progress": 1.0` instead of `null`
3. Cancel response example shows `"status": "cancelled"` instead of `"pending"`
4. API manual progress field description says "0.0-1.0" instead of "0-100"
5. Status enum in spec includes "cancelled" alongside pending, running, complete, failed, timeout
6. End-to-end: All job status examples across the spec show realistic field values for their respective states (pending: null, running: 0.45, complete: 1.0, failed: 0.72, timeout: 0.38, cancelled: 0.30)

## Execution Order

### Theme Dependencies
- **Theme 01** and **Theme 02** are independent — no cross-theme dependencies.
- Both themes can execute in parallel if resources allow.

### Feature Dependencies Within Theme 01
1. **001-execute-command-removal** must complete first — the decision to remove execute_command finalizes the "unused" determination for BL-067/BL-068
2. **002-v001-bindings-trim** and **003-v006-bindings-trim** can execute in parallel after feature 001 completes — they modify different Rust modules (range.rs/sanitize vs expression.rs/filter.rs) and different test classes

### Feature Dependencies Within Theme 02
- **001-transition-gui** and **002-api-spec-corrections** are fully independent — no shared files or state

### Recommended Execution Order
1. Theme 01 / Feature 001 (execute-command-removal) — unlocks Theme 01 features 002/003
2. Theme 01 / Feature 002 (v001-bindings-trim) — parallel with Theme 01 / Feature 003
3. Theme 01 / Feature 003 (v006-bindings-trim) — parallel with Theme 01 / Feature 002
4. Theme 02 / Feature 001 (transition-gui) — can start anytime, independent
5. Theme 02 / Feature 002 (api-spec-corrections) — can start anytime, independent

**Rationale**: BL-061 ordering is documented in PLAN.md and confirmed by research (evidence-log.md). Theme 02 features are independent and can interleave with Theme 01. The two bindings audit features are parallel-safe because they touch different Rust source files and different test classes.

## Research Sources Adopted

### BL-061: Remove Decision
- **Evidence**: Zero production callers confirmed via exhaustive grep (`comms/outbox/versions/design/v012/004-research/evidence-log.md`)
- **Pattern**: Dead code removal with documented upgrade triggers (LRN-029)
- **Rationale**: ThumbnailService calls `executor.run()` directly, bypassing execute_command — no integration point exists

### BL-066: Frontend Wiring Pattern
- **Pattern**: Zustand slices pattern for paired selection (`comms/outbox/versions/design/v012/004-research/external-research.md`)
- **Pattern**: Schema-driven forms following Effect Workshop conventions (LRN-032)
- **Evidence**: Transition endpoint with adjacency validation confirmed (`comms/outbox/versions/design/v012/004-research/codebase-patterns.md`)

### BL-067/BL-068: Binding Removal Pattern
- **Evidence**: Zero production callers for all 11 bindings (`comms/outbox/versions/design/v012/004-research/evidence-log.md`)
- **Evidence**: Rust-internal validation covers CRF/speed without Python involvement (`comms/outbox/versions/design/v012/004-research/evidence-log.md`)
- **Pattern**: Conscious simplicity with upgrade triggers (LRN-029)
- **Guideline**: Python business logic, Rust input safety boundary (LRN-011)

### BL-079: Realistic Progress Values
- **Evidence**: Code uses 0.0-1.0 normalized floats (`comms/outbox/versions/design/v012/004-research/evidence-log.md`)
- **Values**: Recommended per-state values from `comms/outbox/versions/design/v012/004-research/external-research.md`
- **Guideline**: Validate numeric requirements against upstream sources (LRN-034)

## Handler Concurrency Decisions

Not applicable — no new MCP tool handlers are introduced in v012. All features modify existing code, frontend components, or documentation.
