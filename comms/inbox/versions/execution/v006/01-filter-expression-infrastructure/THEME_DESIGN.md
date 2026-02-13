# Theme: filter-expression-infrastructure

## Goal

Build the foundational Rust infrastructure that all other v006 features depend on — a type-safe expression engine for FFmpeg filter expressions and a graph validation system for verifying filter graph correctness before serialization. These two independent subsystems form the base layer of the effects engine and can execute in parallel.

## Design Artifacts

See `comms/outbox/versions/design/v006/006-critical-thinking/` for full risk analysis.
See `comms/outbox/versions/design/v006/005-logical-design/test-strategy.md` for test requirements.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | expression-engine | BL-037 | Implement type-safe FFmpeg expression AST with builder API, serialization, property-based tests, and PyO3 bindings |
| 002 | graph-validation | BL-038 | Add pad matching validation, unconnected pad detection, and cycle detection to FilterGraph with actionable error messages |

## Dependencies

No upstream theme dependencies — this is the first theme in the execution order.

Both features within this theme are independent of each other: expression-engine (BL-037) and graph-validation (BL-038) have no mutual dependencies and can execute in parallel.

## Technical Approach

**Expression engine (BL-037):**
- Implement a Rust expression AST covering enable, alpha, time, and arithmetic FFmpeg expressions
- Expression function whitelist: `{between, if, min, max}` + arithmetic operators + variables `{t, PTS, n}`
- Builder uses `PyRefMut<'_, Self>` for method chaining (LRN-001)
- Property-based tests via proptest generate random valid expressions and verify serialization
- PyO3 bindings with type stubs (incremental binding rule)

**Graph validation (BL-038):**
- Extends existing `FilterGraph` type in `rust/stoat_ferret_core/src/ffmpeg/filter.rs`
- Validation runs automatically before serialization
- Pad label matching, unconnected pad detection, cycle detection via topological sort
- Error messages include actionable guidance on how to fix the graph

See `comms/outbox/versions/design/v006/004-research/` for evidence.

## Risks

| Risk | Mitigation |
|------|------------|
| FFmpeg expression subset scope creep | Bounded whitelist defined — see `006-critical-thinking/risk-assessment.md` |
| Rust coverage threshold gap (~75% vs 90% target) | All new Rust code must achieve >90% module-level coverage via proptest and unit tests |
| Task 004 research was incomplete | Expression function whitelist derived from downstream consumer analysis; remaining gaps addressable during implementation |