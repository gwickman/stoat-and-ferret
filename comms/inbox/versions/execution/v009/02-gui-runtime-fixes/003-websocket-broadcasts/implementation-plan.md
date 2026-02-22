# Implementation Plan: websocket-broadcasts

## Overview

Wire `ConnectionManager.broadcast()` calls into the project creation endpoint and scan job handler. PROJECT_CREATED broadcasts fire from the projects router; SCAN_STARTED and SCAN_COMPLETED broadcasts fire from the scan job handler. Access `ws_manager` via `request.app.state.ws_manager` in routers and dependency injection in the scan service.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/routers/projects.py` | Modify | Add PROJECT_CREATED broadcast after successful project creation |
| `src/stoat_ferret/api/routers/videos.py` | Modify | Pass ws_manager to scan service if needed for broadcast access |
| `src/stoat_ferret/api/services/scan.py` | Modify | Add SCAN_STARTED and SCAN_COMPLETED broadcasts in scan job handler |
| `tests/test_api/test_websocket_broadcasts.py` | Create | Tests for broadcast calls with correct event types and payloads |

## Test Files

`tests/test_api/test_websocket_broadcasts.py`

## Implementation Stages

### Stage 1: Wire PROJECT_CREATED broadcast

1. In `routers/projects.py` `create_project()` endpoint:
   - After successful project creation, get `ws_manager = request.app.state.ws_manager`
   - Call `await ws_manager.broadcast(build_event(EventType.PROJECT_CREATED, {"project_id": project.id, "name": project.name}))`
2. Import `build_event` and `EventType` from `websocket.events`

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_api/test_websocket_broadcasts.py -x -k project
```

### Stage 2: Wire SCAN_STARTED and SCAN_COMPLETED broadcasts

1. Identify the scan job handler (in scan service or job queue processor)
2. At the start of the scan handler:
   - Call `await ws_manager.broadcast(build_event(EventType.SCAN_STARTED, {"path": scan_path}))`
3. At the end of the scan handler (after completion):
   - Call `await ws_manager.broadcast(build_event(EventType.SCAN_COMPLETED, {"path": scan_path, "video_count": len(videos)}))`
4. Pass `ws_manager` to the scan service via constructor or method parameter

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_api/test_websocket_broadcasts.py -x -k scan
```

### Stage 3: Add comprehensive tests

1. Test PROJECT_CREATED: mock `ws_manager`, create project, verify `broadcast()` called with correct event type and payload
2. Test SCAN_STARTED: mock `ws_manager`, trigger scan, verify broadcast at start
3. Test SCAN_COMPLETED: mock `ws_manager`, complete scan, verify broadcast at end
4. Test event payload structure matches `build_event()` output format
5. Test that `ws_manager` being None (test mode without WS) does not crash

**Verification:**
```bash
uv run pytest tests/test_api/test_websocket_broadcasts.py -x
```

## Test Infrastructure Updates

- Tests need a mock `ConnectionManager` to verify broadcast calls
- May need to update test fixtures to inject `ws_manager` mock into `create_app()`
- Scan-related tests need to trigger and await scan completion, not just test endpoint response

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Scan broadcasts fire from job handler, not router — need to trace the scan execution path to find correct insertion point. See `006-critical-thinking/investigation-log.md` Investigation 2.
- HEALTH_STATUS trigger not identified — deferred. See `006-critical-thinking/risk-assessment.md`.
- ws_manager may be None in some test configurations — guard with `if ws_manager:` before broadcasting.

## Commit Message

```
feat(websocket): wire broadcast calls into API operations

BL-065: Add PROJECT_CREATED broadcast in projects router, SCAN_STARTED
and SCAN_COMPLETED broadcasts in scan job handler. Events use build_event()
for consistent payload structure. HEALTH_STATUS trigger deferred.
```