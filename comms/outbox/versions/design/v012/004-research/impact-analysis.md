# Impact Analysis — v012

## Dependencies (Code/Tools/Configs Affected)

### BL-061: execute_command Removal
- **Remove**: `src/stoat_ferret/ffmpeg/integration.py` (execute_command function + CommandExecutionError class)
- **Update**: `src/stoat_ferret/ffmpeg/__init__.py` — remove exports
- **Remove**: `tests/test_integration.py` — 13 test methods (entire file may be removed)
- **Update**: C4 docs — `c4-code-stoat-ferret-ffmpeg.md`, `c4-component-application-services.md`
- **No config changes**

### BL-066: Transition GUI
- **New files**: TransitionPanel/ClipPairSelector components in gui/src/components/
- **New file**: useTransitionStore in gui/src/stores/
- **Modify**: gui/src/pages/EffectsPage.tsx — add transition mode/tab
- **Modify**: gui/src/hooks/useEffects.ts — transition category already exists ("xfade" → "transition")
- **No backend changes** (endpoint already exists)

### BL-067: v001 Binding Removal
- **Modify**: Rust source — remove `#[pyfunction]` wrappers from range.rs:549-588, sanitize/mod.rs:559-582
- **Modify**: Rust lib.rs — remove PyO3 module registrations
- **Regenerate**: stubs/stoat_ferret_core/_core.pyi
- **Modify**: src/stoat_ferret_core/__init__.py — remove 5 imports, fallback stubs, __all__ entries
- **Remove/modify**: tests/test_pyo3_bindings.py — ~22 tests
- **Remove**: benchmarks/bench_ranges.py — 3 benchmarks
- **Update**: docs/design/09-security-audit.md, 10-performance-benchmarks.md
- **Update**: C4 docs (4 files)

### BL-068: v006 Binding Removal
- **Modify**: Rust source — remove PyExpr wrapper from expression.rs:537+, compose PyO3 wrappers from filter.rs
- **Modify**: Rust lib.rs — remove PyO3 module registrations
- **Regenerate**: stubs/stoat_ferret_core/_core.pyi — remove Expr class (~157 lines), FilterGraph compose methods
- **Modify**: src/stoat_ferret_core/__init__.py — remove 6+ imports
- **Remove/modify**: tests/test_pyo3_bindings.py — ~31 tests
- **Update**: C4 docs (2 files)

### BL-079: API Spec Fix
- **Modify**: docs/design/05-api-specification.md — 5 example blocks
- **Modify**: docs/manual/03_api-reference.md — progress field description + examples

## Breaking Changes

**None for external consumers.** All removed bindings have zero production callers. The API spec fixes correct documentation to match existing behavior — no runtime behavior change.

**Internal changes**:
- Import errors if any future code tries to import removed functions from stoat_ferret_core (mitigated by __init__.py cleanup)
- Parity tests will fail if not removed alongside bindings (mitigated by planning test removal as sub-task)

## Test Infrastructure Needs

### Tests to Remove
- `tests/test_integration.py` — entire file (if execute_command removed)
- `tests/test_pyo3_bindings.py` — TestRangeListOperations class (15 tests), TestSanitization crf/speed tests (4), TestExpr class (16), composition tests (~15)
- `benchmarks/bench_ranges.py` — entire file

### Tests to Create
- BL-066: Transition panel component tests (Vitest)
- BL-066: ClipPairSelector component tests (Vitest)
- BL-066: useTransitionStore unit tests (Vitest)

### Tests to Update
- test_pyo3_bindings.py module-level export tests must be updated to reflect removed bindings
- Any snapshot tests referencing removed function names

## Documentation Updates Required

| Document | Change | Caused By |
|----------|--------|-----------|
| docs/design/05-api-specification.md | Fix 5 progress/status inconsistencies | BL-079 |
| docs/manual/03_api-reference.md | Fix progress range 0-100→0.0-1.0 | BL-079 |
| docs/design/09-security-audit.md | Note removal of validate_crf/validate_speed | BL-067 |
| docs/design/10-performance-benchmarks.md | Remove benchmark entries for range ops | BL-067 |
| docs/CHANGELOG.md | Add v012 entries for all binding removals | BL-067, BL-068 |
| C4 code/component docs (6 files) | Remove references to deleted bindings | BL-061, BL-067, BL-068 |
| stubs/stoat_ferret_core/_core.pyi | Regenerate after binding removal | BL-067, BL-068 |
