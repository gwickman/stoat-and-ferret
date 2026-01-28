# Theme 03: library-api Retrospective

## Theme Summary

Theme 03 delivered a complete REST API for video library management, implementing all four planned features:
- Video listing and detail retrieval
- Full-text search with FTS5
- Directory scanning with metadata extraction
- Video deletion with optional file removal

All endpoints follow the API specification and integrate with the async repository from Theme 01. The theme successfully achieved roadmap milestone M1.6.

## Feature Results

| Feature | Status | Acceptance | Quality Gates | Notes |
|---------|--------|------------|---------------|-------|
| 001-videos-list-detail | Complete | 4/4 | All pass | Core CRUD read operations |
| 002-videos-search | Complete | 4/4 | All pass | FTS5 query integration |
| 003-videos-scan | Complete | 4/4 | All pass | FFprobe metadata extraction |
| 004-videos-delete | Complete | 4/4 | All pass | Optional file deletion |

### Metrics Summary

| Metric | Start | End |
|--------|-------|-----|
| Test count | - | 318 |
| Test coverage | - | 92.59% |
| Skipped tests | - | 8 (FFmpeg-dependent) |

## Key Learnings

### What Worked Well

1. **Dependency Injection Pattern**: Using FastAPI's `Depends` with `Annotated` type alias (`RepoDep`) created clean, testable code that satisfies ruff B008 rule. This pattern should be reused for future API development.

2. **Repository Protocol Abstraction**: Leveraging the existing `AsyncVideoRepository` protocol allowed seamless testing with in-memory implementations while maintaining production database support.

3. **Sequential Feature Execution**: Building features in order (list → search → scan → delete) allowed each feature to build on established patterns, reducing ramp-up time.

4. **Error Response Standardization**: Consistent error format with `code` and `message` fields in detail objects provides predictable client experience.

5. **Test Coverage Maintenance**: Coverage remained above 91% throughout all features, ensuring regression protection.

### Patterns Discovered

1. **Route Ordering in FastAPI**: Static paths (like `/search`) must be defined before dynamic paths (like `/{video_id}`) to avoid route conflicts.

2. **Graceful Error Handling in Scan**: Capturing individual file failures in an errors list while continuing to process remaining files provides better UX than failing the entire operation.

3. **Best-Effort File Deletion**: Using `contextlib.suppress(OSError)` for file deletion handles edge cases (file already deleted, permissions changed) gracefully.

### Architectural Decisions Validated

| Decision | Outcome |
|----------|---------|
| AD-001: DI for Repository | Validated - clean testability |
| AD-002: Pydantic Schemas | Validated - type safety and validation |
| AD-003: Synchronous Scan | Acceptable for now, job queue noted for v004 |

## Technical Debt

No quality-gaps.md files were created for this theme, indicating clean implementations. However, the following items were noted in completion reports for future consideration:

| Item | Source | Priority | Notes |
|------|--------|----------|-------|
| True total count for pagination | 001-videos-list-detail | Low | Currently returns count of current page only |
| Async job queue for scan | THEME_DESIGN AD-003 | Medium | Deferred to v004, scan currently blocks |
| FFmpeg-dependent test handling | All features | Low | 8 tests skipped when FFmpeg unavailable |

## Recommendations

### For Future API Themes

1. **Continue Repository Protocol Pattern**: The async repository abstraction proved valuable for testing. Future data access should follow this pattern.

2. **Maintain Route Definition Order**: Document the FastAPI route ordering requirement in coding standards to prevent future issues.

3. **Consider Pagination Enhancement**: If pagination becomes a user concern, implement true total count with a configurable flag (to avoid expensive COUNT queries when not needed).

4. **Plan for Async Operations**: For long-running operations like scan, design with job queue architecture from the start rather than retrofitting.

### Process Improvements

1. The sequential feature execution worked well for this theme's interdependent features. Maintain this approach when features build on each other.

2. Quality gates (ruff, mypy, pytest) caught issues early. No regressions occurred across the four features.
