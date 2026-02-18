# Handoff: 001-expression-engine -> Next Feature

## What Was Built

A type-safe FFmpeg expression builder in Rust (`Expr` enum) with PyO3 bindings exposed as `stoat_ferret_core.Expr` in Python.

## Key Design Decisions

1. **Wrapper Pattern for PyO3**: Complex `Expr` enum with `Box<Expr>` fields can't directly implement PyO3 traits. Solution: `PyExpr` struct wraps `Expr` internally, exposed as `Expr` in Python via `#[pyclass(name = "Expr")]`.

2. **No `If` Variant**: The requirements suggested an `If(Box<Expr>, Box<Expr>, Box<Expr>)` variant, but this was merged into `Func(FuncName::If, Vec<Expr>)` for uniformity. The `if_then_else()` convenience constructor handles the 3-argument case.

3. **Precedence-Aware Display**: Binary operations use `needs_parens()` to minimize unnecessary parentheses in serialized output.

4. **Integer Display for Whole Numbers**: `Const(1.0)` serializes as `"1"` not `"1.0"` since FFmpeg treats them identically and the shorter form is conventional.

## How to Use Expressions

### Rust
```rust
use crate::ffmpeg::expression::{Expr, Variable};

let fade = Expr::between(
    Expr::var(Variable::T),
    Expr::constant(3.0),
    Expr::constant(5.0),
);
println!("{fade}"); // "between(t,3,5)"
```

### Python
```python
from stoat_ferret_core import Expr

fade = Expr.between(Expr.var("t"), Expr.constant(3.0), Expr.constant(5.0))
str(fade)  # "between(t,3,5)"
```

## Extension Points

- **Adding Functions**: Add variant to `FuncName` enum, update `Display` match, add arity to `Expr::func()` validation, add convenience constructor.
- **Adding Variables**: Add variant to `Variable` enum, update `from_str()` and `Display`.
- **Adding Binary/Unary Ops**: Add variant to respective enum, update Display and precedence logic.

## Stubs

Both `stubs/stoat_ferret_core/_core.pyi` and `src/stoat_ferret_core/_core.pyi` were updated. Also added missing `__new__` constructors for `Position` and `Duration` classes (pre-existing gap fixed).
