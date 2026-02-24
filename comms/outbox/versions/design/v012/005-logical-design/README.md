# Logical Design — v012 API Surface & Bindings Cleanup

Proposed structure for v012: 2 themes containing 5 features total. Theme 01 (rust-bindings-cleanup) addresses the core technical debt — removing dead code and unused PyO3 bindings. Theme 02 (workshop-and-docs-polish) closes frontend and documentation gaps. Both themes are independent and can execute in parallel.

## Theme Overview

### Theme 01: rust-bindings-cleanup (3 features)
**Goal**: Remove execute_command() dead code and 11 unused PyO3 bindings from v001/v006, reducing the Rust-Python API surface and maintenance burden.

- **001-execute-command-removal** (BL-061) — Remove dead bridge function with zero callers
- **002-v001-bindings-trim** (BL-067) — Remove 5 unused v001 bindings (TimeRange ops, sanitization)
- **003-v006-bindings-trim** (BL-068) — Remove 6 unused v006 bindings (Expr, composition, validation)

### Theme 02: workshop-and-docs-polish (2 features)
**Goal**: Wire transition effects into the GUI and fix API spec documentation inconsistencies.

- **001-transition-gui** (BL-066) — Frontend-only wiring to existing transition endpoint
- **002-api-spec-corrections** (BL-079) — Fix 5 progress/status documentation issues

## Key Decisions

1. **BL-061: Remove, not wire.** Research confirmed zero production callers and no existing render/export workflow. ThumbnailService bypasses execute_command entirely. Removal documented with upgrade trigger (Phase 3 Composition Engine).

2. **BL-067/BL-068: Remove all 11 bindings.** Zero production callers for all. Rust-internal validation covers CRF/speed. Parity tests removed alongside bindings. Upgrade triggers documented per LRN-029.

3. **BL-066: New ClipPairSelector component.** Existing ClipSelector is single-clip only. A new component avoids complicating the existing interaction model. Backend adjacency validation handles correctness.

4. **BL-079: Fix 5 issues, not just 1.** Research uncovered 4 additional inconsistencies beyond the originally scoped running-state progress null.

## Dependencies

- **Cross-theme**: None — Theme 01 and Theme 02 are independent.
- **Within Theme 01**: Feature 001 (execute_command removal) must precede features 002/003 (bindings audits), as the removal decision finalizes what counts as "unused." Features 002 and 003 can then execute in parallel.
- **Within Theme 02**: Both features are independent.

## Risks and Unknowns

Items for Task 006 (Critical Thinking) investigation:

1. **Phase 3 Composition Engine binding needs** (medium) — removed bindings may be needed by future composition work. Mitigated by documenting upgrade triggers and preserving Rust implementations.

2. **ClipPairSelector UX complexity** (medium) — new interaction pattern for paired clip selection with no existing mockups. Backend adjacency validation provides safety net.

3. **Parity test removal** (low) — ~53 parity tests removed. Recreatable from version history if bindings are re-added.

4. **Stub regeneration with partial removal** (low) — untested scenario but expected to be simpler than additions.

5. **C4 documentation drift** (low) — accepted gap, BL-069 excluded from v012 scope.

6. **Large test file editing** (low) — mitigated by class-level deletion approach.

## Artifacts

- `logical-design.md` — Complete design proposal with themes, features, acceptance criteria, execution order, and research sources
- `test-strategy.md` — Test requirements per feature including removals, additions, and verification steps
- `risks-and-unknowns.md` — 6 identified risks with severity, investigation needs, and current assumptions
