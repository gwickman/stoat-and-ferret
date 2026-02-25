# 005 Architecture Alignment — v012

Architecture drift detected. v012 removed 11 PyO3 bindings, deleted 2 Python files, and added new GUI components (TransitionPanel, transitionStore, ClipSelector pair-mode), none of which are reflected in the C4 documentation last generated for v011. Drift was appended to existing open backlog item BL-069.

## Existing Open Items

- **BL-069**: "Update C4 architecture documentation for v009 changes" (P2, open, tags: architecture/c4/documentation). Already tracks 15 drift items from v009, v010, and v011.
- **PR-007**: "C4 architecture documentation drift accumulating across v009-v010" (P1, open, tags: cross-version-retro/architecture/documentation/drift).

## Changes in v012

### Theme 01: rust-bindings-cleanup
- **Removed 11 PyO3 bindings**: `find_gaps`, `merge_ranges`, `total_coverage`, `validate_crf`, `validate_speed`, `PyExpr`, `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge`, `execute_command`
- **Removed 1 error class**: `CommandExecutionError`
- **Deleted files**: `src/stoat_ferret/ffmpeg/integration.py`, `tests/test_integration.py`, `benchmarks/bench_ranges.py`
- Rust-internal implementations preserved; only Python-facing wrappers removed

### Theme 02: workshop-and-docs-polish
- **New component**: `TransitionPanel` (gui/src/components/TransitionPanel.tsx)
- **New store**: `transitionStore` (gui/src/stores/transitionStore.ts)
- **Extended component**: `ClipSelector` now supports pair-mode props for transition clip selection
- **API doc corrections**: 6 inconsistencies fixed in API spec (progress values, cancelled status)

## Documentation Status

C4 documentation exists at all levels (context, container, component, code) with 43 code-level files. Last generated for v011 (2026-02-24, delta mode). ARCHITECTURE.md exists and is current at a high level.

| Document | Exists | Last Updated |
|----------|--------|-------------|
| docs/C4-Documentation/README.md | Yes | v011 (2026-02-24) |
| docs/C4-Documentation/c4-context.md | Yes | v011 |
| docs/C4-Documentation/c4-container.md | Yes | v011 |
| docs/C4-Documentation/c4-component.md | Yes | v011 |
| docs/C4-Documentation/c4-code-*.md (43 files) | Yes | v011 |
| docs/ARCHITECTURE.md | Yes | Current (high-level) |

## Drift Assessment

Six new drift items from v012, all verified against the codebase:

1. **Removed PyO3 bindings still listed in C4 docs** (BL-069 note 16): 11 bindings removed in PRs #113-#115 but still documented as Python-facing API in c4-container.md, c4-code-rust-core.md, c4-code-stoat-ferret-core.md, c4-code-stubs-stoat-ferret-core.md, and 5 other code-level docs.

2. **integration.py deleted but still documented** (BL-069 note 17): `src/stoat_ferret/ffmpeg/integration.py` deleted in PR #113. Still referenced in c4-code-stoat-ferret-ffmpeg.md.

3. **test_integration.py deleted but still documented** (BL-069 note 18): `tests/test_integration.py` deleted in PR #113. Still referenced in c4-code-tests.md.

4. **Component and store counts stale** (BL-069 note 19): Now 25 React components and 9 Zustand stores (was 24/8 after v011). C4 docs still say "22 React components" and "7 Zustand stores".

5. **TransitionPanel and transitionStore undocumented** (BL-069 note 20): New GUI files from PR #116 not in c4-component-web-gui.md or code-level GUI docs.

6. **ClipSelector pair-mode extension undocumented** (BL-069 note 21): New optional props for transition clip selection not reflected in C4 docs.

## Action Taken

**Updated existing backlog item BL-069** with 6 new drift notes (items 16-21) documenting v012-specific architecture drift. No new backlog item created since BL-069 already consolidates all C4 drift from v009 onward.
