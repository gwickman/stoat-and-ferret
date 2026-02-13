# Requirements: expression-engine

## Goal

Implement a type-safe FFmpeg filter expression engine in Rust with an AST, builder API, serialization to valid FFmpeg syntax, property-based tests, and PyO3 bindings.

## Background

Backlog Item: BL-037

The current filter system (v001) handles simple key=value parameters only. FFmpeg filter expressions like `enable='between(t,3,5)'`, alpha expressions, and time-based arithmetic have no Rust representation. M2.1 requires a type-safe expression builder that prevents syntactically invalid expressions. Text overlay animations (BL-040), speed control (BL-041), and all v007 effects depend on this foundation.

## Functional Requirements

**FR-001: Expression AST types**
- Implement expression types covering enable, alpha, time, and arithmetic expressions
- AC: All four expression categories have dedicated AST node types with appropriate fields

**FR-002: Builder API**
- Provide a fluent builder API that prevents construction of syntactically invalid expressions at compile time
- Builder uses `PyRefMut<'_, Self>` for method chaining (LRN-001)
- AC: Attempting to construct an invalid expression returns an error; valid expressions build successfully

**FR-003: Expression function whitelist**
- Validate expression function names against a whitelist of known FFmpeg functions
- Required functions: `between`, `if`, `min`, `max`
- Required operators: `+`, `-`, `*`, `/` (arithmetic)
- Required variables: `t` (timestamp seconds), `PTS` (presentation timestamp), `n` (frame number)
- Optional (include if trivial): `gte`, `lte`, `eq`, `gt`, `lt`
- AC: Whitelisted functions accepted; unknown function names rejected with clear error

**FR-004: Serialization**
- Expressions serialize to valid FFmpeg filter syntax strings
- AC: Every expression type produces syntactically correct FFmpeg expression output

**FR-005: PyO3 bindings**
- Expose expression builder to Python with type stubs
- Follow `py_` prefix convention with `#[pyo3(name = "...")]` for clean Python names
- AC: Python code can construct, validate, and serialize expressions identically to Rust

## Non-Functional Requirements

**NFR-001: Extensibility**
- New expression functions can be added via whitelist extension without breaking existing API
- AC: Adding a new function name to the whitelist requires no changes to existing expression types or builder methods

**NFR-002: Test coverage**
- Module-level Rust coverage >90% via comprehensive unit tests and proptest
- AC: `cargo tarpaulin` reports >90% for the expression module

## Out of Scope

- Full FFmpeg expression language (only the subset needed by v006 consumers)
- Runtime expression evaluation (Rust builds expressions; FFmpeg evaluates them)
- Expression optimization or simplification passes

## Test Requirements

- **Unit tests:** Cover all expression types (enable, alpha, time, arithmetic), builder API, serialization
- **Property-based tests:** Proptest generates random valid expression trees and verifies all serialize to syntactically valid FFmpeg expressions
- **PyO3 binding tests:** Verify builder API works identically from Python; method chaining returns self

Reference: `See comms/outbox/versions/design/v006/004-research/ for supporting evidence`
