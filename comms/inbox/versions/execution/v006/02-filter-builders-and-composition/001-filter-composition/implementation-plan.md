# Implementation Plan: filter-composition

## Overview

Build chain, branch, and merge composition modes for filter graphs with automatic pad label management and automatic validation. This creates a new composition module that consumes the existing FilterGraph and graph validation from Theme 01.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/composition.rs` | Create | Chain, branch, merge composition types and builder API |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Modify | Add `pub mod composition;` declaration |
| `rust/stoat_ferret_core/src/ffmpeg/filter.rs` | Modify | Expose internal types needed by composition (if not already public) |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Register composition types in PyO3 module |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add type stubs for composition types |
| `rust/stoat_ferret_core/tests/test_composition.rs` | Create | Composition unit tests |

## Implementation Stages

### Stage 1: Chain Composition

1. Create `rust/stoat_ferret_core/src/ffmpeg/composition.rs` with:
   - `CompositionBuilder` struct with `PyRefMut` chaining (LRN-001)
   - `fn chain(filters: Vec<Filter>) -> FilterGraph` — sequential application to single stream
   - Automatic pad label generation: `[chain_0]`, `[chain_1]`, etc.
   - Validation via FilterGraph's `validate()` method
2. Add `pub mod composition;` to `rust/stoat_ferret_core/src/ffmpeg/mod.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_composition
```

### Stage 2: Branch and Merge Composition

1. Add branch composition:
   - `fn branch(input: Filter, outputs: Vec<Filter>) -> FilterGraph`
   - Splits one stream into multiple output streams with automatic pad labels
2. Add merge composition:
   - `fn merge(inputs: Vec<FilterGraph>, merger: Filter) -> FilterGraph`
   - Supports overlay, amix, concat as merger filters
   - Combines multiple input streams with automatic pad management

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_composition
```

### Stage 3: Automatic Validation and Nesting

1. Composed graphs validate automatically before serialization
2. Support nested composition (chain within branch, branch within merge)
3. Verify composed graphs produce valid FFmpeg filter_complex strings

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_composition
```

### Stage 4: PyO3 Bindings and Type Stubs

1. Add `#[pyclass]` and `#[pymethods]` to CompositionBuilder
   - `py_` prefix with `#[pyo3(name = "...")]` convention
   - `#[gen_stub_pyclass]` annotations
2. Register in `lib.rs` PyO3 module
3. Generate and update stubs:
   ```bash
   cd rust/stoat_ferret_core && cargo run --bin stub_gen
   ```
4. Update `stubs/stoat_ferret_core/_core.pyi`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test
uv run python -c "from stoat_ferret_core import CompositionBuilder"
uv run python scripts/verify_stubs.py
```

## Test Infrastructure Updates

- No new test infrastructure needed

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings
cd rust/stoat_ferret_core && cargo test
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Depends on Theme 01 Feature 002 (graph-validation) — must be complete before this feature starts. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: build filter composition system with chain, branch, and merge

Implement chain, branch, and merge composition modes with automatic
pad label management and validation. Composed graphs validate
automatically before serialization. Covers BL-039.
```