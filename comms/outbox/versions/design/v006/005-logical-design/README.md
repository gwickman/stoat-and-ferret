# 005-Logical Design: v006 — Effects Engine Foundation

Proposed structure: 3 themes with 9 features total covering all 7 backlog items (BL-037–BL-043). The design follows infrastructure-first ordering (LRN-019), splits BL-043 into two features based on the impact assessment's substantial impacts, and applies established patterns (PyRefMut builders, DI via create_app, record-replay contract tests, handoff documents) throughout.

## Theme Overview

| # | Theme | Goal | Features | Backlog Items |
|---|-------|------|----------|---------------|
| 01 | `01-filter-expression-infrastructure` | Build foundational Rust expression engine and graph validation | 2 | BL-037, BL-038 |
| 02 | `02-filter-builders-and-composition` | Implement composition API, drawtext builder, and speed control | 3 | BL-039, BL-040, BL-041 |
| 03 | `03-effects-api-layer` | Bridge Rust engine to Python API with discovery and application endpoints | 3 (+1 model feature from BL-043 split) | BL-042, BL-043 |

## Key Decisions

1. **3-theme structure** following the natural dependency chain: infrastructure → builders → API. Each theme has a clear scope boundary (Rust foundations, Rust builders, Python API).

2. **BL-043 split into two features**: The impact assessment identified clip effects model design (impact #9) as substantial. Feature 002 handles the multi-layer schema change; Feature 003 builds the endpoint on top. This prevents a single oversized feature.

3. **Effect registry designed for extensibility**: Impact #13 flagged the registry as substantial. Feature 001 in Theme 03 establishes the pattern before BL-043 builds on it. Designed to support v007 Effect Workshop.

4. **Expression engine scoped to downstream needs**: Only whitelist FFmpeg functions actually needed by drawtext (BL-040) and speed control (BL-041). Extensible but not over-scoped.

5. **All Rust features include PyO3 bindings inline**: Per AGENTS.md incremental binding rule and LRN-001 (`PyRefMut` chaining pattern).

## Dependencies

**Theme-level:** Theme 01 → Theme 02 → Theme 03 (strictly sequential).

**Feature-level within themes:**
- Theme 01: Features 001 and 002 are independent (can execute in parallel within the theme)
- Theme 02: Feature 001 (composition) first, then Feature 002 (drawtext), then Feature 003 (speed control)
- Theme 03: Feature 001 (discovery) → Feature 002 (clip model) → Feature 003 (apply endpoint)

**Rationale:** Infrastructure-first (LRN-019). Handoff documents (LRN-025) chain features within and across themes for zero-rework sequencing.

## Risks and Unknowns

Items needing investigation in Task 006:

| Risk | Severity | Summary |
|------|----------|---------|
| Clip effects model design | High | No effects field exists on any layer. Multi-layer schema change needs design. |
| Effect registry pattern | High | No precedent in codebase. Must be extensible for v007. |
| Research gaps (Task 004 partial) | Medium | FFmpeg expression subset, graph validation rules unresolved. Addressable during implementation. |
| Expression engine scope creep | Medium | FFmpeg expression language is extensive. Scope to downstream needs only. |
| Rust coverage gap | Medium | At 75% vs 90% target. New code must have comprehensive tests. |
| BL-043 dual substantial dependency | Medium | Depends on both substantial impacts being resolved first. |
| Contract tests need FFmpeg in CI | Low | Existing CI setup should suffice. Single matrix entry per LRN-015. |
| Drop-frame timecode vs speed control | Low | Likely no intersection (PTS is frame-rate-independent). |

Full details: [`risks-and-unknowns.md`](./risks-and-unknowns.md)

## Artifacts

| File | Description |
|------|-------------|
| [`logical-design.md`](./logical-design.md) | Complete logical design with theme/feature breakdowns, execution order, and research sources |
| [`test-strategy.md`](./test-strategy.md) | Test requirements per feature (unit, property-based, contract, system, parity) |
| [`risks-and-unknowns.md`](./risks-and-unknowns.md) | All identified risks for Task 006 critical thinking review |
