# Requirements - 002: Pagination Total Count

## Goal

Add a `count()` method to the async repository protocol and implementations, and fix the `list_videos` and `search` endpoints to return the true total count of matching items.

## Background

Paginated list endpoints return page-based results but lack a true total count. This was identified as tech debt in the v003 retrospective. Currently `list_videos` returns `total=len(videos)` which is the page count, not the full dataset count. The library browser needs the total count for virtual scrolling (to size the scroll container) and for displaying "X of Y results" feedback.

**Backlog Item:** BL-034

## Functional Requirements

**FR-001: Repository protocol count method**
Add `async def count(self) -> int` to the `AsyncVideoRepository` protocol.
- AC: `AsyncVideoRepository` protocol includes `count()` method signature

**FR-002: SQLite count implementation**
Implement `count()` in `AsyncSQLiteVideoRepository` using `SELECT COUNT(*)`.
- AC: `AsyncSQLiteVideoRepository.count()` returns accurate total from database

**FR-003: InMemory count implementation**
Implement `count()` in `AsyncInMemoryVideoRepository` using `len()`.
- AC: `AsyncInMemoryVideoRepository.count()` returns accurate total from in-memory store

**FR-004: List endpoint fix**
Update `GET /api/v1/videos` to call `count()` and return true total instead of `len(videos)`.
- AC: `GET /api/v1/videos` response `total` field reflects full count of all videos, not just current page

**FR-005: Search endpoint fix**
Update `GET /api/v1/videos/search` to return total matching results separate from page size.
- AC: `GET /api/v1/videos/search` response `total` field reflects full count of matching results

## Non-Functional Requirements

**NFR-001: Query performance**
`SELECT COUNT(*)` executes within 10ms for libraries with up to 10,000 videos.
- Metric: count query < 10ms on SQLite with 10K rows

## Out of Scope

- Filtered count (count with search/filter parameters) -- basic unfiltered count for v005
- Project repository count method (only video repository in scope for BL-034)
- Pagination cursor-based approach

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests | `count()` returns correct total for SQLite and InMemory repositories; count reflects actual number of stored items |
| Integration tests | `GET /api/v1/videos` response includes `total` field with true count; `GET /api/v1/videos/search` response includes `total` matching full result set, not page size |
| Contract tests | Response schema includes `total: int` field |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.