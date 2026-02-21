# Task 004: Research and Investigation — v008

Research investigated 14 questions across 4 backlog items (BL-055, BL-056, BL-058, BL-062). All AC-referenced functions, settings fields, and constants verified as existing with correct signatures. 7 learnings verified — all VERIFIED (conditions persist). Key findings: BL-055's Playwright `toBeHidden()` uses default 5s timeout while other E2E tests use 10-15s explicit timeouts; BL-056 has a type mismatch between `settings.log_level` (string literal) and `configure_logging(level: int)`; BL-058 has 3 inconsistent async copies of `create_tables_async()` in tests; BL-062 is straightforward 2-line wiring. No persistent state is introduced by any v008 item.

## Research Questions

### BL-055: Flaky E2E Test
1. What causes the `toBeHidden()` flake at `project-creation.spec.ts:37`?
2. What timeout values do other E2E tests use?
3. Is there a modal animation causing the race condition?
4. What does Playwright recommend for `toBeHidden()` reliability?

### BL-056: Wire Structured Logging
5. What is `configure_logging()` signature and its `level` parameter type?
6. What type is `settings.log_level` and how to convert to int?
7. How many modules use structlog and will be affected?
8. Where is `uvicorn.run()` and what `log_level` does it use?

### BL-058: Wire Database Startup
9. Is `create_tables()` sync or async? What's the async bridge approach?
10. How many `create_tables_async()` duplicates exist and are they consistent?
11. Should startup use `create_tables()` or Alembic migrations?

### BL-062: Wire Orphaned Settings
12. Do `settings.debug` and `settings.ws_heartbeat_interval` exist as described?
13. Where is `DEFAULT_HEARTBEAT_INTERVAL` and what value?
14. Are there any other unconsumed settings beyond the three targeted?

## Findings Summary

- **All AC references validated**: Every function, field, and constant referenced in ACs exists with correct names and locations
- **BL-055 root cause identified**: Default 5s Playwright assertion timeout is too short for CI; no modal animation exists; race condition is between API response, React re-render, and DOM update
- **BL-056 type mismatch confirmed**: `configure_logging(level: int)` vs `settings.log_level: Literal["DEBUG",...] (str)` — requires `getattr(logging, settings.log_level)` conversion
- **BL-058 duplication confirmed**: 3 async copies with inconsistent DDL coverage (8, 10, 12 statements); extraction into shared module justified per LRN-035
- **BL-062 fully straightforward**: 2 wiring changes + 1 audit verification; no complications found
- **9 structlog modules**: All will produce visible output after BL-056; test impact is low risk (structlog goes to stderr by default, tests don't capture it)

## Unresolved Questions

- **BL-055 AC #1 "10 consecutive CI runs"**: Cannot be verified pre-implementation. The fix must be validated empirically in CI. Mark as "TBD — requires runtime validation."
- **BL-056 test output interference**: Whether newly-active logging affects any test assertions cannot be fully determined without running tests. Existing tests don't appear to capture stdout/stderr, but verification needed at implementation time.

## Recommendations

1. **BL-055**: Add explicit timeout (10-15s) to `toBeHidden()` assertion, matching the pattern used by other E2E tests. The modal has no CSS animations, so the flake is purely a CI timing issue.
2. **BL-056**: Use `getattr(logging, settings.log_level)` for type conversion. Wire into lifespan before DB connection. Pass `settings.log_level.lower()` to uvicorn.
3. **BL-058**: Use `create_tables()` via `run_in_executor()` for the simplest approach (per LRN-029). Extract shared `create_tables_async()` into `src/stoat_ferret/db/schema.py`. Document Alembic as the upgrade path for multi-version schema changes.
4. **BL-062**: Wire `debug=settings.debug` into `FastAPI()` constructor and replace `DEFAULT_HEARTBEAT_INTERVAL` with `get_settings().ws_heartbeat_interval` in `ws.py`.
5. **Sequencing**: BL-058 → BL-056 → BL-062 within Theme 1 (per LRN-019). BL-055 in Theme 2 is independent.
