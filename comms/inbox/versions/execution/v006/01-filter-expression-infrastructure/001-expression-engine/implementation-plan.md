# Implementation Plan: expression-engine

## Overview

Implement a Rust expression AST for FFmpeg filter expressions with a type-safe builder API, serialization to valid FFmpeg syntax, property-based tests via proptest, and PyO3 bindings. This is greenfield Rust code in a new `expression` module under the `ffmpeg` directory.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/expression.rs` | Create | Expression AST types, builder, serialization, validation |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Modify | Add `pub mod expression;` declaration |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Register expression types in PyO3 `_core` module |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add type stubs for expression builder types |
| `rust/stoat_ferret_core/tests/test_expression.rs` | Create | Unit tests and proptest for expression engine |

## Implementation Stages

### Stage 1: Expression AST and Serialization

1. Create `rust/stoat_ferret_core/src/ffmpeg/expression.rs` with:
   - `Expr` enum: variants for Literal (number), Variable (t, PTS, n), FunctionCall (between, if, min, max), BinaryOp (+, -, *, /)
   - `ExprFunction` enum: whitelisted function names (Between, If, Min, Max, optionally Gte, Lte, Eq, Gt, Lt)
   - `ExprVariable` enum: T, PTS, N
   - `BinaryOp` enum: Add, Sub, Mul, Div
   - `impl Display for Expr` producing valid FFmpeg expression syntax
   - Validation: unknown function names rejected at construction time
2. Add `pub mod expression;` to `rust/stoat_ferret_core/src/ffmpeg/mod.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_expression
```

### Stage 2: Builder API

1. Add `ExpressionBuilder` struct with fluent API:
   - `fn new() -> Self`
   - Methods: `literal()`, `variable()`, `function()`, `add()`, `sub()`, `mul()`, `div()`
   - Uses `PyRefMut<'_, Self>` return type for method chaining (LRN-001)
   - `fn build() -> Result<Expr, ExpressionError>`
2. Add convenience builders: `enable_between(start, end)`, `alpha_fade_in(start, duration)`, `alpha_fade_out(end, duration)`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_expression
```

### Stage 3: PyO3 Bindings and Type Stubs

1. Add `#[pyclass]` and `#[pymethods]` to ExpressionBuilder and Expr types
   - Use `py_` prefix with `#[pyo3(name = "...")]` convention
   - Add `#[gen_stub_pyclass]` annotations
2. Register types in `lib.rs` PyO3 module
3. Generate and update type stubs:
   ```bash
   cd rust/stoat_ferret_core && cargo run --bin stub_gen
   ```
4. Update `stubs/stoat_ferret_core/_core.pyi` with expression type signatures

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test
uv run python -c "from stoat_ferret_core import ExpressionBuilder"
uv run python scripts/verify_stubs.py
```

### Stage 4: Property-Based Tests

1. Create `rust/stoat_ferret_core/tests/test_expression.rs` with:
   - Unit tests for each expression type (literal, variable, function, binary op)
   - Proptest strategies generating random valid expression trees
   - Proptest verifying all generated expressions serialize to non-empty, parseable strings
   - Edge case tests: deeply nested expressions, all operators, all functions

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test test_expression
```

## Test Infrastructure Updates

- Add `proptest` to `[dev-dependencies]` in `rust/stoat_ferret_core/Cargo.toml` if not present
- Expression proptest strategies may be reused by downstream features (drawtext, composition)

## Quality Gates

```bash
cd rust/stoat_ferret_core && cargo clippy -- -D warnings
cd rust/stoat_ferret_core && cargo test
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Expression subset scope creep — bounded by whitelist: `{between, if, min, max}` + arithmetic + `{t, PTS, n}`. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: implement FFmpeg filter expression engine in Rust

Add type-safe expression AST with builder API, serialization to
valid FFmpeg syntax, property-based tests via proptest, and PyO3
bindings with type stubs. Covers BL-037.
```