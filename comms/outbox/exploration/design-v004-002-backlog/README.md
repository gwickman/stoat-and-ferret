# Exploration: design-v004-002-backlog — Backlog Analysis

v004 scope includes 13 mandatory backlog items (8 new, 5 existing) focused on testing infrastructure, quality verification, and developer experience. The v003 retrospective confirmed all 15/15 features completed with 53/53 acceptance criteria passed, validating the exploration-first and sequential-execution approach. Key tech debt carried forward includes async scan (now BL-027), search behavior inconsistency (BL-016), and stub consolidation.

## Backlog Overview

- **Total items**: 13 (all mandatory, no deferrals)
- **Priority distribution**: P1 x4, P2 x5, P3 x4
- **Size distribution**: L x1, M x10, S x2
- **New items (v004)**: BL-020 through BL-027
- **Existing/retagged**: BL-009, BL-010, BL-012, BL-014, BL-016

### By Priority

| Priority | Items | Focus |
|----------|-------|-------|
| P1 | BL-020, BL-021, BL-022, BL-023 | Test infrastructure (doubles, DI, fixtures, black box tests) |
| P2 | BL-024, BL-025, BL-027, BL-009, BL-014 | Quality verification, security, async scan, process, Docker |
| P3 | BL-026, BL-010, BL-012, BL-016 | Benchmarks, Rust coverage, coverage gaps, search consistency |

## Previous Version

- **Version**: v003
- **Status**: Completed (2026-01-28)
- **Retrospective**: `comms/outbox/versions/execution/v003/retrospective.md`
- **Result**: 4 themes, 15 features, 53 acceptance criteria — all passed
- **Test count**: 395 (up from ~258), coverage 93%

## Key Learnings Applicable to v004

1. **Repository protocol pattern** validated in v003 — reuse for InMemoryProjectStorage and InMemoryJobQueue (BL-020)
2. **Dependency injection with FastAPI** (`Depends` + `Annotated`) — extend for create_app() injectable dependencies (BL-021)
3. **Contract test pattern** from v003 — apply to FFmpeg executor contract tests (BL-024) and search behavior unification (BL-016)
4. **Exploration-first approach** — continue for v004 themes
5. **Security whitelist pattern** (LRN-003) — directly applicable to security audit (BL-025)

## Tech Debt From v003

| Item | Priority | v004 Backlog |
|------|----------|--------------|
| Async job queue for scan | Medium | BL-027 (addressed) |
| Stub file consolidation | Low | Not directly scoped |
| True total count for pagination | Low | Not scoped |
| Structured logging integration | Low | Not scoped |
| C4 documentation regeneration | Medium | Not scoped |

## Missing Items

None. All 13 backlog items were successfully retrieved.

## Quality Assessment Summary

All 13 items had formulaic use cases ("This feature addresses: {title}...") which were replaced with authentic user scenarios via notes field updates. See backlog-details.md for per-item assessment.
