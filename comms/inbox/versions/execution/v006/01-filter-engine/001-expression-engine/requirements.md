# Requirements: expression-engine

## Goal

Type-safe Rust expression builder for FFmpeg filter expressions with proptest validation.

## Background

Backlog Item: BL-037

The current filter system (v001) handles simple key=value parameters only. FFmpeg filter expressions like `enable='between(t,3,5)'`, alpha expressions, and time-based arithmetic have no Rust representation. M2.1 requires a type-safe expression builder that prevents syntactically invalid expressions. Without this, text overlay animations (M2.2), speed control (M2.3), and all v007 effects cannot be built safely.

This is a greenfield module — no existing expression code exists in the codebase.

## Functional Requirements

### FR-001: Expression Type System

Expression types cover enable, alpha, time, and arithmetic expressions via an `Expr` enum with variants: `Const(f64)`, `Var(Variable)`, `BinaryOp(Op, Box<Expr>, Box<Expr>)`, `UnaryOp(UnaryOp, Box<Expr>)`, `Func(FuncName, Vec<Expr>)`, `If(Box<Expr>, Box<Expr>, Box<Expr>)`.

**Acceptance criteria:** Expression types cover enable, alpha, time, and arithmetic expressions.

### FR-002: Compile-Time Safety

Builder API prevents construction of syntactically invalid expressions at compile time through Rust's type system. Function arities enforced (e.g., `between` requires exactly 3 arguments).

**Acceptance criteria:** Builder API prevents construction of syntactically invalid expressions at compile time.

### FR-003: FFmpeg Serialization

Expressions serialize to valid FFmpeg filter syntax strings via the `Display` trait. Core functions: `between`, `if`, `lt`, `gt`, `eq`, `gte`, `lte`, `clip`, `abs`, `min`, `max`, `mod`, `not` (13 of 40 total FFmpeg functions).

**Acceptance criteria:** Expressions serialize to valid FFmpeg filter syntax strings.

### FR-004: Property-Based Testing

Proptest generates random valid expressions and verifies serialization produces non-empty, syntactically valid strings. Uses manual strategies (`prop_oneof!`, `prop_compose!`) — no proptest-derive.

**Acceptance criteria:** Property-based tests (proptest) generate random valid expressions and verify serialization.

### FR-005: PyO3 Bindings

PyO3 bindings expose expression builder to Python with type stubs. Follow `PyRefMut<'_, Self>` pattern for method chaining (per LRN-001).

**Acceptance criteria:** PyO3 bindings expose expression builder to Python with type stubs.

## Non-Functional Requirements

### NFR-001: Test Coverage

New expression module targets >90% code coverage individually. CI threshold remains at 75%.

### NFR-002: No New Dependencies

No new Cargo dependencies — proptest already exists, no proptest-derive.

## Out of Scope

- Extended FFmpeg functions beyond the 13 core functions (trigonometric, bitwise, state)
- Expression parsing from strings (only building from Rust/Python API)
- Runtime expression evaluation

## Test Requirements

- Unit tests for each expression variant serialization
- Proptest roundtrip: generate arbitrary `Expr` -> serialize -> verify non-empty and structurally valid
- PyO3 binding tests in Python (expression construction and serialization)
- Type stub regeneration and verification

## Sub-tasks

- Impact #1: Update AGENTS.md Project Structure with new Rust submodule names
- Impact #4: Run `cargo run --bin stub_gen` after adding PyO3 bindings

## Reference

See `comms/outbox/versions/design/v006/004-research/` for supporting evidence.