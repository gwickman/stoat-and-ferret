---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
  cargo_clippy: pass
  cargo_test: pass
---
# Completion Report: 001-expression-engine

## Summary

Implemented a type-safe Rust expression builder for FFmpeg filter expressions with proptest validation, PyO3 bindings, and Python type stubs. The module lives at `rust/stoat_ferret_core/src/ffmpeg/expression.rs` and is exposed to Python as `stoat_ferret_core.Expr`.

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001 | Expression types cover enable, alpha, time, and arithmetic expressions | PASS |
| FR-002 | Builder API prevents construction of syntactically invalid expressions at compile time | PASS |
| FR-003 | Expressions serialize to valid FFmpeg filter syntax strings | PASS |
| FR-004 | Property-based tests generate random valid expressions and verify serialization | PASS |
| FR-005 | PyO3 bindings expose expression builder to Python with type stubs | PASS |

## Implementation Details

### Rust Types (expression.rs)

- **`Expr` enum**: `Const(f64)`, `Var(Variable)`, `BinaryOp(BinaryOp, Box<Expr>, Box<Expr>)`, `UnaryOp(UnaryOp, Box<Expr>)`, `Func(FuncName, Vec<Expr>)`
- **`Variable` enum**: T, N, Pts, W, H, Ih, Iw, A, Sar, Dar, Pos (11 FFmpeg variables)
- **`BinaryOp` enum**: Add, Sub, Mul, Div
- **`UnaryOp` enum**: Negate
- **`FuncName` enum**: Between, If, IfNot, Lt, Gt, Eq, Gte, Lte, Clip, Abs, Min, Max, Mod, Not (14 functions, 13 core + ifnot)

### Display Trait

Precedence-aware serialization that minimizes unnecessary parentheses:
- `Expr::constant(2.0) + Expr::var(Variable::T) * Expr::constant(3.0)` serializes to `2+t*3`
- Integer-valued floats serialize without decimal point: `1.0` → `"1"`

### Builder API

- `Expr::constant(f64)`, `Expr::var(Variable)`, `Expr::negate(Expr)`
- `Expr::between(x, min, max)`, `Expr::if_then_else(cond, then, else_)`
- `Expr::lt/gt/eq/gte/lte(a, b)`, `Expr::clip(x, min, max)`
- `Expr::abs(x)`, `Expr::min/max(a, b)`, `Expr::modulo(a, b)`, `Expr::not(x)`
- `Expr::func(FuncName, Vec<Expr>)` with arity validation returning `Result<Expr, ExprError>`
- Operator overloading: `Add`, `Sub`, `Mul`, `Div`, `Neg`

### PyO3 Bindings

- `PyExpr` wrapper struct with `#[pyclass(name = "Expr")]`
- All builder methods exposed as static methods
- Operator overloading: `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__neg__`
- `__repr__` and `__str__` for Python display

### Testing

- **Rust**: 36 unit tests + 4 proptest properties + 7 doc tests = 47 expression-specific tests
- **Python**: 19 test methods in `TestExpr` class covering all Python API surface
- **Proptest properties**:
  - Serialization is non-empty
  - Serialization has balanced parentheses
  - Serialization contains no NaN/Inf
  - Arity validation rejects wrong argument counts

## Files Changed

| File | Change |
|------|--------|
| `rust/stoat_ferret_core/src/ffmpeg/expression.rs` | NEW - Main implementation (~800 lines) |
| `rust/stoat_ferret_core/src/ffmpeg/mod.rs` | Added `pub mod expression;` |
| `rust/stoat_ferret_core/src/lib.rs` | Registered `PyExpr` in pymodule |
| `stubs/stoat_ferret_core/_core.pyi` | Added `Expr` class stubs + `Position`/`Duration` `__new__` |
| `src/stoat_ferret_core/_core.pyi` | Synced from stubs/ |
| `src/stoat_ferret_core/__init__.py` | Added `Expr` to exports |
| `src/stoat_ferret/db/models.py` | Removed obsolete `type: ignore` comments |
| `tests/test_pyo3_bindings.py` | Added `TestExpr` class (19 tests) |
| `AGENTS.md` | Updated project structure description |
| `pyproject.toml` | Added ruff per-file-ignores for auto-generated pyi |

## Sub-tasks

- Impact #1: Updated AGENTS.md with "expressions" in Rust crate description
- Impact #4: Ran `cargo run --bin stub_gen` and `verify_stubs.py` - all types present

## Quality Gate Results

- **ruff check**: All checks passed
- **ruff format**: 103 files already formatted
- **mypy**: Success: no issues found in 44 source files
- **cargo clippy**: No warnings
- **cargo test**: 237 passed (all Rust tests) + 90 doc tests
- **pytest**: 644 passed, 15 skipped, 93.29% coverage
