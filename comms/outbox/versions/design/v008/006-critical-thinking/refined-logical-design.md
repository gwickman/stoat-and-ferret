# Refined Logical Design: v008 — Startup Integrity & CI Stability

## Version Overview

**Version:** v008
**Description:** Fix P0 blockers and critical startup wiring gaps so a fresh install starts cleanly with working logging, database, and settings.

**Goals:**
1. Wire database schema creation into application startup (P0)
2. Wire structured logging into application startup (P1)
3. Connect orphaned settings to their consumers (P2)
4. Fix the flaky E2E test blocking CI reliability (P0)

**Scope:** 4 backlog items (BL-055, BL-056, BL-058, BL-062), 2 themes, 4 features. All items mandatory. No deferrals.

---

## Theme 1: 01-application-startup-wiring

**Goal:** Wire existing but disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence.

**Backlog Items:** BL-058, BL-056, BL-062

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-database-startup | Wire create_tables() into lifespan so schema is created on startup | BL-058 | None |
| 2 | 002-logging-startup | Call configure_logging() at startup; wire settings.log_level | BL-056 | 001-database-startup |
| 3 | 003-orphaned-settings | Wire settings.debug to FastAPI and settings.ws_heartbeat_interval to ws.py | BL-062 | 002-logging-startup |

**Rationale for grouping:** Unchanged from Task 005 — all three share the app.py lifespan modification point.

**Rationale for feature order:** Unchanged from Task 005 — database first, logging second, settings last. Sequential execution eliminates merge conflict risk on shared files.

---

## Theme 2: 02-ci-stability

**Goal:** Eliminate the flaky E2E test that intermittently blocks CI merges.

**Backlog Items:** BL-055

**Features:**

| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | 001-flaky-e2e-fix | Fix toBeHidden() timeout in project-creation.spec.ts | BL-055 | None |

**Rationale for separate theme:** Unchanged — isolated frontend test with no code overlap with Theme 1.

---

## Execution Order

Unchanged from Task 005:

1. **01-application-startup-wiring** (first) — P0/P1 items
2. **02-ci-stability** (second) — isolated test fix

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

## Feature Details (Refined)

### Theme 1, Feature 001: database-startup (BL-058)

Unchanged from Task 005. No risks materialized that affect this feature.

**What changes:**
- Add async schema creation call to lifespan in app.py (inside _deps_injected guard)
- Add create_tables_async() to schema.py using existing aiosqlite connection
- Replace 3 duplicate create_tables_async() helpers in tests with import from schema.py

### Theme 1, Feature 002: logging-startup (BL-056) — REFINED

**Changes from Task 005** (per risk-assessment.md, Risks #1 and #5):

1. **New requirement: make configure_logging() idempotent.** Before adding a StreamHandler, check if one is already attached to the root logger. This prevents handler accumulation across test runs and multiple lifespan invocations.

2. **Placement confirmed: before _deps_injected guard.** Logging should be available in all modes including test mode. The idempotency fix makes this safe.

3. **New test modification: test_logging.py handler cleanup.** Add root logger handler removal in test teardown (or between tests) to prevent handler accumulation from the 4 calls to configure_logging() in that test file.

**What changes:**
- Make configure_logging() idempotent: guard `root.addHandler(handler)` with a check for existing handlers
- Add configure_logging() call in lifespan BEFORE the _deps_injected guard
- Convert settings.log_level string to int via getattr(logging, settings.log_level)
- Change uvicorn log_level from hardcoded "info" to settings.log_level.lower()

**Key decisions (refined):**
- configure_logging() goes before _deps_injected guard for universal observability
- Idempotency is required to prevent handler accumulation (verified by investigation)
- settings.log_level.lower() for uvicorn is correct — uvicorn uses "warning" (not "warn")

### Theme 1, Feature 003: orphaned-settings (BL-062)

Unchanged from Task 005. Risk investigation confirmed:
- get_settings() is @lru_cache-decorated and safe for runtime access
- Heartbeat interval is read at connection time, not import time
- DEFAULT_HEARTBEAT_INTERVAL (30) matches settings default (30)

### Theme 2, Feature 001: flaky-e2e-fix (BL-055)

Unchanged from Task 005. The "10 consecutive CI runs" AC is interpreted as post-merge validation (see risk-assessment.md, Risk #2). The fix itself (explicit 10s timeout) is sound and follows established project patterns.

---

## Updated Test Strategy

Additions to the test strategy from Task 005:

### Feature 002 additions:
- **New unit test:** Test configure_logging() idempotency — calling twice does not add duplicate handlers
- **Existing test modification:** test_logging.py needs root logger handler cleanup between tests (reset_defaults() only resets structlog, not stdlib logging handlers)

All other test requirements from Task 005 remain unchanged.

---

## Backlog Coverage Verification

| Backlog | Theme | Feature | Status |
|---------|-------|---------|--------|
| BL-055 (P0) | 02-ci-stability | 001-flaky-e2e-fix | Covered |
| BL-056 (P1) | 01-application-startup-wiring | 002-logging-startup | Covered (refined) |
| BL-058 (P0) | 01-application-startup-wiring | 001-database-startup | Covered |
| BL-062 (P2) | 01-application-startup-wiring | 003-orphaned-settings | Covered |

All 4 backlog items from PLAN.md are covered. No deferrals. No descoping.

## Persistence Coherence

No persistence-analysis.md was produced by Task 004. v008 does not introduce new persistent state — it wires existing database schema creation (database_path is already validated in the codebase via settings). No blocking storage path concerns.

## Research Sources Adopted

Unchanged from Task 005 plus:

| Finding | Source | Applied To |
|---------|--------|------------|
| configure_logging() is not idempotent (addHandler without guard) | 006 investigation of logging.py | BL-056 idempotency requirement |
| _deps_injected guard only skips DB/queue, not full lifespan | 006 investigation of app.py | BL-056 placement decision |
| get_settings() is @lru_cache decorated | 006 investigation of settings.py | BL-062 safety confirmation |
| Heartbeat interval read at connection time, not import time | 006 investigation of ws.py | BL-062 safety confirmation |
| uvicorn uses "warning" (not "warn") | 006 investigation | BL-056 format conversion |
