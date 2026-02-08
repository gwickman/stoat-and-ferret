# Retrospective Insights — v003 for v004

Source: `comms/outbox/versions/execution/v003/retrospective.md`

## What Worked Well (Continue in v004)

1. **Repository protocol pattern** — Dual sync/async protocol with contract tests against both SQLite and in-memory implementations ensured consistent behavior. Reuse this pattern for InMemoryProjectStorage (BL-020) and search unification (BL-016).

2. **Exploration-first approach** — Documenting patterns before implementation reduced design decisions during execution and eliminated surprises. Continue for all v004 themes.

3. **Sequential feature execution** — Building features in dependency order (foundations first, consumers second) allowed each feature to build on stable ground. Critical for v004 where test doubles (BL-020) must exist before DI wiring (BL-021), which must exist before black box tests (BL-023).

4. **Dependency injection with FastAPI** — Using `Depends` with `Annotated` type aliases created clean testable code. Directly extends to BL-021's create_app() injectable dependencies.

5. **Quality gates consistency** — ruff, mypy, pytest gates maintained throughout v003. Coverage improved from 91% to 93%. Maintain for v004.

## What Didn't Work (Avoid in v004)

1. **C4 documentation skipped** — Architecture documentation was not regenerated despite significant changes. Still not scoped for v004; risk of documentation drift continues.

2. **Tech debt accumulation** — Several items deferred: async scan, pagination counts, structured logging, stub consolidation. v004 addresses async scan (BL-027) but others remain.

3. **FFmpeg-dependent tests skipped** — 8 tests skipped when FFmpeg unavailable. BL-024 (contract tests) partially addresses this by formalizing the FFmpeg test strategy.

## Tech Debt Addressed vs Deferred

### Addressed in v004
| v003 Debt Item | v004 Backlog |
|----------------|--------------|
| Async job queue for scan | BL-027 |
| InMemory vs FTS5 search inconsistency | BL-016 |

### Still Deferred
| v003 Debt Item | Priority | Notes |
|----------------|----------|-------|
| C4 documentation regeneration | Medium | Architecture changed significantly since last update |
| True total count for pagination | Low | Returns page count only |
| Structured logging integration | Low | structlog included but not integrated with correlation ID |
| Stub file consolidation | Low | Auto-generated and manual stubs coexist |
| Mypy stub priority configuration | Low | Configure mypy to prefer manual stubs |

## Architectural Decisions to Inform v004

1. **Dual sync/async repository** — Validated. Apply to new repositories (Project, Job).
2. **Three-job CI structure** — Validated. Extend for new test types (black box, contract, benchmark).
3. **Rust validation delegation** — Validated. Security audit (BL-025) should verify this delegation is comprehensive.
4. **Route ordering** — Static before dynamic paths in FastAPI. New async scan endpoints must follow this.
5. **Lifespan context manager** — Clean startup/shutdown. Job queue lifecycle should integrate here.

## v003 Statistics (Baseline for v004)

| Metric | v003 Value |
|--------|------------|
| Themes | 4 |
| Features | 15 |
| Tests | 395 |
| Coverage | 93% |
| PRs | 12 (#36-#47) |

## Recommendations for v004 From v003 Retrospective

1. **Leverage health infrastructure** — New dependencies (job queue) should integrate with readiness checks
2. **Use correlation ID** — All logging should include correlation ID for request tracing
3. **Plan async operations upfront** — Design with job queue architecture from start (directly addressed by BL-027)
