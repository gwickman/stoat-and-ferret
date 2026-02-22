---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 003-websocket-broadcasts

## Summary

Wired `ConnectionManager.broadcast()` into project creation and scan job handler for real-time WebSocket events. All four functional requirements (FR-001 through FR-004) are met.

## Changes

### `src/stoat_ferret/api/routers/projects.py`
- Added `EventType`, `build_event`, and `ConnectionManager` imports
- Modified `create_project()` to accept `Request` object (renamed body param to `project_data`)
- After successful project creation, broadcasts `PROJECT_CREATED` event with `project_id` and `name` payload
- Guarded with `if ws_manager:` to avoid crashes when ws_manager is not set

### `src/stoat_ferret/api/services/scan.py`
- Added `EventType`, `build_event` imports and `ConnectionManager` TYPE_CHECKING import
- Extended `make_scan_handler()` with optional `ws_manager` parameter
- Broadcasts `SCAN_STARTED` with `path` payload at start of scan handler
- Broadcasts `SCAN_COMPLETED` with `path` and `video_count` payload after scan finishes
- `video_count` = `new + updated` (counts videos actually processed)

### `src/stoat_ferret/api/app.py`
- Updated `make_scan_handler()` call in lifespan to pass `app.state.ws_manager`

### `tests/test_api/test_websocket_broadcasts.py` (new)
- 10 tests covering all broadcast scenarios
- `TestProjectCreatedBroadcast`: 5 tests for PROJECT_CREATED (broadcast called, event type, payload, timestamp, no-crash without ws_manager)
- `TestScanBroadcasts`: 5 tests for SCAN_STARTED/SCAN_COMPLETED (event types, payloads, video_count, no-crash without ws_manager, event structure)

## Acceptance Criteria

| # | Criteria | Status |
|---|---------|--------|
| FR-001 | SCAN_STARTED broadcast at start of scan | Pass |
| FR-002 | SCAN_COMPLETED broadcast at end of scan with video count | Pass |
| FR-003 | PROJECT_CREATED broadcast after project creation | Pass |
| FR-004 | Events use build_event() for consistent structure | Pass |

## Test Results

- 936 passed, 20 skipped, 92.92% coverage (threshold: 80%)
- All 10 new broadcast tests pass
