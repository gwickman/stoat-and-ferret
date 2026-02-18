# Theme: filter-engine

## Goal

Build the foundational Rust filter infrastructure — expression type system, filter graph validation, and composition API. These are the building blocks that all downstream filter builders and API endpoints depend on. Corresponds to M2.1 (Filter Expression Engine). Per LRN-019, infrastructure-first sequencing eliminates rework.

## Design Artifacts

See `comms/outbox/versions/design/v006/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | expression-engine | BL-037 | Type-safe Rust expression builder for FFmpeg filter expressions with proptest validation |
| 002 | graph-validation | BL-038 | Validate FilterGraph pad matching, detect unconnected pads and cycles using Kahn's algorithm |
| 003 | filter-composition | BL-039 | Programmatic chain, branch, and merge composition with automatic pad label management |

## Dependencies

None — this is the first theme. No prior v006 work required.

## Technical Approach

- **Expression engine (BL-037):** Model as `Expr` enum with `Const(f64)`, `Var(Variable)`, `BinaryOp`, `UnaryOp`, `Func(name, args)`, `If(cond, then, else)` variants. Core FFmpeg functions: `between`, `if`, `lt`, `gt`, `eq`, `gte`, `lte`, `clip`, `abs`, `min`, `max`, `mod`, `not`. Proptest for roundtrip validation. See `004-research/external-research.md` Section 1.
- **Graph validation (BL-038):** Kahn's algorithm implemented inline (~30 lines, O(V+E)). Opt-in `validate()` method on FilterGraph — no breaking changes. See `004-research/external-research.md` Section 5.
- **Composition (BL-039):** Chain (sequential), branch (one-to-many), merge (many-to-one) operations with automatic pad label management. Composed graphs pass validation automatically. See `004-research/codebase-patterns.md` for existing FilterGraph patterns.

## Risks

| Risk | Mitigation |
|------|------------|
| FilterGraph backward compatibility | Opt-in `validate()` method; existing `Display`/`to_string()` unchanged. See `006-critical-thinking/risk-assessment.md` |
| Rust coverage threshold | Keep CI at 75%; new code targets >90%. See `006-critical-thinking/risk-assessment.md` |