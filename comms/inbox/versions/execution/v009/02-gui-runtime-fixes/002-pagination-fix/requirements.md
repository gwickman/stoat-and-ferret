# Requirements: pagination-fix

## Goal

Add count() to AsyncProjectRepository, fix total in API response, and add frontend pagination UI for the Projects page.

## Background

Backlog Item: BL-064

`GET /api/v1/projects` returns `total=len(projects)` which equals the current page size, not the true database total. A `count()` method was added to `AsyncVideoRepository` in v005 but not to `AsyncProjectRepository`. The Projects page also lacks pagination UI — it fetches with hardcoded `limit=100` and no offset. BL-064 AC3 requires frontend pagination, so the Library page pattern must be replicated.

## Functional Requirements

**FR-001: AsyncProjectRepository count() method**
- Add `count()` to the `AsyncProjectRepository` protocol
- Implement in `SQLiteProjectRepository` using `SELECT COUNT(*) FROM projects`
- Implement in `InMemoryProjectRepository` using `len(self._projects)`
- Acceptance: `await repo.count()` returns correct total for both implementations

**FR-002: Correct API total count**
- Wire `count()` into the projects router so `GET /api/v1/projects` returns the true database total
- Acceptance: With 25 projects and `limit=10`, response `total` is 25

**FR-003: Frontend pagination state**
- Add `page` and `pageSize` state to `projectStore.ts` (matching `libraryStore.ts` pattern)
- Acceptance: Project store tracks current page and page size

**FR-004: Frontend pagination parameters**
- Update `useProjects` hook to accept `page`/`pageSize` and send `limit`/`offset` query parameters
- Acceptance: API requests include correct `limit` and `offset` based on current page

**FR-005: Frontend pagination UI**
- Add Previous/Next pagination UI to `ProjectsPage.tsx` (matching `LibraryPage.tsx` pattern)
- Display correct page count based on `total` and `pageSize`
- Acceptance: Projects page shows pagination controls when projects exceed page limit

## Non-Functional Requirements

**NFR-001: Pattern consistency**
- count() implementation follows the exact pattern from AsyncVideoRepository
- Metric: Code structure mirrors `AsyncVideoRepository.count()` at protocol, SQLite, and InMemory levels

## Out of Scope

- Adding count() to other repositories (clips, etc.)
- Server-side sorting or filtering for projects
- Infinite scroll or virtualized list rendering
- Project search functionality

## Test Requirements

- Unit: Verify `AsyncProjectRepository.count()` returns correct total (SQLite implementation)
- Unit: Verify `AsyncProjectRepository.count()` returns correct total (InMemory implementation)
- Unit: Verify protocol defines `count()` method
- Integration: Verify `GET /api/v1/projects` returns correct total count (AC2)
- Frontend: Verify Projects page shows pagination when projects exceed page limit (AC3)
- Frontend: Verify Previous/Next navigation works for projects
- Frontend: Verify page resets when project is created/deleted
- Existing: Add `count()` tests to project repository tests mirroring video repository test patterns

See `comms/outbox/versions/design/v009/005-logical-design/test-strategy.md` for full test strategy.

## Reference

See `comms/outbox/versions/design/v009/004-research/` for supporting evidence.