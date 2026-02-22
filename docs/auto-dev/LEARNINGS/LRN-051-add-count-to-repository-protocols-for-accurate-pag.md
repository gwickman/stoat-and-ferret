## Context

List endpoints that paginate results need an accurate total count to calculate page numbers. Using `len(page_results)` as the total returns the page size rather than the true database count, breaking pagination UI.

## Learning

Add a `count()` method to repository protocols alongside `list()` for any entity type that supports pagination. Implement as `SELECT COUNT(*)` for SQLite and `len(self._store)` for InMemory. Call `count()` separately from `list()` in the endpoint to populate the total field accurately.

## Evidence

In v009, the projects endpoint returned `total=len(projects)` which equaled the page size rather than the true count. Adding `count()` to `AsyncProjectRepository` protocol (mirroring the existing `AsyncVideoRepository.count()` pattern), implementing in both SQLite and InMemory backends, and wiring into the router fixed the pagination total. The pattern was straightforward: 3 test classes confirmed correctness across both implementations.

## Application

When adding a new repository protocol or noticing a list endpoint with pagination:
1. Add `count()` to the protocol definition
2. Implement `SELECT COUNT(*) FROM table` for SQLite
3. Implement `len(self._store)` for InMemory
4. Call `await repo.count()` in the endpoint, not `len(results)`
5. Add contract tests verifying count accuracy across implementations