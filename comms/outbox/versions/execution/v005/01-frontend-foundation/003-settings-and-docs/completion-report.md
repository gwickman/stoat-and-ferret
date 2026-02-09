---
status: complete
acceptance_passed: 6
acceptance_total: 6
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 003-settings-and-docs

## Summary

Added three new settings fields (`thumbnail_dir`, `gui_static_path`, `ws_heartbeat_interval`) to the Pydantic Settings class with env var support and sensible defaults. Updated architecture, API specification, and AGENTS documentation to reflect v005 Theme 01 changes including the React frontend, WebSocket endpoint, and static file serving.

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| FR-001 | `STOAT_THUMBNAIL_DIR` env var parsed into `Settings.thumbnail_dir` | Pass |
| FR-002 | `STOAT_GUI_STATIC_PATH` env var parsed into `Settings.gui_static_path` | Pass |
| FR-003 | `STOAT_WS_HEARTBEAT_INTERVAL` env var parsed into `Settings.ws_heartbeat_interval` | Pass |
| FR-004 | Architecture doc reflects React frontend, WebSocket endpoint, and static file serving | Pass |
| FR-005 | API spec includes WebSocket endpoint schema and static file serving configuration | Pass |
| FR-006 | AGENTS.md includes frontend commands and updated directory structure | Pass |

## Changes Made

### Settings (`src/stoat_ferret/api/settings.py`)
- Added `thumbnail_dir: str` field (default: `data/thumbnails`, env: `STOAT_THUMBNAIL_DIR`)
- Added `gui_static_path: str` field (default: `gui/dist`, env: `STOAT_GUI_STATIC_PATH`)
- Added `ws_heartbeat_interval: int` field (default: 30, env: `STOAT_WS_HEARTBEAT_INTERVAL`, min: 1)

### Tests (`tests/test_api/test_settings.py`)
- Added 6 tests covering defaults and env var overrides for all three new settings fields

### Documentation
- `docs/design/02-architecture.md`: Updated client layer diagram, added `/ws` and `/gui` endpoint groups, added WebSocket transport and frontend static serving descriptions, added `gui/` to directory structure
- `docs/design/05-api-specification.md`: Added `/ws` and `/gui` to endpoint group summary, added WebSocket endpoint and GUI static files sections with message schema and event types
- `AGENTS.md`: Added `gui/` to project structure, added frontend commands section, added frontend quality gate section

## Test Results

- 605 passed, 15 skipped, 93.23% coverage
- All quality gates pass (ruff lint, ruff format, mypy, pytest)
