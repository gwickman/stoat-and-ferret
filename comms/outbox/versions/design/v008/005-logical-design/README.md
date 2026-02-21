# Task 005: Logical Design — v008

v008 proposes **2 themes with 4 features total** to achieve "Startup Integrity & CI Stability." All 4 backlog items (BL-055, BL-056, BL-058, BL-062) are mapped — no deferrals. The design wires existing but disconnected infrastructure into the application startup sequence and fixes a flaky E2E test blocking CI reliability.

## Theme Overview

| # | Theme | Goal | Features | Backlog Items |
|---|-------|------|----------|---------------|
| 01 | application-startup-wiring | Wire database, logging, and orphaned settings into FastAPI lifespan startup | 3 | BL-058, BL-056, BL-062 |
| 02 | ci-stability | Fix flaky E2E test for reliable CI signal | 1 | BL-055 |

## Key Decisions

1. **create_tables() over Alembic** for database startup — simpler for current scope (IF NOT EXISTS is idempotent), with Alembic documented as upgrade path per LRN-029.
2. **Async extraction approach** for schema creation — uses existing aiosqlite connection in lifespan rather than run_in_executor bridge.
3. **Type conversion for log_level** — getattr(logging, settings.log_level) bridges the Literal string → int mismatch between Settings and configure_logging().
4. **10,000ms explicit timeout** for E2E fix — matches project's established pattern (scan.spec.ts uses 10000, accessibility.spec.ts uses 15_000).
5. **Test helper consolidation** — 3 duplicate create_tables_async() helpers (with inconsistent DDL coverage) replaced by single shared function per LRN-035.

## Dependencies

**Theme order:** 01-application-startup-wiring → 02-ci-stability (no cross-theme dependencies; priority-based ordering).

**Feature order within Theme 01:** 001-database-startup → 002-logging-startup → 003-orphaned-settings. Rationale:
- Database before logging (DB must exist before logging emits during init — LRN-019)
- Sequential to avoid merge conflicts on shared file (src/stoat_ferret/api/app.py modified by all 3)
- Priority-descending (P0 → P1 → P2)

**Theme 02** has a single feature with no dependencies.

## Risks and Unknowns

Items for investigation in Task 006:

| Risk | Severity | Summary |
|------|----------|---------|
| Logging activation breaks tests | Medium | configure_logging() may add unexpected stdout in tests |
| E2E "10 consecutive runs" AC | Medium | Cannot validate count-based AC in a single PR |
| configure_logging() guard placement | Medium | Before or after _deps_injected guard affects test behavior |
| Schema evolution strategy | Low | create_tables() doesn't handle future schema changes |
| Shared modification point (app.py) | Low | Mitigated by sequential execution order |
| uvicorn log_level format | Low | .lower() conversion assumed complete |
| WebSocket settings access pattern | Low | get_settings() at runtime vs import-time constant |

Full details: [risks-and-unknowns.md](./risks-and-unknowns.md)

## Output Files

- [logical-design.md](./logical-design.md) — Complete theme/feature breakdown with execution order and research sources
- [test-strategy.md](./test-strategy.md) — Per-feature test requirements (~16 new tests)
- [risks-and-unknowns.md](./risks-and-unknowns.md) — 7 risks for Task 006 critical review
