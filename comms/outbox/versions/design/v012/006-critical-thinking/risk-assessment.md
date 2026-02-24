# Risk Assessment — v012

## Risk: Accidental removal of bindings needed by Phase 3 Composition Engine

- **Original severity**: medium
- **Category**: investigate now
- **Investigation**: Reviewed Phase 3 scope in `docs/design/01-roadmap.md:271-348` (8 milestones: layout calculations, PIP, split screen, layer system, project persistence, quality verification, visual timeline GUI, composition preview GUI). Checked which of the 11 removed bindings Phase 3 would need.
- **Finding**: Phase 3 scope focuses on layout/composition at the Rust level (positions, scales, Z-ordering, filter graph generation). TimeRange operations (find_gaps, merge_ranges, total_coverage) are NOT needed — Phase 3 uses layout calculations, not gap analysis. Filter composition bindings (compose_chain, compose_branch, compose_merge, Expr) are used internally by DrawtextBuilder and DuckingPattern via native Rust calls, not PyO3 wrappers. Phase 3's "complex filter graph generator" does not specify Python-level composition access. Current Rust-internal usage patterns confirm Python bindings are redundant.
- **Resolution**: Proceed with removal as designed. The Rust implementations remain intact for internal use. Upgrade triggers in CHANGELOG.md provide a clear re-addition path if Phase 3 scope evolves to require Python-level access. Re-adding PyO3 wrappers is mechanical (~5-10 lines per binding).
- **Affected themes/features**: Theme 01 / Features 002, 003

## Risk: Parity test removal reduces Rust-Python equivalence confidence

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: Reviewed test structure in `tests/test_pyo3_bindings.py`. The ~53 parity tests verify equivalence for functions that will no longer have Python bindings. Checked version control accessibility for test pattern recovery.
- **Finding**: Parity tests validate Rust-Python equivalence for specific bindings. Once bindings are removed, these tests are structurally invalid — they cannot execute. Git history preserves the exact test patterns for future reference. Commenting out or archiving tests introduces dead code maintenance burden.
- **Resolution**: Fully remove parity tests as designed. If bindings are re-added in the future, parity tests can be recreated using git history (`git log --all -- tests/test_pyo3_bindings.py`) and the current test patterns as templates. The remaining ~120+ parity tests for active bindings continue to provide Rust-Python equivalence confidence.
- **Affected themes/features**: Theme 01 / Features 002, 003

## Risk: ClipPairSelector UX complexity for transition selection

- **Original severity**: medium
- **Category**: investigate now
- **Investigation**: Examined ClipSelector component (`gui/src/components/ClipSelector.tsx`, ~50 lines) — single-select button-chip pattern with `onSelect: (clipId: string) => void`. Reviewed EffectsPage integration, Zustand store patterns (effectStackStore, effectCatalogStore), and searched for existing multi-select patterns in the GUI (none found).
- **Finding**: ClipSelector is a simple, focused component. Extending it with optional `pairMode` props (selectedFromId, selectedToId, onSelectPair) requires ~30-40 additional lines while preserving the existing single-select API untouched. A separate ClipPairSelector duplicates ~45 lines of clip rendering logic and creates a maintenance burden. The "from/to" toggle interaction (click first clip = "from", click second = "to") is straightforward UX with visual differentiation via color coding.
- **Resolution**: **Design change**: Replace the separate ClipPairSelector component with an extended ClipSelector that supports optional pair-mode selection. This follows KISS/DRY principles and avoids component duplication. The `useTransitionStore` Zustand store and `TransitionPanel` component remain as designed.
- **Affected themes/features**: Theme 02 / Feature 001 (transition-gui)

## Risk: Stub regeneration may require manual fixups

- **Original severity**: low
- **Category**: investigate now
- **Investigation**: Examined `scripts/verify_stubs.py` verification logic, `stubs/stoat_ferret_core/_core.pyi` (1,766 lines manual, vs 802 lines generated), and `lib.rs` module registration.
- **Finding**: The verification script performs **one-way drift detection only** — it checks that generated types exist in manual stubs, but does NOT verify the reverse. When removing PyO3 bindings, the generator produces fewer types, but verify_stubs.py will still pass because manual stubs having extra entries is not flagged. The actual risk is **not** in stub regeneration itself (which works correctly for removals) but in a gap where stale manual stub entries could remain after removal without CI catching them.
- **Resolution**: Stub removal for v012 is safe because: (1) we know exactly which entries to remove from manual stubs (documented in logical design), (2) `verify_stubs.py` will catch any entries we fail to ADD, and (3) removing entries from manual stubs is straightforward deletion. Add a post-removal step to each binding trim feature: manually verify that `_core.pyi` no longer contains entries for removed bindings by grep. No changes to verify_stubs.py needed for v012 scope (a reverse-verification enhancement is a separate backlog concern).
- **Affected themes/features**: Theme 01 / Features 002, 003

## Risk: Architecture drift from C4 documentation exclusion

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: None for v012 — this is an accepted known gap per Task 005.
- **Finding**: BL-069 (C4 documentation update) is excluded from v012 scope. C4 docs will drift further with v012's 11 binding removals and new GUI component. The drift is tracked externally.
- **Resolution**: Accept. C4 documentation update is explicitly tracked as a deferred item in PLAN.md. v012 changes are primarily removals (reducing API surface), which makes C4 drift less impactful — removed items simply no longer need documentation. The new TransitionPanel component is a bounded addition within the existing Effect Workshop architecture.
- **Affected themes/features**: All themes (documentation-level impact only)

## Risk: Edit tool non-unique match errors in large test files

- **Original severity**: low
- **Category**: accept with mitigation
- **Investigation**: None — Task 005 already identified the mitigation (class-level deletion).
- **Finding**: `test_pyo3_bindings.py` contains similar test patterns across classes. Method-level editing risks non-unique matches.
- **Resolution**: Use class-level deletion (match entire `class TestRangeListOperations:` block, etc.) rather than method-by-method editing. If class blocks are too large for single Edit operations, use Write tool to rewrite the file with classes removed. This is already documented in Task 005 and requires no design change.
- **Affected themes/features**: Theme 01 / Features 002, 003
