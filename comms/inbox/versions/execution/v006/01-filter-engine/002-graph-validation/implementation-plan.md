# Implementation Plan: graph-validation

## Overview

Add opt-in validation to the existing FilterGraph in `filter.rs`. Implement Kahn's algorithm for cycle detection, pad label matching for unconnected pad detection, and duplicate label checking. Expose `validate()` and `validated_to_string()` via PyO3 bindings without modifying existing `Display`/`to_string()`.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/filter.rs` | Modify | Add validate(), validated_to_string(), validation error types, Kahn's algorithm |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Export validation error types if needed |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add validate/validated_to_string stubs (via stub_gen) |
| `tests/test_pyo3_bindings.py` | Modify | Add Python-side validation tests |

## Test Files

`tests/test_pyo3_bindings.py`

## Implementation Stages

### Stage 1: Validation Error Types

1. Define `GraphValidationError` enum in `filter.rs`:
   - `UnconnectedPad { label: String }` — pad has no matching connection
   - `CycleDetected { labels: Vec<String> }` — graph contains a cycle
   - `DuplicateLabel { label: String }` — same label used multiple times as output
2. Implement `Display` for actionable error messages
3. Implement conversion to `PyValueError` for PyO3

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- filter
```

### Stage 2: Kahn's Algorithm and Pad Matching

1. Implement `validate()` method on `FilterGraph`:
   - Build adjacency map from output labels to chain indices
   - Build in-degree map from input labels
   - Special-case stream references (`N:v`, `N:a`) — not inter-chain labels
   - Check for duplicate output labels
   - Check for unmatched input labels (unconnected pads)
   - Run Kahn's BFS: enqueue zero in-degree nodes, process, decrement successors
   - If result count < total chains, cycle detected
2. Return `Result<(), Vec<GraphValidationError>>`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- filter
```

### Stage 3: validated_to_string and PyO3 Bindings

1. Add `validated_to_string()` convenience method: calls `validate()` then `to_string()`
2. Add `#[pyo3(name = "validate")]` and `#[pyo3(name = "validated_to_string")]` bindings
3. Regenerate stubs: `cargo run --bin stub_gen`
4. Verify stubs: `uv run python scripts/verify_stubs.py`
5. Add Python tests for validation in `tests/test_pyo3_bindings.py`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo run --bin stub_gen
uv run python scripts/verify_stubs.py
uv run pytest tests/test_pyo3_bindings.py -v
```

### Stage 4: Backward Compatibility Verification

1. Run all existing FilterGraph tests — must pass without changes
2. Verify existing `to_string()` / `Display` behavior is unchanged
3. Add tests for invalid graphs (unconnected pads, cycles, duplicate labels)
4. Add tests for valid graphs passing validation

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test
uv run pytest tests/test_pyo3_bindings.py -v
```

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings
cd rust/stoat_ferret_core && cargo test
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- FilterGraph backward compatibility — mitigate with opt-in validate() method. See `006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat(rust): add filter graph validation with cycle detection

BL-038: Opt-in validate() and validated_to_string() on FilterGraph using
Kahn's algorithm. Detects unconnected pads, cycles, and duplicate labels.
```