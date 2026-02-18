# Implementation Plan: filter-composition

## Overview

Build a composition API for FilterGraph that supports chain (sequential), branch (one-to-many), and merge (many-to-one) operations with automatic pad label management. The composition system uses the graph validation from the previous feature to ensure structural correctness.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/filter.rs` | Modify | Add composition API (chain, branch, merge) with auto-labeling |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Export composition types if needed |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add composition API stubs (via stub_gen) |
| `tests/test_pyo3_bindings.py` | Modify | Add Python-side composition tests |

## Test Files

`tests/test_pyo3_bindings.py`

## Implementation Stages

### Stage 1: Auto-Label Manager

1. Add label generation utility in `filter.rs` (e.g., `LabelGenerator` with auto-incrementing labels like `_v006_0`, `_v006_1`)
2. Ensure generated labels don't conflict with user-provided labels
3. Unit test label generation and uniqueness

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- filter
```

### Stage 2: Chain Composition

1. Add `FilterGraph::chain(input, filters) -> FilterGraph` method
2. Chain takes an input stream/label and a sequence of filters
3. Automatically generates intermediate labels between filters
4. Result is a FilterGraph with properly wired chains

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- filter
```

### Stage 3: Branch and Merge Composition

1. Add `FilterGraph::branch(input, count) -> Vec<String>` — splits stream using `split`/`asplit`, returns output labels
2. Add `FilterGraph::merge(inputs, merge_filter) -> String` — combines multiple streams using overlay/amix/concat, returns output label
3. Both methods use auto-labeling
4. Validate composed graphs automatically via `validate()`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- filter
```

### Stage 4: PyO3 Bindings

1. Add `#[pymethods]` for composition methods
2. Use `PyRefMut<'_, Self>` for method chaining where appropriate
3. Regenerate stubs: `cargo run --bin stub_gen`
4. Verify stubs: `uv run python scripts/verify_stubs.py`
5. Add Python tests for composition in `tests/test_pyo3_bindings.py`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo run --bin stub_gen
uv run python scripts/verify_stubs.py
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

- Composition complexity — mitigate with simple chain/branch/merge primitives. See `006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat(rust): add filter graph composition API

BL-039: Chain, branch, and merge composition with automatic pad label
management and integrated validation.
```