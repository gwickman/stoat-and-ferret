# Handoff: 001-inmemory-test-doubles

## What Was Done

- All three InMemory repositories now use `copy.deepcopy()` for full isolation:
  - On write (add, update): stores a deepcopy of the input
  - On read (get, list, search): returns a deepcopy of stored data
- Each InMemory repository has a `seed(items)` method for populating test data
- New `src/stoat_ferret/jobs/` package with `AsyncJobQueue` protocol and `InMemoryJobQueue`

## Key Design Decisions

- **Deepcopy on both read and write**: This ensures complete isolation. Callers can't mutate store state regardless of whether they hold the input object or the returned object.
- **seed() is synchronous**: Unlike `add()`, `seed()` is a sync method since it's a test setup utility, not a production code path. It does not perform duplicate-ID checks — it overwrites.
- **InMemoryJobQueue executes synchronously at submit time**: Jobs complete immediately for deterministic testing. No actual async execution happens.
- **JobOutcome configuration per job type**: Tests can configure different outcomes (success/failure/timeout) for different job types using `configure_outcome()`.

## For Next Feature

- The `AsyncJobQueue` protocol is ready to be implemented with real async backends (e.g., asyncio.Queue in Theme 03)
- Existing tests that create InMemory repos can now use `seed()` instead of calling `add()` multiple times
- Contract tests in `tests/test_contract/test_repository_parity.py` can be extended when adding new repository methods
