// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Grant Wickman

//! Bespoke recursive-descent expression parser for procedural image generation.
//!
//! Grammar:
//!   expr    := add_sub
//!   add_sub := mul_div ( ('+' | '-') mul_div )*
//!   mul_div := unary   ( ('*' | '/' | '%') unary )*
//!   unary   := '-' unary | power
//!   power   := primary ('^' unary)?
//!   primary := NUMBER | IDENT | '(' expr ')' | fn_call | if_expr

use std::fmt;

// ──────────────────────────────────────────────────────────── tokens ────

#[derive(Debug, Clone, PartialEq)]
enum Token {
    Number(f64),
    Ident(String),
    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    Caret,
    LParen,
    RParen,
    Comma,
    Eof,
}

fn tokenize(input: &str) -> Result<Vec<Token>, ParseError> {
    let mut tokens = Vec::new();
    let chars: Vec<char> = input.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        match chars[i] {
            ' ' | '\t' | '\n' | '\r' => {
                i += 1;
            }
            '+' => {
                tokens.push(Token::Plus);
                i += 1;
            }
            '-' => {
                tokens.push(Token::Minus);
                i += 1;
            }
            '*' => {
                tokens.push(Token::Star);
                i += 1;
            }
            '/' => {
                tokens.push(Token::Slash);
                i += 1;
            }
            '%' => {
                tokens.push(Token::Percent);
                i += 1;
            }
            '^' => {
                tokens.push(Token::Caret);
                i += 1;
            }
            '(' => {
                tokens.push(Token::LParen);
                i += 1;
            }
            ')' => {
                tokens.push(Token::RParen);
                i += 1;
            }
            ',' => {
                tokens.push(Token::Comma);
                i += 1;
            }
            c if c.is_ascii_digit() || c == '.' => {
                let start = i;
                while i < chars.len() && (chars[i].is_ascii_digit() || chars[i] == '.') {
                    i += 1;
                }
                if i < chars.len() && (chars[i] == 'e' || chars[i] == 'E') {
                    i += 1;
                    if i < chars.len() && (chars[i] == '+' || chars[i] == '-') {
                        i += 1;
                    }
                    while i < chars.len() && chars[i].is_ascii_digit() {
                        i += 1;
                    }
                }
                let s: String = chars[start..i].iter().collect();
                let n: f64 = s
                    .parse()
                    .map_err(|_| ParseError::UnexpectedToken(s.clone()))?;
                tokens.push(Token::Number(n));
            }
            c if c.is_alphabetic() || c == '_' => {
                let start = i;
                while i < chars.len() && (chars[i].is_alphanumeric() || chars[i] == '_') {
                    i += 1;
                }
                let s: String = chars[start..i].iter().collect();
                tokens.push(Token::Ident(s));
            }
            c => {
                return Err(ParseError::UnexpectedToken(c.to_string()));
            }
        }
    }
    tokens.push(Token::Eof);
    Ok(tokens)
}

// ─────────────────────────────────────────────────────────────── AST ────

#[derive(Debug, Clone, PartialEq)]
pub enum VarKind {
    X,
    Y,
    T,
}

#[derive(Debug, Clone, PartialEq)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Pow,
}

#[derive(Debug, Clone, PartialEq)]
pub enum FnName {
    Sin,
    Cos,
    Tan,
    Atan2,
    Hypot,
    Sqrt,
    Exp,
    Log,
    Abs,
    Floor,
    Ceil,
    Pow,
    Mod,
}

#[derive(Debug, Clone)]
pub enum Expr {
    Literal(f64),
    Var(VarKind),
    BinOp(BinOp, Box<Expr>, Box<Expr>),
    UnaryNeg(Box<Expr>),
    FnCall(FnName, Vec<Expr>),
    IfExpr(Box<Expr>, Box<Expr>, Box<Expr>),
}

// ──────────────────────────────────────────────────────────── errors ────

#[derive(Debug, Clone, PartialEq)]
pub enum ParseError {
    UnexpectedToken(String),
    UnknownIdent(String),
    MaxDepthExceeded,
    UnexpectedEnd,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::UnexpectedToken(s) => write!(f, "unexpected token: {s}"),
            ParseError::UnknownIdent(s) => write!(f, "unknown identifier: {s}"),
            ParseError::MaxDepthExceeded => write!(f, "expression depth limit exceeded (max 32)"),
            ParseError::UnexpectedEnd => write!(f, "unexpected end of expression"),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum EvalError {
    BudgetExceeded,
}

impl fmt::Display for EvalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            EvalError::BudgetExceeded => write!(f, "eval step budget exceeded"),
        }
    }
}

// ─────────────────────────────────────────────────────────── parser ─────

const MAX_DEPTH: usize = 32;

struct Parser {
    tokens: Vec<Token>,
    pos: usize,
    depth: usize,
}

impl Parser {
    fn new(tokens: Vec<Token>) -> Self {
        Self {
            tokens,
            pos: 0,
            depth: 0,
        }
    }

    fn peek(&self) -> &Token {
        self.tokens
            .get(self.pos)
            .unwrap_or(&Token::Eof)
    }

    fn advance(&mut self) -> Token {
        let t = self.tokens.get(self.pos).cloned().unwrap_or(Token::Eof);
        if self.pos + 1 < self.tokens.len() {
            self.pos += 1;
        }
        t
    }

    fn enter_depth(&mut self) -> Result<(), ParseError> {
        self.depth += 1;
        if self.depth > MAX_DEPTH {
            return Err(ParseError::MaxDepthExceeded);
        }
        Ok(())
    }

    fn leave_depth(&mut self) {
        if self.depth > 0 {
            self.depth -= 1;
        }
    }

    fn parse_expr(&mut self) -> Result<Expr, ParseError> {
        self.enter_depth()?;
        let r = self.parse_add_sub();
        self.leave_depth();
        r
    }

    fn parse_add_sub(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.parse_mul_div()?;
        loop {
            match self.peek() {
                Token::Plus => {
                    self.advance();
                    let right = self.parse_mul_div()?;
                    left = Expr::BinOp(BinOp::Add, Box::new(left), Box::new(right));
                }
                Token::Minus => {
                    self.advance();
                    let right = self.parse_mul_div()?;
                    left = Expr::BinOp(BinOp::Sub, Box::new(left), Box::new(right));
                }
                _ => break,
            }
        }
        Ok(left)
    }

    fn parse_mul_div(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.parse_unary()?;
        loop {
            match self.peek() {
                Token::Star => {
                    self.advance();
                    let right = self.parse_unary()?;
                    left = Expr::BinOp(BinOp::Mul, Box::new(left), Box::new(right));
                }
                Token::Slash => {
                    self.advance();
                    let right = self.parse_unary()?;
                    left = Expr::BinOp(BinOp::Div, Box::new(left), Box::new(right));
                }
                Token::Percent => {
                    self.advance();
                    let right = self.parse_unary()?;
                    left = Expr::BinOp(BinOp::Mod, Box::new(left), Box::new(right));
                }
                _ => break,
            }
        }
        Ok(left)
    }

    fn parse_unary(&mut self) -> Result<Expr, ParseError> {
        if matches!(self.peek(), Token::Minus) {
            self.advance();
            let e = self.parse_power()?;
            Ok(Expr::UnaryNeg(Box::new(e)))
        } else {
            self.parse_power()
        }
    }

    fn parse_power(&mut self) -> Result<Expr, ParseError> {
        let base = self.parse_primary()?;
        if matches!(self.peek(), Token::Caret) {
            self.advance();
            let exp = self.parse_unary()?;
            Ok(Expr::BinOp(BinOp::Pow, Box::new(base), Box::new(exp)))
        } else {
            Ok(base)
        }
    }

    fn parse_primary(&mut self) -> Result<Expr, ParseError> {
        match self.peek().clone() {
            Token::Number(n) => {
                self.advance();
                Ok(Expr::Literal(n))
            }
            Token::LParen => {
                self.advance();
                let e = self.parse_expr()?;
                match self.peek() {
                    Token::RParen => {
                        self.advance();
                    }
                    other => {
                        return Err(ParseError::UnexpectedToken(format!("{other:?}")));
                    }
                }
                Ok(e)
            }
            Token::Ident(name) => {
                let name = name.clone();
                self.advance();
                if matches!(self.peek(), Token::LParen) {
                    self.parse_fn_call(name)
                } else {
                    match name.as_str() {
                        "x" => Ok(Expr::Var(VarKind::X)),
                        "y" => Ok(Expr::Var(VarKind::Y)),
                        "t" => Ok(Expr::Var(VarKind::T)),
                        _ => Err(ParseError::UnknownIdent(name)),
                    }
                }
            }
            Token::Eof => Err(ParseError::UnexpectedEnd),
            other => Err(ParseError::UnexpectedToken(format!("{other:?}"))),
        }
    }

    fn parse_fn_call(&mut self, name: String) -> Result<Expr, ParseError> {
        self.advance(); // consume '('

        if name == "if" {
            let cond = self.parse_expr()?;
            match self.peek() {
                Token::Comma => {
                    self.advance();
                }
                other => {
                    return Err(ParseError::UnexpectedToken(format!("{other:?}")));
                }
            }
            let then_e = self.parse_expr()?;
            match self.peek() {
                Token::Comma => {
                    self.advance();
                }
                other => {
                    return Err(ParseError::UnexpectedToken(format!("{other:?}")));
                }
            }
            let else_e = self.parse_expr()?;
            match self.peek() {
                Token::RParen => {
                    self.advance();
                }
                other => {
                    return Err(ParseError::UnexpectedToken(format!("{other:?}")));
                }
            }
            return Ok(Expr::IfExpr(
                Box::new(cond),
                Box::new(then_e),
                Box::new(else_e),
            ));
        }

        let fn_name = match name.as_str() {
            "sin" => FnName::Sin,
            "cos" => FnName::Cos,
            "tan" => FnName::Tan,
            "atan2" => FnName::Atan2,
            "hypot" => FnName::Hypot,
            "sqrt" => FnName::Sqrt,
            "exp" => FnName::Exp,
            "log" => FnName::Log,
            "abs" => FnName::Abs,
            "floor" => FnName::Floor,
            "ceil" => FnName::Ceil,
            "pow" => FnName::Pow,
            "mod" => FnName::Mod,
            _ => return Err(ParseError::UnknownIdent(name)),
        };

        let mut args = Vec::new();
        if !matches!(self.peek(), Token::RParen) {
            args.push(self.parse_expr()?);
            while matches!(self.peek(), Token::Comma) {
                self.advance();
                args.push(self.parse_expr()?);
            }
        }

        match self.peek() {
            Token::RParen => {
                self.advance();
            }
            other => {
                return Err(ParseError::UnexpectedToken(format!("{other:?}")));
            }
        }

        Ok(Expr::FnCall(fn_name, args))
    }
}

/// Parse an expression string into an AST.
///
/// Rejects expressions with depth > 32 at parse time.
pub fn parse(expr: &str) -> Result<Expr, ParseError> {
    let tokens = tokenize(expr)?;
    let mut parser = Parser::new(tokens);
    let ast = parser.parse_expr()?;
    if !matches!(parser.peek(), Token::Eof) {
        return Err(ParseError::UnexpectedToken(format!("{:?}", parser.peek())));
    }
    Ok(ast)
}

// ─────────────────────────────────────────────────────────── eval ────

/// Evaluate the AST at (x, y, t), decrementing `budget` for each node.
///
/// Returns `EvalError::BudgetExceeded` when budget reaches 0.
/// Pow exponent is clamped to [-100, 100] to prevent overflow.
pub fn eval(
    expr: &Expr,
    x: f64,
    y: f64,
    t: f64,
    budget: &mut usize,
) -> Result<f64, EvalError> {
    if *budget == 0 {
        return Err(EvalError::BudgetExceeded);
    }
    *budget -= 1;

    match expr {
        Expr::Literal(n) => Ok(*n),
        Expr::Var(v) => match v {
            VarKind::X => Ok(x),
            VarKind::Y => Ok(y),
            VarKind::T => Ok(t),
        },
        Expr::UnaryNeg(e) => Ok(-eval(e, x, y, t, budget)?),
        Expr::BinOp(op, l, r) => {
            let lv = eval(l, x, y, t, budget)?;
            let rv = eval(r, x, y, t, budget)?;
            match op {
                BinOp::Add => Ok(lv + rv),
                BinOp::Sub => Ok(lv - rv),
                BinOp::Mul => Ok(lv * rv),
                BinOp::Div => {
                    if rv == 0.0 {
                        Ok(0.0)
                    } else {
                        Ok(lv / rv)
                    }
                }
                BinOp::Mod => {
                    if rv == 0.0 {
                        Ok(0.0)
                    } else {
                        Ok(lv % rv)
                    }
                }
                BinOp::Pow => {
                    let rv_clamped = rv.clamp(-100.0, 100.0);
                    Ok(lv.powf(rv_clamped))
                }
            }
        }
        Expr::FnCall(fn_name, args) => {
            match fn_name {
                FnName::Sin => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.sin())
                }
                FnName::Cos => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.cos())
                }
                FnName::Tan => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.tan())
                }
                FnName::Sqrt => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.sqrt())
                }
                FnName::Exp => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.exp())
                }
                FnName::Log => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.ln())
                }
                FnName::Abs => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.abs())
                }
                FnName::Floor => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.floor())
                }
                FnName::Ceil => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.ceil())
                }
                FnName::Atan2 => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    let b = eval(args.get(1).ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.atan2(b))
                }
                FnName::Hypot => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    let b = eval(args.get(1).ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    Ok(a.hypot(b))
                }
                FnName::Pow => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    let b = eval(args.get(1).ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    let b_clamped = b.clamp(-100.0, 100.0);
                    Ok(a.powf(b_clamped))
                }
                FnName::Mod => {
                    let a = eval(args.first().ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    let b = eval(args.get(1).ok_or(EvalError::BudgetExceeded)?, x, y, t, budget)?;
                    if b == 0.0 {
                        Ok(0.0)
                    } else {
                        Ok(a % b)
                    }
                }
            }
        }
        Expr::IfExpr(cond, then_e, else_e) => {
            let c = eval(cond, x, y, t, budget)?;
            if c != 0.0 {
                eval(then_e, x, y, t, budget)
            } else {
                eval(else_e, x, y, t, budget)
            }
        }
    }
}

// ───────────────────────────────────────────────────────────── tests ────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_literal() {
        let e = parse("3.14").unwrap();
        let mut b = 100usize;
        let v = eval(&e, 0.0, 0.0, 0.0, &mut b).unwrap();
        assert!((v - 3.14).abs() < 1e-9);
    }

    #[test]
    fn test_parse_vars() {
        let e = parse("x+y+t").unwrap();
        let mut b = 100usize;
        let v = eval(&e, 0.1, 0.2, 0.3, &mut b).unwrap();
        assert!((v - 0.6).abs() < 1e-9, "got {v}");
    }

    #[test]
    fn test_parse_sin() {
        let e = parse("sin(x)").unwrap();
        let mut b = 100usize;
        let v = eval(&e, 1.0, 0.0, 0.0, &mut b).unwrap();
        assert!((v - 1.0_f64.sin()).abs() < 1e-9);
    }

    #[test]
    fn test_parse_hypot() {
        let e = parse("hypot(x-0.5, y-0.5)").unwrap();
        let mut b = 100usize;
        let v = eval(&e, 0.5, 0.5, 0.0, &mut b).unwrap();
        assert!(v.abs() < 1e-9, "center should be ~0, got {v}");
    }

    #[test]
    fn test_pow_exponent_clamped() {
        let e = parse("2^200").unwrap();
        let mut b = 100usize;
        let v = eval(&e, 0.0, 0.0, 0.0, &mut b).unwrap();
        // With clamp to 100: 2^100 ≈ 1.27e30, not infinity
        assert!(v.is_finite(), "pow should not overflow with clamped exponent, got {v}");
        assert!(v < 2.0_f64.powi(101), "exponent not clamped: {v}");
    }

    #[test]
    fn test_max_depth_exceeded() {
        // 33 levels of nesting via parentheses
        let expr = "((((((((((((((((((((((((((((((((((x))))))))))))))))))))))))))))))))))"
            .to_string();
        let result = parse(&expr);
        assert!(
            matches!(result, Err(ParseError::MaxDepthExceeded)),
            "expected MaxDepthExceeded, got {result:?}"
        );
    }

    #[test]
    fn test_eval_budget_exceeded() {
        let e = parse("x+x").unwrap();
        let mut b = 1usize;
        // BinOp consumes 1 budget, then first x gets budget=0
        let result = eval(&e, 0.5, 0.5, 0.0, &mut b);
        assert!(
            matches!(result, Err(EvalError::BudgetExceeded)),
            "expected BudgetExceeded, got {result:?}"
        );
    }

    #[test]
    fn test_if_expr() {
        let e = parse("if(x, 1.0, 0.0)").unwrap();
        let mut b = 100usize;
        let v1 = eval(&e, 1.0, 0.0, 0.0, &mut b).unwrap();
        assert!((v1 - 1.0).abs() < 1e-9, "if(1) should return 1.0");
        let mut b = 100usize;
        let v0 = eval(&e, 0.0, 0.0, 0.0, &mut b).unwrap();
        assert!((v0 - 0.0).abs() < 1e-9, "if(0) should return 0.0");
    }

    #[test]
    fn test_unknown_ident_error() {
        let result = parse("foo");
        assert!(matches!(result, Err(ParseError::UnknownIdent(_))));
    }

    #[test]
    fn test_div_by_zero_returns_zero() {
        let e = parse("x/0").unwrap();
        let mut b = 100usize;
        let v = eval(&e, 1.0, 0.0, 0.0, &mut b).unwrap();
        assert_eq!(v, 0.0, "div-by-zero should return 0.0");
    }
}
