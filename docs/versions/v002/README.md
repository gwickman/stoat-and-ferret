# v002 - Database & FFmpeg Integration

**Completed:** 2026-01-27

## Summary

v002 addressed roadmap milestones M1.4-1.5 by completing the Python bindings for all v001 Rust types, establishing CI-enforced stub verification, building the database foundation with SQLite and repository pattern, and integrating FFmpeg execution with observability.

## Themes

| Theme | Features | Description |
|-------|----------|-------------|
| 01-rust-python-bindings | 4 | Stub regeneration, Clip bindings, Range list ops, API naming cleanup |
| 02-tooling-process | 1 | PyO3 guidance in AGENTS.md |
| 03-database-foundation | 4 | SQLite schema, Repository pattern, Alembic migrations, Audit logging |
| 04-ffmpeg-integration | 4 | FFprobe wrapper, Executor protocol, Command integration, Observability |

**Total:** 13 features, 55 acceptance criteria (100% pass rate)

## Key Deliverables

### Python Bindings Completion
- `Clip` and `ClipValidationError` types exposed to Python
- `find_gaps`, `merge_ranges`, `total_coverage` functions for TimeRange operations
- Automatic stub verification script (`scripts/verify_stubs.py`)
- CI drift detection for stub files

### Database Foundation
- SQLite schema with 14-column `videos` table
- FTS5 full-text search with automatic index synchronization
- `VideoRepository` protocol with SQLite and InMemory implementations
- Alembic migration support with rollback capability
- Audit logging for tracking all data modifications

### FFmpeg Integration
- FFprobe wrapper for extracting structured video metadata
- `FFmpegExecutor` protocol with Real, Recording, and Fake implementations
- Integration layer bridging Rust `FFmpegCommand` to Python executor
- Recording/replay pattern for deterministic subprocess testing
- `ObservableFFmpegExecutor` with structured logging and Prometheus metrics

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Verification-based stub checking | pyo3-stub-gen generates incomplete stubs; manual stubs remain source of truth |
| Synchronous SQLite | No async needed until FastAPI in v003; simpler implementation |
| FTS5 external content mode | Automatic index synchronization via triggers |
| Executor boundary at Python | Subprocess execution cleaner in Python; Rust handles command building |
| Observable executor wrapper | Adds logging/metrics without modifying executors |

## Technical Debt Introduced

| Item | Priority | Notes |
|------|----------|-------|
| No async repository | P2 | Synchronous sqlite3; aiosqlite migration needed for v003 |
| InMemory vs FTS5 search behavior | P3 | Consider unifying for consistent testing |
| Timeout configuration | P3 | Per-call timeout; could add default configuration |

## Dependencies Added

- `alembic>=1.13` - Database migrations
- `structlog>=24.0` - Structured logging
- `prometheus-client>=0.20` - Metrics collection

## Test Coverage

- 222 total tests (201 Rust + 73 Python + 83 doc tests)
- 90-97% coverage (varies by module)
- 77 FFmpeg-related tests

## Links

- [Full Retrospective](../../comms/outbox/versions/execution/v002/retrospective.md)
- [CHANGELOG](../../CHANGELOG.md#v002---2026-01-27)
