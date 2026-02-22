## Context

When wiring initialization logic into application startup (e.g., FastAPI lifespan), the same startup function may be invoked multiple times — once in production and repeatedly across test fixtures.

## Learning

All startup/lifespan functions should be idempotent. Use guards appropriate to the operation: `IF NOT EXISTS` for DDL statements, exact-type checks for handler registration, and initialization flags for one-time setup. This prevents accumulating duplicate side effects (duplicate log handlers, redundant schema creation) without requiring callers to track invocation state.

## Evidence

In v008 Theme 01, both `create_tables_async()` (using `IF NOT EXISTS` DDL) and `configure_logging()` (guarding `root.addHandler()` with an exact-type check for existing `StreamHandler`) were made idempotent. This allowed tests to invoke lifespan functions freely without accumulating duplicate handlers or triggering schema errors.

## Application

When adding any initialization logic to an application lifespan or startup sequence:
1. Assume the function will be called multiple times
2. Choose an idempotency guard appropriate to the operation type
3. Test explicitly that multiple invocations produce the same result as a single invocation