# Risks and Unknowns: v008

## Risk: Logging activation breaks existing tests

- **Severity:** medium
- **Description:** Calling configure_logging() at startup activates structlog output across 9 modules. Tests that capture stdout/stderr or assert on output content may see unexpected log lines, causing false failures.
- **Investigation needed:** Run full pytest suite with configure_logging() enabled to identify any tests that break from new log output. Check for tests that assert on stdout content or use capsys fixtures.
- **Current assumption:** UNVERIFIED — Most tests use the _deps_injected=True bypass and won't trigger lifespan logging. However, any test that directly calls configure_logging() or exercises code paths with logger.info() calls may be affected.

## Risk: E2E "10 consecutive CI runs" validation is not automatable in a single PR

- **Severity:** medium
- **Description:** BL-055 AC #1 requires the assertion to pass across 10 consecutive CI runs. A single PR merge cannot prove this — it requires monitoring post-merge CI runs over time.
- **Investigation needed:** Define how to validate this AC. Options: (a) manually re-trigger CI 10 times before merge, (b) accept the fix based on root cause analysis and monitor post-merge, (c) adjust the AC to "passes reliably in CI" without specifying a count.
- **Current assumption:** UNVERIFIED — The fix (adding explicit 10s timeout matching project patterns) addresses the identified root cause (default 5s too short for GitHub Actions). Post-merge monitoring is likely sufficient, but the AC as written requires pre-merge proof.

## Risk: create_tables_async() may need schema evolution strategy

- **Severity:** low
- **Description:** Using CREATE TABLE IF NOT EXISTS is idempotent for initial creation but does not handle schema changes (new columns, altered indexes). Alembic is configured but not wired. If v009+ adds schema changes, the startup strategy must evolve.
- **Investigation needed:** None for v008 — document Alembic as upgrade path per LRN-029.
- **Current assumption:** v008 scope does not include schema changes beyond initial creation. The IF NOT EXISTS pattern is safe and sufficient. Alembic upgrade trigger: when the first schema migration is needed post-v008.

## Risk: Shared modification point (app.py) creates merge conflict potential

- **Severity:** low
- **Description:** Three features in Theme 1 (BL-058, BL-056, BL-062) all modify src/stoat_ferret/api/app.py. If features execute in parallel or out of order, merge conflicts are likely.
- **Investigation needed:** None — mitigated by strict sequential execution order (001 → 002 → 003).
- **Current assumption:** Sequential execution within Theme 1 eliminates this risk. The execution order (database → logging → settings) is already mandated by functional dependencies.

## Risk: configure_logging() placement relative to _deps_injected guard

- **Severity:** medium
- **Description:** BL-056 must decide whether configure_logging() goes before or after the _deps_injected guard in the lifespan. Placing it inside the guard means test mode has no logging. Placing it outside means tests get logging output (which may break assertions per Risk #1).
- **Investigation needed:** Determine whether test-mode logging is desirable. Check if any tests rely on silent stdout. Research recommends placing logging before the guard for universal availability, but this interacts with Risk #1.
- **Current assumption:** UNVERIFIED — Logging should be configured unconditionally (before the guard) for maximum observability, but this needs validation against the test suite.

## Risk: uvicorn log_level format mismatch

- **Severity:** low
- **Description:** settings.log_level is a Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] (uppercase). uvicorn.run() expects lowercase log_level values. The conversion settings.log_level.lower() must handle all cases correctly.
- **Investigation needed:** Verify uvicorn accepts all lowercase variants of the Literal values. "warning" vs "warn" is a known inconsistency in some logging frameworks.
- **Current assumption:** uvicorn accepts "debug", "info", "warning", "error", "critical" — standard Python logging levels in lowercase. The .lower() conversion is straightforward and complete.

## Risk: WebSocket heartbeat settings access pattern

- **Severity:** low
- **Description:** ws.py currently uses a module-level constant. Replacing it with get_settings().ws_heartbeat_interval requires calling get_settings() at runtime rather than import time. The settings object is cached, so performance is not a concern, but the import and call pattern must be correct.
- **Investigation needed:** Verify get_settings() is importable in ws.py context and returns a valid Settings instance during WebSocket connection handling.
- **Current assumption:** get_settings() is already used elsewhere in the codebase (verified in 004-research). The pattern is established and safe.
