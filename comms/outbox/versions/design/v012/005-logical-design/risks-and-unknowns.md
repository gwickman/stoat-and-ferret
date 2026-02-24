# Risks and Unknowns — v012

## Risk: Accidental removal of bindings needed by Phase 3 Composition Engine

- **Severity**: medium
- **Description**: BL-067 removes TimeRange list operations (find_gaps, merge_ranges, total_coverage) and BL-068 removes filter composition bindings (compose_chain, compose_branch, compose_merge). The deferred Phase 3 Composition Engine may require some of these for multi-clip timeline editing or Python-level filter graph composition.
- **Investigation needed**: Review Phase 3 Composition Engine scope (if documented) to determine which bindings it would need. Check whether re-adding PyO3 wrappers later is straightforward.
- **Current assumption**: Re-adding PyO3 wrappers is mechanical and low-cost. The Rust implementations remain intact — only the Python-facing bindings are removed. Documenting upgrade triggers (per LRN-029) mitigates this risk. UNVERIFIED — Phase 3 scope is not yet fully specified.

## Risk: Parity test removal reduces Rust-Python equivalence confidence

- **Severity**: low
- **Description**: Removing ~53 parity tests (22 for v001 bindings, 31 for v006 bindings) eliminates a layer of Rust-Python equivalence verification. If bindings are re-added in the future, parity tests would need to be recreated.
- **Investigation needed**: Determine if parity test patterns should be preserved as commented templates or archived for future use.
- **Current assumption**: Parity tests should be fully removed (not commented out). They can be recreated from the current test patterns in version control history if needed. Dead test code is worse than no test code. UNVERIFIED — team preference on archival approach not confirmed.

## Risk: ClipPairSelector UX complexity for transition selection

- **Severity**: medium
- **Description**: The existing ClipSelector component uses a single-clip selection model (`onSelect: (clipId: string) => void`). Transitions require selecting two adjacent clips, which is a fundamentally different interaction pattern. The ClipPairSelector component is new and may require multiple design iterations to get the UX right.
- **Investigation needed**: Determine whether to build a new ClipPairSelector from scratch or extend ClipSelector with a multi-select mode. Review how adjacency is communicated visually to users.
- **Current assumption**: A new ClipPairSelector component is preferred over extending ClipSelector, to avoid complicating the existing single-clip selection flow. Backend adjacency validation (effects.py:556-566) handles correctness — the GUI only needs to provide UX convenience hints. UNVERIFIED — no UX mockups exist.

## Risk: Stub regeneration may require manual fixups

- **Severity**: low
- **Description**: After removing PyO3 bindings in BL-067 and BL-068, stub regeneration via `cargo run --bin stub_gen` produces baseline stubs that may need manual adjustment (per AGENTS.md: "pyo3-stub-gen generates incomplete stubs"). Removing bindings should simplify stubs, but the generator may produce unexpected output when types are partially removed.
- **Investigation needed**: Run stub generation after the first binding removal (BL-067) to verify output is clean before proceeding to BL-068.
- **Current assumption**: Stub regeneration for removals is simpler than for additions — the generator just omits removed types. Manual stubs are maintained separately and should be straightforward to update by deleting the corresponding sections. UNVERIFIED — not tested with partial type removal.

## Risk: Architecture drift from C4 documentation exclusion

- **Severity**: low
- **Description**: v012 removes 11 PyO3 bindings and adds a new GUI component, but BL-069 (C4 architecture documentation update) is explicitly excluded from v012 scope. This means C4 docs will drift further (currently 19 items from v009-v011, plus v012 changes).
- **Investigation needed**: None for v012 — this is an accepted known gap.
- **Current assumption**: C4 documentation update will occur separately. The drift is tracked and will be addressed outside the version cycle. Not a risk to v012 execution, only to documentation accuracy.

## Risk: Edit tool non-unique match errors in large test files

- **Severity**: low
- **Description**: `test_pyo3_bindings.py` is a large file with many similar test patterns. Removing specific test classes (TestRangeListOperations, TestExpr, composition tests) via Edit tool may encounter non-unique match errors if test method names or patterns are similar across classes.
- **Investigation needed**: None — mitigated by using class-level deletion rather than method-by-method editing.
- **Current assumption**: Deleting entire test classes by matching the class definition and its body is sufficient to avoid non-unique match issues. If needed, the file can be rewritten with the classes removed.
