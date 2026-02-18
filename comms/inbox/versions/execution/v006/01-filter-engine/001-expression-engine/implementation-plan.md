# Implementation Plan: expression-engine

## Overview

Create a new `expression.rs` module in the Rust FFmpeg crate implementing a type-safe expression builder for FFmpeg filter expressions. The module defines an `Expr` enum with variants for constants, variables, binary/unary operations, functions, and conditionals. All types get PyO3 bindings and proptest validation.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/expression.rs` | Create | Expression type system, builder, Display serialization |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Modify | Register `expression` submodule |
| `rust/stoat_ferret_core/src/lib.rs` | Modify | Export expression types and PyO3 bindings |
| `stubs/stoat_ferret_core/_core.pyi` | Modify | Add expression type stubs (via stub_gen) |
| `tests/test_pyo3_bindings.py` | Modify | Add Python-side expression tests |
| `AGENTS.md` | Modify | Add expression module to Project Structure (Impact #1) |

## Test Files

`tests/test_pyo3_bindings.py`

## Implementation Stages

### Stage 1: Expression Type System

1. Create `rust/stoat_ferret_core/src/ffmpeg/expression.rs`
2. Define `Variable` enum: `T`, `N`, `Pos`, `W`, `H`, `TextW`, `TextH`, `LineH`, `MainW`, `MainH` (and others as needed)
3. Define `BinaryOp` enum: `Add`, `Sub`, `Mul`, `Div`, `Pow`
4. Define `UnaryOp` enum: `Neg`, `Pos`
5. Define `FuncName` enum: `Between`, `If`, `IfNot`, `Lt`, `Gt`, `Eq`, `Gte`, `Lte`, `Clip`, `Abs`, `Min`, `Max`, `Mod`, `Not`
6. Define `Expr` enum: `Const(f64)`, `Var(Variable)`, `BinaryOp(BinaryOp, Box<Expr>, Box<Expr>)`, `UnaryOp(UnaryOp, Box<Expr>)`, `Func(FuncName, Vec<Expr>)`, `If(Box<Expr>, Box<Expr>, Box<Expr>)`
7. Implement `Display` for all types (FFmpeg syntax serialization)
8. Register module in `ffmpeg/mod.rs`

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- expression
```

### Stage 2: Builder API and Convenience Functions

1. Add builder functions: `Expr::constant(f64)`, `Expr::var(Variable)`, `Expr::between(expr, min, max)`, `Expr::if_then_else(cond, then, else)`, etc.
2. Add operator overloading via `std::ops` traits (Add, Sub, Mul, Div) for ergonomic expression building
3. Add function arity validation (e.g., `between` requires exactly 3 args)

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- expression
```

### Stage 3: Proptest Validation

1. Create proptest strategies using `prop_oneof!` for `Expr` variants
2. Use `prop_compose!` for constrained generation (avoid deep recursion)
3. Add roundtrip test: generate `Expr` -> `to_string()` -> verify non-empty, no NaN/Infinity in output
4. Add structural tests for specific expression patterns

**Verification:**
```bash
cd rust/stoat_ferret_core && cargo test -- expression
```

### Stage 4: PyO3 Bindings

1. Add `#[pyclass]` and `#[pymethods]` to expression types
2. Use `PyRefMut<'_, Self>` for builder method chaining
3. Export via `lib.rs`
4. Regenerate stubs: `cargo run --bin stub_gen`
5. Verify stubs: `uv run python scripts/verify_stubs.py`
6. Add Python-side tests in `tests/test_pyo3_bindings.py`
7. Update AGENTS.md Project Structure (Impact #1)

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

- Expression type hierarchy complexity — mitigate with focused core function set (13 of 40). See `006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat(rust): add FFmpeg filter expression engine with proptest validation

BL-037: Type-safe expression builder with Expr enum, Display serialization,
proptest roundtrip validation, and PyO3 bindings.
```