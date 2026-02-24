# C4 Code-Level Analysis: Batch 2 of 2 (v011)

## Summary

Updated 12 C4 Code-level documentation files for the Python backend and test directories. This batch covers all `src/stoat_ferret/` sub-packages and the `tests/` directory tree. All updates are delta-mode changes reflecting current codebase state.

## Directories Processed (12)

| # | Directory | Description |
|---|-----------|-------------|
| 1 | `src/stoat_ferret/api/routers` | REST/WebSocket endpoint routers (8 files) |
| 2 | `src/stoat_ferret/api/schemas` | Pydantic v2 request/response schemas (7 files) |
| 3 | `src/stoat_ferret/api/services` | Business logic services - scan, thumbnail (3 files) |
| 4 | `src/stoat_ferret/api` | Application factory, settings, lifespan, middleware (4 files) |
| 5 | `src/stoat_ferret/db` | Database layer - repositories, models, schema, audit (8 files) |
| 6 | `src/stoat_ferret/ffmpeg` | FFmpeg integration - executor, probe, observable (6 files) |
| 7 | `src/stoat_ferret/jobs` | Async job queue with cancellation and progress (2 files) |
| 8 | `src/stoat_ferret` | Package root - version metadata, structured logging (2 files) |
| 9 | `tests/test_api` | API endpoint tests (17 test files + conftest) |
| 10 | `tests/test_doubles` | Test double isolation and seed tests (3 test files) |
| 11 | `tests/test_jobs` | Job queue and worker lifecycle tests (2 test files) |
| 12 | `tests/` | Root-level tests covering infrastructure (26 test files + 2 helpers) |

## Files Updated (12)

| File | Lines | Key Changes |
|------|-------|-------------|
| `c4-code-stoat-ferret-api-routers.md` | 247 | Added filesystem.py router, cancel_job endpoint, ws heartbeat with settings |
| `c4-code-stoat-ferret-api-schemas.md` | 195 | Added filesystem.py schemas (DirectoryEntry, DirectoryListResponse) |
| `c4-code-stoat-ferret-api-services.md` | 101 | Added ws_manager/queue params to make_scan_handler, cancel_event/progress_callback |
| `c4-code-stoat-ferret-api.md` | 130 | Added filesystem router, AuditLogger/ObservableFFmpegExecutor in lifespan, log settings |
| `c4-code-stoat-ferret-db.md` | 222 | Added count() to AsyncProjectRepository, schema constants, detailed DDL |
| `c4-code-stoat-ferret-ffmpeg.md` | 158 | Async ffprobe_video signature, correlation_id in ObservableFFmpegExecutor |
| `c4-code-stoat-ferret-jobs.md` | 125 | CANCELLED status, cancel/set_progress in protocols, _AsyncJobEntry with cancel_event |
| `c4-code-stoat-ferret.md` | 69 | RotatingFileHandler, max_bytes/backup_count params, ffmpeg/jobs sub-packages |
| `c4-code-tests-test-api.md` | 133 | 215 tests across 17 files (added filesystem, spa_routing, websocket_broadcasts) |
| `c4-code-tests-test-doubles.md` | 143 | 33 tests across 3 files, added TestHandlerRegistration |
| `c4-code-tests-test-jobs.md` | 129 | 25 tests across 2 files, added cancellation and progress test sections |
| `c4-code-tests.md` | 190 | ~606 tests across 26 files, added new test files and updated counts |

## Languages Detected

| Language | Files | Location |
|----------|-------|----------|
| Python | 40 source files | `src/stoat_ferret/` |
| Python (pytest) | 48 test files | `tests/` |

## Test Coverage Summary

| Test Directory | Test Count | Files |
|----------------|------------|-------|
| `tests/` (root) | ~606 | 26 test files + 2 helpers |
| `tests/test_api/` | 215 | 17 test files + conftest |
| `tests/test_doubles/` | 33 | 3 test files |
| `tests/test_jobs/` | 25 | 2 test files |

## Issues Encountered

None. All source files were readable and all existing C4 documents were successfully updated in delta mode.

## Notable Changes Since Last C4 Update

- **Filesystem browsing**: New `filesystem.py` router and schemas for directory listing with scan-root security
- **Job cancellation**: CANCELLED status added to JobStatus enum, cancel/set_progress methods on queue protocol
- **WebSocket broadcasts**: ConnectionManager integration with scan service for real-time event delivery
- **Observable FFmpeg**: correlation_id parameter added for distributed tracing support
- **Expanded test suite**: Root tests grew to ~606 across 26 files with new database startup, logging startup, observability, and event loop responsiveness tests
