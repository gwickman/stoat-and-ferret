# Investigation Log — v012 Critical Thinking

## Investigation 1: Phase 3 Composition Engine Scope

**Question**: Which of the 11 removed PyO3 bindings does Phase 3 actually need?

**Method**: Read `docs/design/01-roadmap.md:271-348` for Phase 3 milestone definitions. Cross-referenced Phase 3 deliverables against the binding categories.

**Findings**:
- Phase 3 has 8 milestones: M3.1 (Layout Calculations), M3.2 (PIP), M3.3 (Split Screen), M3.4 (Layer System), M3.5 (Project Persistence), M3.6 (Quality Verification), M3.7 (Visual Timeline GUI), M3.8 (Composition Preview GUI)
- **TimeRange ops** (find_gaps, merge_ranges, total_coverage): Not referenced in Phase 3 scope. Phase 3 focuses on spatial layout, not temporal gap analysis.
- **Filter composition** (Expr, compose_chain, compose_branch, compose_merge, validated_to_string): Used internally by DrawtextBuilder (`ffmpeg/drawtext.rs:319-356`) and DuckingPattern (`ffmpeg/audio.rs:720-745`) via native Rust calls. Phase 3 mentions "complex filter graph generator" but doesn't specify Python-level access. Current pattern: Rust builds graphs internally, Python receives filter strings via API responses.
- **Sanitization** (validate_crf, validate_speed): Rust-internal validation in `command.rs:582-586` and `speed.rs:116-117` covers these entirely.

**Evidence**: `docs/design/01-roadmap.md:271-348`, `comms/outbox/versions/design/v012/004-research/evidence-log.md`, `comms/outbox/versions/design/v012/004-research/codebase-patterns.md`

**Conclusion**: None of the 11 bindings are required by Phase 3's current scope. The Rust implementations remain available for internal use.

## Investigation 2: ClipSelector Extension vs. New Component

**Question**: Should BL-066 use a new ClipPairSelector or extend ClipSelector?

**Method**: Read `gui/src/components/ClipSelector.tsx`, `gui/src/pages/EffectsPage.tsx`, examined Zustand store patterns. Searched for existing multi-select patterns.

**Findings**:
- ClipSelector is ~50 lines with a single-select `onSelect: (clipId: string) => void` API
- No multi-select patterns exist in the GUI codebase
- EffectsPage uses ClipSelector with effectStackStore's `selectClip(clipId)` — single ID state
- ClipSelector renders button chips with timeline metadata — this rendering logic would need duplication in a separate component
- Extending with optional props (`pairMode?: boolean`, `selectedFromId`, `selectedToId`, `onSelectPair`) adds ~30-40 lines while keeping the single-select API unchanged
- A separate ClipPairSelector would duplicate ~45 lines of clip rendering and create two components to maintain

**Evidence**: `gui/src/components/ClipSelector.tsx`, `gui/src/pages/EffectsPage.tsx`, `gui/src/stores/effectStackStore.ts`

**Conclusion**: Extend ClipSelector with optional pair-mode props. This follows KISS/DRY (per AGENTS.md Code Quality Principles). The TransitionPanel and useTransitionStore designs remain valid — only the clip selection component changes.

## Investigation 3: Stub Regeneration Safety

**Question**: Will removing PyO3 bindings cause stub regeneration issues?

**Method**: Read `scripts/verify_stubs.py`, `stubs/stoat_ferret_core/_core.pyi` (1,766 lines), `lib.rs` module registration. Analyzed verification logic.

**Findings**:
- verify_stubs.py performs **one-way** drift detection: checks that all generated stub types exist in manual stubs
- Manual stubs (1,766 lines) are ~2x larger than generated stubs (802 lines) due to hand-written method signatures and docstrings
- Removing `#[pyfunction]` from Rust removes the function from the generated stubs
- verify_stubs.py would NOT catch stale entries remaining in manual stubs after binding removal (it only flags missing entries, not extra ones)
- The stub generation itself works correctly for removals — `cargo run --bin stub_gen` simply omits removed types

**Gap identified**: If manual stubs retain entries for removed bindings, CI won't catch this. The entries would reference non-existent Python functions, potentially confusing IDE tooling.

**Evidence**: `scripts/verify_stubs.py`, `stubs/stoat_ferret_core/_core.pyi`, `rust/stoat_ferret_core/src/lib.rs`

**Conclusion**: Stub regeneration is safe for v012. The one-way verification gap doesn't block v012 but should be noted. Mitigation: add grep verification step to binding trim features to confirm manual stubs don't retain removed entries.

## Investigation 4: PLAN.md Backlog Coverage Validation

**Question**: Are all 5 backlog items (BL-061, BL-066, BL-067, BL-068, BL-079) still covered?

**Method**: Cross-referenced `docs/auto-dev/plan.md` v012 section against logical design themes/features.

**Findings**:
- BL-061 → Theme 01 / Feature 001-execute-command-removal
- BL-066 → Theme 02 / Feature 001-transition-gui
- BL-067 → Theme 01 / Feature 002-v001-bindings-trim
- BL-068 → Theme 01 / Feature 003-v006-bindings-trim
- BL-079 → Theme 02 / Feature 002-api-spec-corrections
- All 5 items fully covered. No deferrals, no scope reduction.

**Evidence**: `docs/auto-dev/plan.md:46-61`, `comms/outbox/versions/design/v012/005-logical-design/logical-design.md`

**Conclusion**: Full backlog coverage confirmed. No changes needed.

## Investigation 5: Persistence Coherence Check

**Question**: Does v012 introduce persistent state requiring storage path verification?

**Method**: Reviewed v012 features for state persistence. Checked Task 004 output for persistence analysis.

**Findings**:
- No persistence analysis was produced in Task 004 (no `persistence-analysis.md` exists)
- Theme 01 (bindings cleanup) only removes code — no new persistent state
- Theme 02 / Feature 001 (transition-gui): Transitions store to existing `transitions_json` column in projects table (`schema.py:93`, `project_repository.py:110-111,155-156,199-200`). This storage was established in v007 and is fully operational.
- Theme 02 / Feature 002 (api-spec-corrections): Documentation-only — no persistence changes

**Evidence**: No `persistence-analysis.md` in Task 004 artifacts. `comms/outbox/versions/design/v012/004-research/codebase-patterns.md` documents existing transition storage.

**Conclusion**: No new persistent state introduced. All storage paths are pre-existing and verified by production usage since v007. No BLOCKING persistence risk.
