# VERSION DESIGN — v004: Testing Infrastructure & Quality Verification

## Overview

**Version**: v004
**Goal**: Build comprehensive testing and quality verification infrastructure covering black box testing, recording test doubles, contract tests, and quality verification suite (milestones M1.8–M1.9).
**Scope**: 13 backlog items (4 P1, 5 P2, 4 P3) → 5 themes, 15 features.
**Baseline**: v003 completed with 395 tests, 93% Python coverage.
**Target**: ~500 tests, maintain 80%+ Python coverage, establish Rust coverage baseline (90% target).

## Design Artifacts

All design analysis is in the centralized artifact store:

| Artifact | Path |
|----------|------|
| Environment verification | `comms/outbox/versions/design/v004/001-environment/README.md` |
| Backlog analysis | `comms/outbox/versions/design/v004/002-backlog/` |
| Codebase patterns | `comms/outbox/versions/design/v004/004-research/codebase-patterns.md` |
| External research | `comms/outbox/versions/design/v004/004-research/external-research.md` |
| Logical design | `comms/outbox/versions/design/v004/005-logical-design/logical-design.md` |
| Test strategy | `comms/outbox/versions/design/v004/005-logical-design/test-strategy.md` |
| Refined logical design | `comms/outbox/versions/design/v004/006-critical-thinking/refined-logical-design.md` |
| Risk assessment | `comms/outbox/versions/design/v004/006-critical-thinking/risk-assessment.md` |

## Themes

| # | Theme | Goal | Features | Backlog IDs |
|---|-------|------|----------|-------------|
| 01 | test-foundation | Core testing infrastructure: doubles, DI, fixtures | 3 | BL-020, BL-021, BL-022 |
| 02 | blackbox-contract | Black box tests, verified fakes, search unification | 3 | BL-023, BL-024, BL-016 |
| 03 | async-scan | Async job queue for scan operations | 3 | BL-027 (split into 3 features) |
| 04 | security-performance | Security audit and performance benchmarks | 2 | BL-025, BL-026 |
| 05 | devex-coverage | Developer tooling, coverage, Docker testing | 4 | BL-009, BL-010, BL-012, BL-014 |

## Execution Order

### Phase 1: Foundation (Theme 01) — strictly sequential
1. `test-foundation/inmemory-test-doubles` (BL-020)
2. `test-foundation/dependency-injection` (BL-021)
3. `test-foundation/fixture-factory` (BL-022)

### Phase 2: Consumers & Independent Work (Themes 02–05)
4–15. See THEME_INDEX.md and refined-logical-design.md for full ordering.

## Key Design Decisions

- **Deepcopy isolation**: `copy.deepcopy()` for flat scalar dataclasses — negligible overhead (R2 resolved).
- **DI migration**: `create_app()` gets optional params; 4 `dependency_overrides` consolidated.
- **Async scan breaking change**: Safe — no external consumers of scan endpoint (R1 resolved).
- **FTS5 emulation**: Per-token `startswith` matching; full FTS5 emulation unnecessary (R3 resolved).
- **Security audit scope**: `validate_path` gap confirmed; bounded fix of ~20 lines Python (R4 resolved).
- **Rust coverage**: llvm-cov on single CI matrix combo; progressive threshold if baseline < 90%.

## Risk Summary

All 8 risks investigated. 4 downgraded in severity. No blockers. See `006-critical-thinking/risk-assessment.md` for full details.

## Constraints

- v004 is prerequisite for v005 (black box tests validate GUI backend)
- Python 80% coverage minimum, Rust 90% target per AGENTS.md
- Pre-v1.0 API — breaking changes acceptable with test migration
