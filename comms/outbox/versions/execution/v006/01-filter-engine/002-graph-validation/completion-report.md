---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  clippy: pass
  cargo_test: pass
---
# Completion Report: 002-graph-validation

## Summary

Implemented opt-in filter graph validation for `FilterGraph` in Rust with PyO3 bindings. The validation detects three categories of structural errors: unconnected pads, cycles (via Kahn's algorithm), and duplicate output labels. All validation is opt-in via `validate()` and `validated_to_string()` methods -- existing `Display`/`to_string()` behavior is completely unchanged.

## Acceptance Criteria

### FR-001: Pad Label Validation - PASS
Pad labels are validated for correct matching. Each output label must feed a matching input label in another chain. Stream references (`N:v`, `N:a`) are special-cased as external inputs and exempt from matching.

### FR-002: Unconnected Pad Detection - PASS
Unconnected input pads are detected when an input label references a label not produced by any chain's output. Errors report the specific pad name. Uses `HashMap<output_label, chain_index>` for O(1) lookup.

### FR-003: Cycle Detection - PASS
Graph cycles are detected using Kahn's algorithm (BFS + in-degree tracking) before serialization. O(V+E) time, O(V) space. When cycles are detected, the labels of involved chains are reported.

### FR-004: Actionable Error Messages - PASS
`GraphValidationError` enum with `UnconnectedPad { label }`, `CycleDetected { labels }`, and `DuplicateLabel { label }` variants. Each has a `Display` implementation with actionable guidance (e.g., "Add an output label [x] to another chain, or remove this input.").

### FR-005: Backward Compatibility - PASS
`validate()` and `validated_to_string()` are opt-in methods. Existing `Display`/`to_string()` is not modified. All existing tests continue to pass without modification.

## Files Modified

| File | Changes |
|------|---------|
| `rust/stoat_ferret_core/src/ffmpeg/filter.rs` | Added `GraphValidationError` enum, `validate()`, `validated_to_string()`, PyO3 bindings, 16 new Rust tests |
| `stubs/stoat_ferret_core/_core.pyi` | Added `validate()` and `validated_to_string()` method stubs to `FilterGraph` |
| `tests/test_pyo3_bindings.py` | Added 6 Python tests for validation via PyO3 bindings |

## Test Coverage

- **Rust**: 16 new tests covering valid graphs, unconnected pads, duplicate labels, cycles, multiple errors, split patterns, error display, and backward compatibility
- **Python**: 6 new tests covering valid validation, unconnected pad error, duplicate label error, cycle detection error, validated_to_string success and failure
- **All existing tests pass unchanged**: 253 Rust tests, 92 doc-tests, 650 Python tests

## Quality Gates

- ruff check: pass
- ruff format: pass
- mypy: pass (0 errors)
- pytest: 650 passed, 93.29% coverage
- cargo clippy: pass (0 warnings)
- cargo test: 253 passed + 92 doc-tests passed
