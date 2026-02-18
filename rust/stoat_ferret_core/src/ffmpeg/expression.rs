//! FFmpeg filter expression builder.
//!
//! This module provides a type-safe expression builder for FFmpeg filter
//! expressions like `enable='between(t,3,5)'`, alpha expressions, and
//! time-based arithmetic.
//!
//! # Overview
//!
//! - [`Expr`] - Expression tree with variants for constants, variables, operations, and functions
//! - [`Variable`] - FFmpeg built-in variables (t, n, w, h, etc.)
//! - [`BinaryOp`] / [`UnaryOp`] - Arithmetic operators
//! - [`FuncName`] - Supported FFmpeg expression functions
//! - [`PyExpr`] - Python-facing wrapper around [`Expr`]
//!
//! # Examples
//!
//! ```
//! use stoat_ferret_core::ffmpeg::expression::{Expr, Variable};
//!
//! // Build: between(t,3,5)
//! let expr = Expr::between(
//!     Expr::var(Variable::T),
//!     Expr::constant(3.0),
//!     Expr::constant(5.0),
//! );
//! assert_eq!(expr.to_string(), "between(t,3,5)");
//!
//! // Build: if(gt(t,10),0.5,1.0)
//! let expr = Expr::if_then_else(
//!     Expr::gt(Expr::var(Variable::T), Expr::constant(10.0)),
//!     Expr::constant(0.5),
//!     Expr::constant(1.0),
//! );
//! assert_eq!(expr.to_string(), "if(gt(t,10),0.5,1)");
//! ```
//!
//! # Arithmetic operators
//!
//! Expressions support `+`, `-`, `*`, `/` via `std::ops` traits:
//!
//! ```
//! use stoat_ferret_core::ffmpeg::expression::{Expr, Variable};
//!
//! let expr = Expr::var(Variable::T) * Expr::constant(2.0) + Expr::constant(1.0);
//! assert_eq!(expr.to_string(), "t*2+1");
//! ```

use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyclass;
use std::fmt;

/// FFmpeg built-in variables available in expressions.
///
/// These correspond to variables that FFmpeg evaluates at runtime
/// when processing filter expressions.
#[derive(Debug, Clone, PartialEq)]
pub enum Variable {
    /// Current time in seconds.
    T,
    /// Current frame number (starting from 0).
    N,
    /// Current sample position.
    Pos,
    /// Input width.
    W,
    /// Input height.
    H,
    /// Text width (drawtext filter).
    TextW,
    /// Text height (drawtext filter).
    TextH,
    /// Line height (drawtext filter).
    LineH,
    /// Main input width (overlay filter).
    MainW,
    /// Main input height (overlay filter).
    MainH,
}

impl fmt::Display for Variable {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Variable::T => write!(f, "t"),
            Variable::N => write!(f, "n"),
            Variable::Pos => write!(f, "pos"),
            Variable::W => write!(f, "w"),
            Variable::H => write!(f, "h"),
            Variable::TextW => write!(f, "text_w"),
            Variable::TextH => write!(f, "text_h"),
            Variable::LineH => write!(f, "line_h"),
            Variable::MainW => write!(f, "main_w"),
            Variable::MainH => write!(f, "main_h"),
        }
    }
}

/// Binary arithmetic operators for expressions.
#[derive(Debug, Clone, PartialEq)]
pub enum BinaryOp {
    /// Addition (+).
    Add,
    /// Subtraction (-).
    Sub,
    /// Multiplication (*).
    Mul,
    /// Division (/).
    Div,
    /// Exponentiation (pow).
    Pow,
}

/// Unary operators for expressions.
#[derive(Debug, Clone, PartialEq)]
pub enum UnaryOp {
    /// Negation (-x).
    Neg,
}

/// Supported FFmpeg expression functions.
///
/// This covers the 13 core functions needed for enable, alpha,
/// time-based, and conditional expressions.
#[derive(Debug, Clone, PartialEq)]
pub enum FuncName {
    /// `between(x, min, max)` - Returns 1 if min <= x <= max, 0 otherwise.
    Between,
    /// `if(cond, then, else)` - Conditional expression.
    If,
    /// `ifnot(cond, then, else)` - Inverted conditional.
    IfNot,
    /// `lt(x, y)` - Less than.
    Lt,
    /// `gt(x, y)` - Greater than.
    Gt,
    /// `eq(x, y)` - Equal.
    Eq,
    /// `gte(x, y)` - Greater than or equal.
    Gte,
    /// `lte(x, y)` - Less than or equal.
    Lte,
    /// `clip(x, min, max)` - Clamp value to range.
    Clip,
    /// `abs(x)` - Absolute value.
    Abs,
    /// `min(x, y)` - Minimum of two values.
    Min,
    /// `max(x, y)` - Maximum of two values.
    Max,
    /// `mod(x, y)` - Modulo.
    Mod,
    /// `not(x)` - Logical not.
    Not,
}

impl FuncName {
    /// Returns the expected number of arguments for this function.
    fn arity(&self) -> usize {
        match self {
            FuncName::Abs | FuncName::Not => 1,
            FuncName::Lt
            | FuncName::Gt
            | FuncName::Eq
            | FuncName::Gte
            | FuncName::Lte
            | FuncName::Min
            | FuncName::Max
            | FuncName::Mod => 2,
            FuncName::Between | FuncName::If | FuncName::IfNot | FuncName::Clip => 3,
        }
    }
}

impl fmt::Display for FuncName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FuncName::Between => write!(f, "between"),
            FuncName::If => write!(f, "if"),
            FuncName::IfNot => write!(f, "ifnot"),
            FuncName::Lt => write!(f, "lt"),
            FuncName::Gt => write!(f, "gt"),
            FuncName::Eq => write!(f, "eq"),
            FuncName::Gte => write!(f, "gte"),
            FuncName::Lte => write!(f, "lte"),
            FuncName::Clip => write!(f, "clip"),
            FuncName::Abs => write!(f, "abs"),
            FuncName::Min => write!(f, "min"),
            FuncName::Max => write!(f, "max"),
            FuncName::Mod => write!(f, "mod"),
            FuncName::Not => write!(f, "not"),
        }
    }
}

/// A type-safe FFmpeg filter expression tree.
///
/// Expressions are built using constructors and operator overloading,
/// then serialized to FFmpeg syntax via [`Display`].
#[derive(Debug, Clone, PartialEq)]
pub enum Expr {
    /// A constant numeric value.
    Const(f64),
    /// A built-in FFmpeg variable.
    Var(Variable),
    /// A binary arithmetic operation.
    BinaryOp(BinaryOp, Box<Expr>, Box<Expr>),
    /// A unary operation.
    UnaryOp(UnaryOp, Box<Expr>),
    /// A function call with arguments.
    Func(FuncName, Vec<Expr>),
}

// ---- Display (FFmpeg serialization) ----

impl fmt::Display for Expr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Expr::Const(value) => {
                // Format integers without decimal point for cleaner output
                if value.fract() == 0.0 && value.is_finite() {
                    write!(f, "{}", *value as i64)
                } else {
                    write!(f, "{value}")
                }
            }
            Expr::Var(var) => write!(f, "{var}"),
            Expr::BinaryOp(op, left, right) => {
                let op_str = match op {
                    BinaryOp::Add => "+",
                    BinaryOp::Sub => "-",
                    BinaryOp::Mul => "*",
                    BinaryOp::Div => "/",
                    BinaryOp::Pow => "^",
                };
                write_binary_operand(f, left, op)?;
                write!(f, "{op_str}")?;
                write_binary_operand(f, right, op)
            }
            Expr::UnaryOp(op, operand) => match op {
                UnaryOp::Neg => {
                    write!(f, "-")?;
                    match operand.as_ref() {
                        Expr::BinaryOp(..) => write!(f, "({operand})"),
                        _ => write!(f, "{operand}"),
                    }
                }
            },
            Expr::Func(name, args) => {
                write!(f, "{name}(")?;
                for (i, arg) in args.iter().enumerate() {
                    if i > 0 {
                        write!(f, ",")?;
                    }
                    write!(f, "{arg}")?;
                }
                write!(f, ")")
            }
        }
    }
}

/// Writes a binary operand, adding parentheses only when needed for precedence.
fn write_binary_operand(
    f: &mut fmt::Formatter<'_>,
    operand: &Expr,
    parent_op: &BinaryOp,
) -> fmt::Result {
    match operand {
        Expr::BinaryOp(child_op, ..) if needs_parens(child_op, parent_op) => {
            write!(f, "({operand})")
        }
        _ => write!(f, "{operand}"),
    }
}

/// Determines if a child binary operation needs parentheses inside a parent operation.
fn needs_parens(child: &BinaryOp, parent: &BinaryOp) -> bool {
    let precedence = |op: &BinaryOp| -> u8 {
        match op {
            BinaryOp::Add | BinaryOp::Sub => 1,
            BinaryOp::Mul | BinaryOp::Div => 2,
            BinaryOp::Pow => 3,
        }
    };
    precedence(child) < precedence(parent)
}

// ---- Builder API ----

impl Expr {
    /// Creates a constant expression.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::expression::Expr;
    ///
    /// let expr = Expr::constant(3.14);
    /// assert_eq!(expr.to_string(), "3.14");
    /// ```
    #[must_use]
    pub fn constant(value: f64) -> Self {
        Expr::Const(value)
    }

    /// Creates a variable expression.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::expression::{Expr, Variable};
    ///
    /// let expr = Expr::var(Variable::T);
    /// assert_eq!(expr.to_string(), "t");
    /// ```
    #[must_use]
    pub fn var(v: Variable) -> Self {
        Expr::Var(v)
    }

    /// Creates a negation expression.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::expression::{Expr, Variable};
    ///
    /// let expr = Expr::negate(Expr::var(Variable::T));
    /// assert_eq!(expr.to_string(), "-t");
    /// ```
    #[must_use]
    pub fn negate(operand: Expr) -> Self {
        Expr::UnaryOp(UnaryOp::Neg, Box::new(operand))
    }

    /// Creates a `between(x, min, max)` expression.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::expression::{Expr, Variable};
    ///
    /// let expr = Expr::between(
    ///     Expr::var(Variable::T),
    ///     Expr::constant(3.0),
    ///     Expr::constant(5.0),
    /// );
    /// assert_eq!(expr.to_string(), "between(t,3,5)");
    /// ```
    #[must_use]
    pub fn between(x: Expr, min: Expr, max: Expr) -> Self {
        Expr::Func(FuncName::Between, vec![x, min, max])
    }

    /// Creates an `if(cond, then, else)` expression.
    ///
    /// # Examples
    ///
    /// ```
    /// use stoat_ferret_core::ffmpeg::expression::Expr;
    ///
    /// let expr = Expr::if_then_else(
    ///     Expr::constant(1.0),
    ///     Expr::constant(2.0),
    ///     Expr::constant(3.0),
    /// );
    /// assert_eq!(expr.to_string(), "if(1,2,3)");
    /// ```
    #[must_use]
    pub fn if_then_else(cond: Expr, then_expr: Expr, else_expr: Expr) -> Self {
        Expr::Func(FuncName::If, vec![cond, then_expr, else_expr])
    }

    /// Creates an `ifnot(cond, then, else)` expression.
    #[must_use]
    pub fn if_not(cond: Expr, then_expr: Expr, else_expr: Expr) -> Self {
        Expr::Func(FuncName::IfNot, vec![cond, then_expr, else_expr])
    }

    /// Creates a `lt(x, y)` expression.
    #[must_use]
    pub fn lt(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Lt, vec![a, b])
    }

    /// Creates a `gt(x, y)` expression.
    #[must_use]
    pub fn gt(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Gt, vec![a, b])
    }

    /// Creates an `eq(x, y)` equality expression.
    #[must_use]
    pub fn eq_expr(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Eq, vec![a, b])
    }

    /// Creates a `gte(x, y)` expression.
    #[must_use]
    pub fn gte(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Gte, vec![a, b])
    }

    /// Creates a `lte(x, y)` expression.
    #[must_use]
    pub fn lte(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Lte, vec![a, b])
    }

    /// Creates a `clip(x, min, max)` expression.
    #[must_use]
    pub fn clip(x: Expr, min: Expr, max: Expr) -> Self {
        Expr::Func(FuncName::Clip, vec![x, min, max])
    }

    /// Creates an `abs(x)` expression.
    #[must_use]
    pub fn abs(x: Expr) -> Self {
        Expr::Func(FuncName::Abs, vec![x])
    }

    /// Creates a `min(x, y)` expression.
    #[must_use]
    pub fn min(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Min, vec![a, b])
    }

    /// Creates a `max(x, y)` expression.
    #[must_use]
    pub fn max(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Max, vec![a, b])
    }

    /// Creates a `mod(x, y)` expression.
    #[must_use]
    pub fn modulo(a: Expr, b: Expr) -> Self {
        Expr::Func(FuncName::Mod, vec![a, b])
    }

    /// Creates a `not(x)` expression.
    #[must_use]
    #[allow(clippy::should_implement_trait)] // FFmpeg logical not, not std::ops::Not
    pub fn not(x: Expr) -> Self {
        Expr::Func(FuncName::Not, vec![x])
    }

    /// Creates a function expression with arity validation.
    ///
    /// Returns `Err` if the number of arguments doesn't match the function's arity.
    pub fn func(name: FuncName, args: Vec<Expr>) -> Result<Self, ExprError> {
        let expected = name.arity();
        if args.len() != expected {
            return Err(ExprError::ArityMismatch {
                func: name.to_string(),
                expected,
                got: args.len(),
            });
        }
        Ok(Expr::Func(name, args))
    }
}

/// Errors that can occur when building expressions.
#[derive(Debug, Clone, PartialEq)]
pub enum ExprError {
    /// Wrong number of arguments for a function.
    ArityMismatch {
        /// The function name.
        func: String,
        /// Expected argument count.
        expected: usize,
        /// Actual argument count.
        got: usize,
    },
}

impl fmt::Display for ExprError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ExprError::ArityMismatch {
                func,
                expected,
                got,
            } => write!(
                f,
                "function '{func}' expects {expected} arguments, got {got}"
            ),
        }
    }
}

impl std::error::Error for ExprError {}

// ---- Operator overloading ----

impl std::ops::Add for Expr {
    type Output = Expr;
    fn add(self, rhs: Expr) -> Expr {
        Expr::BinaryOp(BinaryOp::Add, Box::new(self), Box::new(rhs))
    }
}

impl std::ops::Sub for Expr {
    type Output = Expr;
    fn sub(self, rhs: Expr) -> Expr {
        Expr::BinaryOp(BinaryOp::Sub, Box::new(self), Box::new(rhs))
    }
}

impl std::ops::Mul for Expr {
    type Output = Expr;
    fn mul(self, rhs: Expr) -> Expr {
        Expr::BinaryOp(BinaryOp::Mul, Box::new(self), Box::new(rhs))
    }
}

impl std::ops::Div for Expr {
    type Output = Expr;
    fn div(self, rhs: Expr) -> Expr {
        Expr::BinaryOp(BinaryOp::Div, Box::new(self), Box::new(rhs))
    }
}

impl std::ops::Neg for Expr {
    type Output = Expr;
    fn neg(self) -> Expr {
        Expr::negate(self)
    }
}

// ---- PyO3 wrapper ----

/// Python-facing wrapper around the Rust [`Expr`] expression tree.
///
/// This struct provides a Python-friendly API for building and serializing
/// FFmpeg filter expressions. Expressions are built using static constructor
/// methods and operator overloading.
#[gen_stub_pyclass]
#[pyclass(name = "Expr")]
#[derive(Debug, Clone)]
pub struct PyExpr {
    inner: Expr,
}

impl PyExpr {
    /// Creates a new `PyExpr` wrapping the given `Expr`.
    pub fn new(expr: Expr) -> Self {
        Self { inner: expr }
    }

    /// Returns a reference to the inner `Expr`.
    pub fn expr(&self) -> &Expr {
        &self.inner
    }
}

#[pymethods]
impl PyExpr {
    /// Creates a constant expression.
    #[staticmethod]
    fn constant(value: f64) -> Self {
        Self::new(Expr::constant(value))
    }

    /// Creates a variable expression from a variable name string.
    ///
    /// Valid names: "t", "n", "pos", "w", "h", "text_w", "text_h",
    /// "line_h", "main_w", "main_h".
    ///
    /// Raises ValueError for unrecognized variable names.
    #[staticmethod]
    fn var(name: &str) -> PyResult<Self> {
        let v = match name {
            "t" => Variable::T,
            "n" => Variable::N,
            "pos" => Variable::Pos,
            "w" => Variable::W,
            "h" => Variable::H,
            "text_w" => Variable::TextW,
            "text_h" => Variable::TextH,
            "line_h" => Variable::LineH,
            "main_w" => Variable::MainW,
            "main_h" => Variable::MainH,
            _ => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "unknown variable: '{name}'"
                )))
            }
        };
        Ok(Self::new(Expr::var(v)))
    }

    /// Creates a negation expression.
    #[staticmethod]
    fn negate(operand: PyExpr) -> Self {
        Self::new(Expr::negate(operand.inner))
    }

    /// Creates a `between(x, min, max)` expression.
    #[staticmethod]
    fn between(x: PyExpr, min: PyExpr, max: PyExpr) -> Self {
        Self::new(Expr::between(x.inner, min.inner, max.inner))
    }

    /// Creates an `if(cond, then, else)` conditional expression.
    #[staticmethod]
    fn if_then_else(cond: PyExpr, then_expr: PyExpr, else_expr: PyExpr) -> Self {
        Self::new(Expr::if_then_else(
            cond.inner,
            then_expr.inner,
            else_expr.inner,
        ))
    }

    /// Creates an `ifnot(cond, then, else)` inverted conditional expression.
    #[staticmethod]
    fn if_not(cond: PyExpr, then_expr: PyExpr, else_expr: PyExpr) -> Self {
        Self::new(Expr::if_not(
            cond.inner,
            then_expr.inner,
            else_expr.inner,
        ))
    }

    /// Creates a `lt(x, y)` less-than expression.
    #[staticmethod]
    fn lt(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::lt(a.inner, b.inner))
    }

    /// Creates a `gt(x, y)` greater-than expression.
    #[staticmethod]
    fn gt(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::gt(a.inner, b.inner))
    }

    /// Creates an `eq(x, y)` equality expression.
    #[staticmethod]
    fn eq_expr(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::eq_expr(a.inner, b.inner))
    }

    /// Creates a `gte(x, y)` greater-than-or-equal expression.
    #[staticmethod]
    fn gte(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::gte(a.inner, b.inner))
    }

    /// Creates a `lte(x, y)` less-than-or-equal expression.
    #[staticmethod]
    fn lte(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::lte(a.inner, b.inner))
    }

    /// Creates a `clip(x, min, max)` clamping expression.
    #[staticmethod]
    fn clip(x: PyExpr, min: PyExpr, max: PyExpr) -> Self {
        Self::new(Expr::clip(x.inner, min.inner, max.inner))
    }

    /// Creates an `abs(x)` absolute value expression.
    #[staticmethod]
    fn abs(x: PyExpr) -> Self {
        Self::new(Expr::abs(x.inner))
    }

    /// Creates a `min(x, y)` minimum expression.
    #[staticmethod]
    #[pyo3(name = "min")]
    fn py_min(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::min(a.inner, b.inner))
    }

    /// Creates a `max(x, y)` maximum expression.
    #[staticmethod]
    #[pyo3(name = "max")]
    fn py_max(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::max(a.inner, b.inner))
    }

    /// Creates a `mod(x, y)` modulo expression.
    #[staticmethod]
    fn modulo(a: PyExpr, b: PyExpr) -> Self {
        Self::new(Expr::modulo(a.inner, b.inner))
    }

    /// Creates a `not(x)` logical not expression.
    #[staticmethod]
    fn not_(x: PyExpr) -> Self {
        Self::new(Expr::not(x.inner))
    }

    /// Adds two expressions.
    fn __add__(&self, other: &PyExpr) -> PyExpr {
        PyExpr::new(self.inner.clone() + other.inner.clone())
    }

    /// Subtracts two expressions.
    fn __sub__(&self, other: &PyExpr) -> PyExpr {
        PyExpr::new(self.inner.clone() - other.inner.clone())
    }

    /// Multiplies two expressions.
    fn __mul__(&self, other: &PyExpr) -> PyExpr {
        PyExpr::new(self.inner.clone() * other.inner.clone())
    }

    /// Divides two expressions.
    fn __truediv__(&self, other: &PyExpr) -> PyExpr {
        PyExpr::new(self.inner.clone() / other.inner.clone())
    }

    /// Negates an expression.
    fn __neg__(&self) -> PyExpr {
        PyExpr::new(-self.inner.clone())
    }

    /// Returns the FFmpeg expression string.
    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    /// Returns a debug representation.
    fn __repr__(&self) -> String {
        format!("Expr({})", self.inner)
    }
}

// ---- Tests ----

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // ---- Unit tests for Display serialization ----

    #[test]
    fn test_const_integer() {
        assert_eq!(Expr::constant(5.0).to_string(), "5");
    }

    #[test]
    fn test_const_float() {
        assert_eq!(Expr::constant(3.14).to_string(), "3.14");
    }

    #[test]
    fn test_const_negative() {
        assert_eq!(Expr::constant(-2.0).to_string(), "-2");
    }

    #[test]
    fn test_const_zero() {
        assert_eq!(Expr::constant(0.0).to_string(), "0");
    }

    #[test]
    fn test_var_t() {
        assert_eq!(Expr::var(Variable::T).to_string(), "t");
    }

    #[test]
    fn test_var_n() {
        assert_eq!(Expr::var(Variable::N).to_string(), "n");
    }

    #[test]
    fn test_var_all() {
        assert_eq!(Expr::var(Variable::Pos).to_string(), "pos");
        assert_eq!(Expr::var(Variable::W).to_string(), "w");
        assert_eq!(Expr::var(Variable::H).to_string(), "h");
        assert_eq!(Expr::var(Variable::TextW).to_string(), "text_w");
        assert_eq!(Expr::var(Variable::TextH).to_string(), "text_h");
        assert_eq!(Expr::var(Variable::LineH).to_string(), "line_h");
        assert_eq!(Expr::var(Variable::MainW).to_string(), "main_w");
        assert_eq!(Expr::var(Variable::MainH).to_string(), "main_h");
    }

    #[test]
    fn test_binary_add() {
        let expr = Expr::var(Variable::T) + Expr::constant(1.0);
        assert_eq!(expr.to_string(), "t+1");
    }

    #[test]
    fn test_binary_sub() {
        let expr = Expr::var(Variable::T) - Expr::constant(1.0);
        assert_eq!(expr.to_string(), "t-1");
    }

    #[test]
    fn test_binary_mul() {
        let expr = Expr::var(Variable::T) * Expr::constant(2.0);
        assert_eq!(expr.to_string(), "t*2");
    }

    #[test]
    fn test_binary_div() {
        let expr = Expr::var(Variable::T) / Expr::constant(2.0);
        assert_eq!(expr.to_string(), "t/2");
    }

    #[test]
    fn test_binary_precedence() {
        // (t + 1) * 2 -> (t+1)*2
        let expr = (Expr::var(Variable::T) + Expr::constant(1.0)) * Expr::constant(2.0);
        assert_eq!(expr.to_string(), "(t+1)*2");
    }

    #[test]
    fn test_binary_no_unnecessary_parens() {
        // t * 2 + 1 -> t*2+1
        let expr = Expr::var(Variable::T) * Expr::constant(2.0) + Expr::constant(1.0);
        assert_eq!(expr.to_string(), "t*2+1");
    }

    #[test]
    fn test_negate_var() {
        let expr = -Expr::var(Variable::T);
        assert_eq!(expr.to_string(), "-t");
    }

    #[test]
    fn test_negate_binary() {
        let expr = -(Expr::var(Variable::T) + Expr::constant(1.0));
        assert_eq!(expr.to_string(), "-(t+1)");
    }

    #[test]
    fn test_between() {
        let expr = Expr::between(
            Expr::var(Variable::T),
            Expr::constant(3.0),
            Expr::constant(5.0),
        );
        assert_eq!(expr.to_string(), "between(t,3,5)");
    }

    #[test]
    fn test_if_then_else() {
        let expr = Expr::if_then_else(
            Expr::gt(Expr::var(Variable::T), Expr::constant(10.0)),
            Expr::constant(0.5),
            Expr::constant(1.0),
        );
        assert_eq!(expr.to_string(), "if(gt(t,10),0.5,1)");
    }

    #[test]
    fn test_if_not() {
        let expr = Expr::if_not(
            Expr::var(Variable::T),
            Expr::constant(1.0),
            Expr::constant(0.0),
        );
        assert_eq!(expr.to_string(), "ifnot(t,1,0)");
    }

    #[test]
    fn test_comparison_functions() {
        assert_eq!(
            Expr::lt(Expr::var(Variable::T), Expr::constant(5.0)).to_string(),
            "lt(t,5)"
        );
        assert_eq!(
            Expr::gt(Expr::var(Variable::T), Expr::constant(5.0)).to_string(),
            "gt(t,5)"
        );
        assert_eq!(
            Expr::eq_expr(Expr::var(Variable::N), Expr::constant(0.0)).to_string(),
            "eq(n,0)"
        );
        assert_eq!(
            Expr::gte(Expr::var(Variable::T), Expr::constant(1.0)).to_string(),
            "gte(t,1)"
        );
        assert_eq!(
            Expr::lte(Expr::var(Variable::T), Expr::constant(10.0)).to_string(),
            "lte(t,10)"
        );
    }

    #[test]
    fn test_clip() {
        let expr = Expr::clip(
            Expr::var(Variable::T),
            Expr::constant(0.0),
            Expr::constant(10.0),
        );
        assert_eq!(expr.to_string(), "clip(t,0,10)");
    }

    #[test]
    fn test_abs() {
        let expr = Expr::abs(Expr::var(Variable::T) - Expr::constant(5.0));
        assert_eq!(expr.to_string(), "abs(t-5)");
    }

    #[test]
    fn test_min_max() {
        assert_eq!(
            Expr::min(Expr::var(Variable::W), Expr::var(Variable::H)).to_string(),
            "min(w,h)"
        );
        assert_eq!(
            Expr::max(Expr::var(Variable::W), Expr::var(Variable::H)).to_string(),
            "max(w,h)"
        );
    }

    #[test]
    fn test_modulo() {
        let expr = Expr::modulo(Expr::var(Variable::N), Expr::constant(2.0));
        assert_eq!(expr.to_string(), "mod(n,2)");
    }

    #[test]
    fn test_not() {
        let expr = Expr::not(Expr::between(
            Expr::var(Variable::T),
            Expr::constant(3.0),
            Expr::constant(5.0),
        ));
        assert_eq!(expr.to_string(), "not(between(t,3,5))");
    }

    // ---- Arity validation ----

    #[test]
    fn test_func_correct_arity() {
        let result = Expr::func(
            FuncName::Between,
            vec![Expr::constant(1.0), Expr::constant(2.0), Expr::constant(3.0)],
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_func_wrong_arity() {
        let result = Expr::func(FuncName::Between, vec![Expr::constant(1.0)]);
        assert_eq!(
            result,
            Err(ExprError::ArityMismatch {
                func: "between".to_string(),
                expected: 3,
                got: 1,
            })
        );
    }

    #[test]
    fn test_func_abs_arity() {
        assert!(Expr::func(FuncName::Abs, vec![Expr::constant(1.0)]).is_ok());
        assert!(Expr::func(FuncName::Abs, vec![Expr::constant(1.0), Expr::constant(2.0)]).is_err());
    }

    #[test]
    fn test_func_lt_arity() {
        assert!(Expr::func(FuncName::Lt, vec![Expr::constant(1.0), Expr::constant(2.0)]).is_ok());
        assert!(Expr::func(FuncName::Lt, vec![Expr::constant(1.0)]).is_err());
    }

    // ---- Complex expression tests ----

    #[test]
    fn test_enable_expression() {
        let expr = Expr::between(
            Expr::var(Variable::T),
            Expr::constant(3.0),
            Expr::constant(5.0),
        );
        assert_eq!(expr.to_string(), "between(t,3,5)");
    }

    #[test]
    fn test_alpha_fade_expression() {
        let expr = Expr::clip(
            Expr::var(Variable::T) / Expr::constant(2.0),
            Expr::constant(0.0),
            Expr::constant(1.0),
        );
        assert_eq!(expr.to_string(), "clip(t/2,0,1)");
    }

    #[test]
    fn test_nested_conditional() {
        let inner = Expr::if_then_else(
            Expr::lt(Expr::var(Variable::T), Expr::constant(20.0)),
            Expr::constant(1.0),
            Expr::constant(0.0),
        );
        let outer = Expr::if_then_else(
            Expr::gt(Expr::var(Variable::T), Expr::constant(10.0)),
            inner,
            Expr::constant(0.0),
        );
        assert_eq!(outer.to_string(), "if(gt(t,10),if(lt(t,20),1,0),0)");
    }

    #[test]
    fn test_expr_error_display() {
        let err = ExprError::ArityMismatch {
            func: "between".to_string(),
            expected: 3,
            got: 1,
        };
        assert_eq!(
            err.to_string(),
            "function 'between' expects 3 arguments, got 1"
        );
    }

    // ---- Proptest ----

    fn arb_variable() -> impl Strategy<Value = Variable> {
        prop_oneof![
            Just(Variable::T),
            Just(Variable::N),
            Just(Variable::Pos),
            Just(Variable::W),
            Just(Variable::H),
            Just(Variable::TextW),
            Just(Variable::TextH),
            Just(Variable::LineH),
            Just(Variable::MainW),
            Just(Variable::MainH),
        ]
    }

    fn arb_func_name() -> impl Strategy<Value = FuncName> {
        prop_oneof![
            Just(FuncName::Between),
            Just(FuncName::If),
            Just(FuncName::IfNot),
            Just(FuncName::Lt),
            Just(FuncName::Gt),
            Just(FuncName::Eq),
            Just(FuncName::Gte),
            Just(FuncName::Lte),
            Just(FuncName::Clip),
            Just(FuncName::Abs),
            Just(FuncName::Min),
            Just(FuncName::Max),
            Just(FuncName::Mod),
            Just(FuncName::Not),
        ]
    }

    fn arb_leaf() -> BoxedStrategy<Expr> {
        prop_oneof![
            (-1000.0f64..1000.0).prop_map(|v| Expr::constant((v * 100.0).round() / 100.0)),
            arb_variable().prop_map(Expr::var),
        ]
        .boxed()
    }

    /// Generates arbitrary expressions with bounded depth to avoid stack overflow.
    fn arb_expr(max_depth: u32) -> BoxedStrategy<Expr> {
        if max_depth == 0 {
            arb_leaf()
        } else {
            let d = max_depth - 1;
            prop_oneof![
                4 => arb_leaf(),
                1 => (arb_expr(d), arb_expr(d)).prop_map(|(a, b)| a + b),
                1 => (arb_expr(d), arb_expr(d)).prop_map(|(a, b)| a * b),
                1 => (arb_expr(d), arb_expr(d)).prop_map(|(a, b)| a - b),
                1 => arb_expr(d).prop_map(|e| -e),
                1 => (arb_expr(d), arb_expr(d), arb_expr(d))
                    .prop_map(|(x, min, max)| Expr::between(x, min, max)),
                1 => (arb_expr(d), arb_expr(d), arb_expr(d))
                    .prop_map(|(c, t, e)| Expr::if_then_else(c, t, e)),
                1 => (arb_func_name(), arb_leaf())
                    .prop_flat_map(|(name, arg)| {
                        let arity = name.arity();
                        let args_strategy: BoxedStrategy<Vec<Expr>> = match arity {
                            1 => Just(vec![arg]).boxed(),
                            2 => arb_leaf().prop_map(move |b| vec![arg.clone(), b]).boxed(),
                            3 => (arb_leaf(), arb_leaf())
                                .prop_map(move |(b, c)| vec![arg.clone(), b, c])
                                .boxed(),
                            _ => unreachable!(),
                        };
                        args_strategy.prop_map(move |args| Expr::Func(name.clone(), args))
                    }),
            ]
            .boxed()
        }
    }

    proptest! {
        /// Property: all generated expressions produce non-empty serialization.
        #[test]
        fn serialization_is_non_empty(expr in arb_expr(2)) {
            let s = expr.to_string();
            prop_assert!(!s.is_empty(), "Expression serialized to empty string: {:?}", expr);
        }

        /// Property: serialized expressions contain no NaN or Infinity.
        #[test]
        fn serialization_has_no_nan_or_inf(expr in arb_expr(2)) {
            let s = expr.to_string();
            prop_assert!(!s.contains("NaN"), "Expression contains NaN: {}", s);
            prop_assert!(!s.contains("inf"), "Expression contains inf: {}", s);
        }

        /// Property: function calls have balanced parentheses.
        #[test]
        fn serialization_has_balanced_parens(expr in arb_expr(2)) {
            let s = expr.to_string();
            let open = s.chars().filter(|&c| c == '(').count();
            let close = s.chars().filter(|&c| c == ')').count();
            prop_assert_eq!(open, close, "Unbalanced parens in: {}", s);
        }

        /// Property: function arity validation works for all functions.
        #[test]
        fn arity_validation_rejects_wrong_count(
            name in arb_func_name(),
            extra_args in proptest::collection::vec(
                (-100.0f64..100.0).prop_map(Expr::constant),
                0..5usize
            )
        ) {
            let expected = name.arity();
            if extra_args.len() != expected {
                let result = Expr::func(name, extra_args);
                prop_assert!(result.is_err());
            }
        }
    }
}
