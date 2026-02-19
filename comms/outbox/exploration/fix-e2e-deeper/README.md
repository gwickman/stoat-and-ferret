# Fix: Persistent E2E Project-Creation Failure (BL-055)

The root cause was a schema mismatch: the `projects` and `clips` alembic
migrations omitted the `transitions_json` and `effects_json` columns that
the repository INSERT statements reference. In CI, where the database is
always created fresh from migrations, every `POST /api/v1/projects` call
hit a SQLite "table projects has no column named transitions_json" error,
returning a 500 to the frontend. The modal caught the error and stayed open,
causing the `toBeHidden` assertion to time out.

## What Was Changed

1. **New alembic migration** (`1e895699ad50`): adds `transitions_json TEXT`
   to `projects` and `effects_json TEXT` to `clips` via `ALTER TABLE`.
2. **E2E test cleanup**: removed the misleading "slow backend" workaround
   comments and inflated timeouts that were added during earlier fix attempts.

## Why Previous Fixes Failed

- The `waitForResponse` synchronization and 10s timeout in the E2E test
  addressed a timing hypothesis, but the API was returning a 500 error
  every time, not running slowly.
- The modal's catch block kept it open and displayed the error, so no
  amount of waiting would make it close.

## Verification

- Alembic migration roundtrips cleanly (upgrade -> downgrade -> upgrade).
- All 854 Python tests pass (pytest, 92% coverage).
- Local database upgraded successfully with `alembic upgrade head`.
