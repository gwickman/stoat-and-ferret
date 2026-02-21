# External Research — v008

## Playwright toBeHidden() Best Practices

**Source:** DeepWiki query on `microsoft/playwright` repository

### Key Findings

1. **Default assertion timeout is 5000ms (5 seconds)**, not 30 seconds as sometimes assumed. Timeout precedence: per-assertion > `expect.configure()` > `expect.timeout` in config > default 5000ms.

2. **`toBeHidden()` and `not.toBeVisible()` are functionally equivalent** — both use the same underlying mechanism. No reliability difference between them.

3. **CI environments are slower** — the primary cause of intermittent `toBeHidden()` failures. Slower infrastructure means UI transitions take longer, and the default 5s timeout may expire before the DOM updates.

4. **Recommended practices for modal close assertions:**
   - Add explicit timeout matching expected async operation duration
   - Wait for the network request that triggers the state change to complete before asserting visibility
   - Ensure the element is truly removed from DOM (not just CSS-hidden)

5. **Never use `locator.isHidden()`** (returns boolean immediately without waiting) — always use `expect(locator).toBeHidden()` for reliable assertions.

### Application to BL-055

The `project-creation.spec.ts:37` assertion `await expect(page.getByTestId("create-project-modal")).toBeHidden()` fails intermittently because:
- It uses the default 5s timeout
- The test must wait for: API POST response → React state update → DOM unmount
- CI infrastructure (GitHub Actions ubuntu-latest) adds latency to all three steps
- Other E2E tests in this project use 10-15s explicit timeouts for similar async operations

**Recommended fix:** Add explicit `{ timeout: 10_000 }` to the `toBeHidden()` assertion, consistent with the project's existing pattern in `scan.spec.ts` and `effect-workshop.spec.ts`.

### Additional Consideration

The modal component (`gui/src/components/CreateProjectModal.tsx`) uses conditional rendering (`if (!open) return null`) — no CSS animations or transitions. The element is fully removed from the DOM when closed. This means `toBeHidden()` is appropriate (vs `not.toBeVisible()`), but the timing depends entirely on React's re-render cycle after the API response completes.

## structlog Configuration Patterns

**Source:** Project codebase analysis (no external research needed — `configure_logging()` already exists)

The existing `configure_logging()` function at `src/stoat_ferret/logging.py` follows standard structlog patterns:
- JSON renderer for production, console renderer for development
- stdlib logging integration via `logging.basicConfig()`
- structlog processor chain with timestamps, log level, caller info

No external research required — the function is complete and well-structured. The only gap is that it's never called.

## SQLite Schema-at-Startup Patterns

**Source:** Project codebase analysis

Two viable approaches exist in the codebase:

1. **`create_tables()` (sync):** Uses `CREATE TABLE IF NOT EXISTS` — idempotent, safe to run on every startup. Requires `run_in_executor()` bridge for async lifespan context.

2. **Alembic migrations:** Already configured with 5 migrations. E2E tests use `alembic upgrade head`. More complex but supports schema versioning.

**Per LRN-029 (Conscious Simplicity):** `create_tables()` is the simpler approach for current scope. All DDL uses `IF NOT EXISTS`, making it safe for repeated execution. Document Alembic as upgrade path when schema versioning becomes necessary (e.g., when adding columns to existing tables with data migration needs).

**Async bridge options:**
- `await asyncio.get_event_loop().run_in_executor(None, create_tables, sync_conn)` — requires a sync `sqlite3.Connection`
- Extract async version using `await conn.execute()` pattern from test helpers — uses existing `aiosqlite.Connection`

The async extraction approach is cleaner because the lifespan already has an `aiosqlite.Connection` open. Creating a separate sync connection just for `create_tables()` adds unnecessary complexity.
