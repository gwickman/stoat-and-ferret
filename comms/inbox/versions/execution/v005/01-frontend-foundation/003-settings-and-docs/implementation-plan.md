# Implementation Plan - 003: Settings and Docs

## Overview

Add three new settings fields to the Pydantic Settings class for thumbnail directory, GUI static path, and WebSocket heartbeat interval. Update architecture, API, and AGENTS documentation to reflect all v005 Theme 01 changes.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/settings.py` | Modify | Add `thumbnail_dir`, `gui_static_path`, `ws_heartbeat_interval` fields |
| `tests/test_settings.py` | Modify | Add tests for new settings fields |
| `docs/design/02-architecture.md` | Modify | Add frontend project structure and WebSocket layer |
| `docs/design/05-api-specification.md` | Modify | Add `/ws` endpoint and `/gui` static mount |
| `AGENTS.md` | Modify | Add frontend commands and updated project structure |

## Implementation Stages

### Stage 1: Settings Fields

1. Add `thumbnail_dir: str = Field(default="data/thumbnails")` with `STOAT_THUMBNAIL_DIR` env prefix
2. Add `gui_static_path: str = Field(default="gui/dist")` with `STOAT_GUI_STATIC_PATH` env prefix
3. Add `ws_heartbeat_interval: int = Field(default=30)` with `STOAT_WS_HEARTBEAT_INTERVAL` env prefix
4. Add unit tests verifying env var parsing for each new field

**Verification:**
```bash
uv run pytest tests/test_settings.py -v
```

### Stage 2: Documentation Updates

1. Update `docs/design/02-architecture.md`:
   - Add `gui/` to project structure diagram
   - Add WebSocket transport layer description
   - Add static file serving architecture
2. Update `docs/design/05-api-specification.md`:
   - Add `/ws` WebSocket endpoint with message schema
   - Add `/gui` static file mount description
3. Update `AGENTS.md`:
   - Add frontend commands (`npm run dev`, `npm run build`, `npx vitest run`)
   - Update project structure to include `gui/` directory
   - Add frontend quality gate commands

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Test Infrastructure Updates

- Settings tests extended with new field assertions

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

None specific to this feature. Settings additions are backward-compatible (all have defaults).

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: add v005 settings fields and update architecture docs

- Add thumbnail_dir, gui_static_path, ws_heartbeat_interval settings
- Update architecture doc with frontend and WebSocket layers
- Update API spec with /ws endpoint and /gui static mount
- Update AGENTS.md with frontend development commands

Implements BL-003, BL-029 (settings/docs portion)
```