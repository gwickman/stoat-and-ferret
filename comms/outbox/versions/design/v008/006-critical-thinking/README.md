# Task 006: Critical Thinking and Risk Investigation — v008

Reviewed 7 risks from Task 005's logical design. Investigated 4 resolvable risks via codebase analysis, accepted 2 with mitigations, and confirmed 1 was already mitigated by design. The key design change is making `configure_logging()` idempotent before wiring it into the lifespan — without this, test runs accumulate duplicate logging handlers. All other risks were resolved without structural design changes.

## Risks Investigated

- **7 total risks** from Task 005
- **4 investigated now** (codebase queries): logging test breakage, logging placement, uvicorn format, WebSocket settings access
- **2 accepted with mitigation**: E2E 10-run validation (post-merge monitoring), schema evolution (document Alembic)
- **1 already mitigated by design**: merge conflicts on app.py (sequential execution)

## Resolutions

1. **configure_logging() is not idempotent** — `addHandler()` called without checking for existing handlers. Multiple calls accumulate duplicate handlers. Fix: add idempotency guard before adding handler. This is a new implementation requirement for Feature 002.
2. **Logging placement confirmed** — Place before `_deps_injected` guard for universal observability. Safe with idempotency fix.
3. **uvicorn format confirmed safe** — `.lower()` conversion handles all Literal values correctly. uvicorn uses "warning" (not "warn").
4. **WebSocket settings access confirmed safe** — `get_settings()` is @lru_cache, heartbeat interval read at connection time.

## Design Changes

From Task 005's proposal:
- **Feature 002 (logging-startup)**: Added requirement to make configure_logging() idempotent. Added test_logging.py handler cleanup to test modifications.
- **Feature 002 (logging-startup)**: Confirmed placement before _deps_injected guard (was UNVERIFIED in Task 005).
- **Test strategy**: Added 1 new unit test (idempotency) and 1 existing test modification (handler cleanup).

No changes to theme structure, feature ordering, or execution order.

## Remaining TBDs

- **E2E 10-run validation**: Post-merge monitoring required. Cannot be proven pre-merge.

## Confidence Assessment

**High confidence.** All UNVERIFIED assumptions from Task 005 have been resolved. The only design change (logging idempotency) is a small, well-understood fix. The scope remains tight: 4 backlog items, 2 themes, 4 features. No structural issues discovered.
