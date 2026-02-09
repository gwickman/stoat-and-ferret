# Requirements - 003: Settings and Docs

## Goal

Add new settings fields for thumbnail directory, GUI static path, and WebSocket heartbeat interval, and update architecture, API, and AGENTS documentation to reflect v005 changes.

## Background

Features 001 and 002 introduced new configurable parameters that need formal settings fields in the Pydantic `Settings` class. Documentation must be updated to reflect the new frontend project structure, WebSocket endpoint, and static file serving configuration. This feature collects settings and doc updates to keep Features 001 and 002 focused on code.

**Backlog Items:** BL-003, BL-029

## Functional Requirements

**FR-001: Thumbnail directory setting**
Add `thumbnail_dir: str = Field(default="data/thumbnails")` to Settings class, configurable via `STOAT_THUMBNAIL_DIR` env var.
- AC: `STOAT_THUMBNAIL_DIR` env var is parsed into `Settings.thumbnail_dir`

**FR-002: GUI static path setting**
Add `gui_static_path: str = Field(default="gui/dist")` to Settings class, configurable via `STOAT_GUI_STATIC_PATH` env var.
- AC: `STOAT_GUI_STATIC_PATH` env var is parsed into `Settings.gui_static_path`

**FR-003: WebSocket heartbeat setting**
Add `ws_heartbeat_interval: int = Field(default=30)` to Settings class, configurable via `STOAT_WS_HEARTBEAT_INTERVAL` env var.
- AC: `STOAT_WS_HEARTBEAT_INTERVAL` env var is parsed into `Settings.ws_heartbeat_interval`

**FR-004: Architecture documentation update**
Update `docs/design/02-architecture.md` to include frontend project structure and WebSocket transport layer.
- AC: Architecture doc reflects React frontend, WebSocket endpoint, and static file serving

**FR-005: API documentation update**
Update `docs/design/05-api-specification.md` to include `/ws` endpoint and `/gui` static mount.
- AC: API spec includes WebSocket endpoint schema and static file serving configuration

**FR-006: AGENTS.md update**
Update `AGENTS.md` with frontend development commands (`npm run dev`, `npm run build`, `npx vitest run`) and updated project structure.
- AC: AGENTS.md includes frontend commands and updated directory structure

## Non-Functional Requirements

**NFR-001: Settings backward compatibility**
All new settings have sensible defaults. Existing deployments without new env vars continue to work.
- Metric: Application starts successfully without any new env vars set

## Out of Scope

- GUI architecture document (08-gui-architecture.md) updates -- that doc describes the target, not the implementation
- Roadmap updates
- User-facing documentation or README changes

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests | New settings fields parse from env vars (`STOAT_THUMBNAIL_DIR`, `STOAT_GUI_STATIC_PATH`, `STOAT_WS_HEARTBEAT_INTERVAL`) |
| Integration tests | None (documentation updates) |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.