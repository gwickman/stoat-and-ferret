# Logical Design: v008 — Startup Integrity & CI Stability

## Version Overview

**Version:** v008
**Description:** Fix P0 blockers and critical startup wiring gaps so a fresh install starts cleanly with working logging, database, and settings.

**Goals:**
1. Wire database schema creation into application startup (P0)
2. Wire structured logging into application startup (P1)
3. Connect orphaned settings to their consumers (P2)
4. Fix the flaky E2E test blocking CI reliability (P0)

**Scope:** 4 backlog items, 2 themes, 4 features. All items are mandatory per PLAN.md. No deferrals.

---

## Theme 1: 01-application-startup-wiring

**Goal:** Wire existing but disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence, so a fresh application start produces a fully functional system without manual intervention.

**Backlog Items:** BL-058, BL-056, BL-062

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-database-startup | Wire create_tables() into lifespan so database schema is created automatically on startup | BL-058 | None |
| 2 | 002-logging-startup | Call configure_logging() at startup and wire settings.log_level to control log verbosity | BL-056 | 001-database-startup |
| 3 | 003-orphaned-settings | Wire settings.debug to FastAPI and settings.ws_heartbeat_interval to ws.py | BL-062 | 002-logging-startup |

**Rationale for grouping:** All three items share the same modification point (src/stoat_ferret/api/app.py lifespan) and represent the same class of work: connecting existing infrastructure that was built but never wired. Grouping avoids merge conflicts on the shared file by sequencing changes.

**Rationale for feature order:**
- **001-database-startup first:** Database must exist before any other startup activity. Logging may emit during DB init, so DB should be ready first (per LRN-019).
- **002-logging-startup second:** Depends on lifespan structure established by 001. Also modifies app.py lifespan and __main__.py.
- **003-orphaned-settings last:** Smallest change (2-line wiring). Both preceding features touch the same files; sequencing last avoids conflicts. Also lower priority (P2).

---

## Theme 2: 02-ci-stability

**Goal:** Eliminate the flaky E2E test that intermittently blocks CI merges, restoring reliable CI signal for all future development.

**Backlog Items:** BL-055

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-flaky-e2e-fix | Fix toBeHidden() timeout in project-creation.spec.ts so E2E passes reliably | BL-055 | None |

**Rationale for separate theme:** BL-055 is an isolated frontend test change with no code overlap with Theme 1. It touches only gui/e2e/project-creation.spec.ts. Separating it allows independent execution and clear CI validation (AC requires 10 consecutive passing runs).

---

## Execution Order

### Theme Order

1. **01-application-startup-wiring** (first)
2. **02-ci-stability** (second)

**Rationale:** Theme 1 addresses P0 (BL-058) and P1 (BL-056) items that affect application functionality. Theme 2's fix (BL-055) is isolated to test infrastructure. No cross-theme dependencies exist — either order works, but wiring fixes are higher combined priority.

### Feature Order Within Themes

**Theme 1:**
1. 001-database-startup — Foundation; no dependencies
2. 002-logging-startup — Depends on lifespan structure from 001; shared file (app.py)
3. 003-orphaned-settings — Depends on app.py state from 001+002; lowest priority (P2)

**Theme 2:**
1. 001-flaky-e2e-fix — No dependencies; standalone

### Dependency Graph

```
Theme 01:
  001-database-startup
    └── 002-logging-startup
          └── 003-orphaned-settings

Theme 02:
  001-flaky-e2e-fix (independent)
```

---

## Feature Details

### Theme 1, Feature 001: database-startup (BL-058)

**Goal:** Wire create_tables() into the FastAPI lifespan so database schema is created automatically on every startup.

**What changes:**
- Add async schema creation call to lifespan in src/stoat_ferret/api/app.py (inside _deps_injected guard)
- Add create_tables_async() to src/stoat_ferret/db/schema.py using existing aiosqlite connection
- Replace 3 duplicate create_tables_async() helpers in tests with import from schema.py

**Key decisions:**
- Use create_tables() (sync with IF NOT EXISTS) rather than Alembic migrations — simpler for current scope (per LRN-029). Document Alembic as upgrade path.
- Implement async version using aiosqlite connection already open in lifespan — cleaner than run_in_executor bridge.

**End-to-end acceptance criteria:**
- Fresh database becomes fully functional after single application start
- Existing tests continue to pass (test helpers replaced with shared function)

### Theme 1, Feature 002: logging-startup (BL-056)

**Goal:** Call configure_logging() during startup and wire settings.log_level so operators can control log verbosity.

**What changes:**
- Add configure_logging() call in lifespan (src/stoat_ferret/api/app.py)
- Convert settings.log_level (string Literal) to int via getattr(logging, settings.log_level) — type mismatch identified in research
- Change uvicorn log_level from hardcoded "info" to settings.log_level.lower() (src/stoat_ferret/api/__main__.py)

**Key decisions:**
- Call configure_logging() before _deps_injected guard (logging should be available in all modes)
- Type conversion: getattr(logging, settings.log_level) bridges the Literal string → int gap

**End-to-end acceptance criteria:**
- STOAT_LOG_LEVEL=DEBUG produces visible debug output on application start
- All 9 structlog logger.info() calls produce visible structured output at INFO level
- uvicorn respects the configured log level

### Theme 1, Feature 003: orphaned-settings (BL-062)

**Goal:** Wire settings.debug to FastAPI and settings.ws_heartbeat_interval to ws.py so all defined settings are consumed.

**What changes:**
- Add debug=settings.debug to FastAPI() constructor in src/stoat_ferret/api/app.py
- Replace DEFAULT_HEARTBEAT_INTERVAL constant with get_settings().ws_heartbeat_interval in src/stoat_ferret/api/routers/ws.py
- Potentially pass debug to uvicorn.run() in src/stoat_ferret/api/__main__.py

**Key decisions:**
- DEFAULT_HEARTBEAT_INTERVAL (30) already matches settings default (30) — wiring is a no-op for default config but enables operator override
- After this feature, all 9 Settings fields will be consumed (0 orphaned)

**End-to-end acceptance criteria:**
- STOAT_DEBUG=true enables FastAPI debug mode
- STOAT_WS_HEARTBEAT_INTERVAL=15 changes actual WebSocket heartbeat interval
- No settings fields remain defined but unconsumed

### Theme 2, Feature 001: flaky-e2e-fix (BL-055)

**Goal:** Fix the intermittent toBeHidden() timeout in project-creation.spec.ts.

**What changes:**
- Add explicit { timeout: 10_000 } to toBeHidden() assertion at gui/e2e/project-creation.spec.ts:37
- Consistent with project's established timeout pattern (scan.spec.ts uses 10000, accessibility.spec.ts uses 15_000)

**Key decisions:**
- Root cause: default 5s Playwright assertion timeout too short for CI (GitHub Actions ubuntu-latest). No modal animation exists — the race is between API response, React re-render, and DOM update.
- Fix uses 10,000ms matching established project pattern rather than increasing global timeout

**End-to-end acceptance criteria:**
- toBeHidden() assertion passes reliably (AC requires 10 consecutive CI runs for validation)
- No E2E test requires retry loops in CI
- Fix doesn't alter tested functionality — timeout parameter only

---

## Research Sources Adopted

| Finding | Source | Applied To |
|---------|--------|------------|
| Playwright default assertion timeout is 5000ms | `004-research/evidence-log.md` (Evidence #1) | BL-055 fix rationale |
| Project uses 10-15s explicit timeouts elsewhere | `004-research/evidence-log.md` (Evidence #2) | BL-055 timeout value (10_000) |
| configure_logging(level: int) vs settings.log_level (Literal str) | `004-research/evidence-log.md` (Evidence #3, #4) | BL-056 type conversion |
| 9 structlog modules (not 10) | `004-research/evidence-log.md` (Evidence #5) | BL-056 AC verification |
| 3 duplicate create_tables_async() with inconsistent DDL | `004-research/evidence-log.md` (Evidence #7) | BL-058 test consolidation |
| DEFAULT_HEARTBEAT_INTERVAL = 30 matches settings default | `004-research/evidence-log.md` (Evidence #6) | BL-062 wiring confirmation |
| All 3 orphaned settings verified to exist | `004-research/evidence-log.md` (Evidence #8) | BL-062 completeness |
| create_tables() uses IF NOT EXISTS (idempotent) | `004-research/external-research.md` | BL-058 startup safety |
| Async extraction preferred over run_in_executor bridge | `004-research/external-research.md` | BL-058 implementation approach |
| Lifespan startup pattern at app.py:38-89 is canonical | `004-research/codebase-patterns.md` | All Theme 1 features |
| Test mode bypass via _deps_injected = True | `004-research/codebase-patterns.md` | BL-058, BL-056 guard placement |

## Handler Concurrency Decisions

Not applicable — no new MCP tool handlers are introduced in v008. All changes wire existing infrastructure into the startup sequence or fix an E2E test timeout.
