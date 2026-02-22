# C4 Component Level: Data Access Layer

## Overview
- **Name**: Data Access Layer
- **Description**: SQLite-based persistence layer with repository pattern for videos, projects, clips, and audit logging, plus application-wide infrastructure including structured logging configuration
- **Type**: Data Access
- **Technology**: Python, SQLite, aiosqlite, structlog

## Purpose

The Data Access Layer provides all data persistence and retrieval for stoat-and-ferret using the repository pattern. It defines protocol interfaces for video, project, and clip repositories, with both synchronous (SQLite) and asynchronous (aiosqlite) implementations, plus in-memory implementations for testing. The layer includes domain model definitions (with effects and transitions stored as JSON), database schema management, FTS5 full-text search, and audit logging.

The domain models include a Rust validation bridge: the `Clip` model delegates validation to `stoat_ferret_core` via `Clip.validate()`, ensuring timeline constraints are enforced at the Rust level. The `AuditLogger` records change history for all video entities with JSON diffs.

The package root (`stoat_ferret`) providing version metadata and structured logging configuration via `configure_logging()` is included here as foundational infrastructure consumed by the application lifespan on startup. Structured logging setup is wired into the lifespan so that all components use consistent JSON or console output.

## Software Features
- **Repository Pattern**: Protocol-based abstractions with SQLite and in-memory implementations for all three domain entities
- **Async Support**: Full async/await repository implementations via aiosqlite for FastAPI integration
- **Domain Models**: Dataclass definitions for Video, Project (with transitions as JSON), Clip (with effects as JSON), and AuditEntry with Rust validation bridge
- **Full-Text Search**: FTS5 index on video filename/path for fast search
- **Audit Logging**: Change tracking with operation, entity type, entity ID, and JSON diff
- **Schema Management**: DDL for all tables, indexes, and FTS triggers with idempotent `IF NOT EXISTS` semantics
- **Structured Logging**: Application-wide structlog configuration with JSON/console output, wired into lifespan startup
- **Test Doubles**: In-memory repositories with deepcopy isolation and seed helpers for all three entity types

## Code Elements

This component contains:
- [c4-code-stoat-ferret-db.md](./c4-code-stoat-ferret-db.md) -- Repository protocols/impls for Video, Project, Clip; domain models; schema; audit logger
- [c4-code-python-db.md](./c4-code-python-db.md) -- Database layer overview with models and repository pattern
- [c4-code-stoat-ferret.md](./c4-code-stoat-ferret.md) -- Package root with version metadata and `configure_logging()` for structured logging setup

## Interfaces

### Video Repository (Async)
- **Protocol**: Python protocol (async)
- **Operations**: `add`, `get`, `get_by_path`, `list_videos`, `search`, `count`, `update`, `delete`

### Project Repository (Async)
- **Protocol**: Python protocol (async)
- **Operations**: `add`, `get`, `list_projects`, `update`, `delete`

### Clip Repository (Async)
- **Protocol**: Python protocol (async)
- **Operations**: `add`, `get`, `list_by_project`, `update`, `delete`

### Logging Configuration
- **Operations**: `configure_logging(json_format: bool = True, level: int = logging.INFO) -> None` -- Sets up structlog with shared processors, JSON or console rendering, stdlib integration, and idempotent StreamHandler registration

## Dependencies

### Components Used
- **Python Bindings Layer**: Clip model uses `stoat_ferret_core` for Rust-side clip validation via `validate_clip()`

### External Systems
- **SQLite**: Persistent storage via sqlite3 (sync) and aiosqlite (async)
- **structlog**: Structured logging framework with BoundLogger, ProcessorFormatter, JSONRenderer, ConsoleRenderer

## Component Diagram

```mermaid
C4Component
    title Component Diagram for Data Access Layer

    Container_Boundary(data, "Data Access Layer") {
        Component(models, "Domain Models", "Python dataclasses", "Video, Project, Clip, AuditEntry")
        Component(schema, "Schema Manager", "Python/SQLite", "DDL, tables, indexes, FTS5 triggers")
        Component(video_repo, "Video Repository", "Python/aiosqlite", "Async CRUD with FTS5 search")
        Component(project_repo, "Project Repository", "Python/aiosqlite", "Async project CRUD")
        Component(clip_repo, "Clip Repository", "Python/aiosqlite", "Async clip CRUD, timeline ordering")
        Component(audit, "Audit Logger", "Python/SQLite", "Change tracking with JSON diffs")
        Component(logging_mod, "Logging Config", "Python/structlog", "JSON/console logging setup, wired into lifespan")
    }

    Rel(video_repo, schema, "queries tables from")
    Rel(video_repo, audit, "logs changes via")
    Rel(project_repo, schema, "queries tables from")
    Rel(clip_repo, schema, "queries tables from")
    Rel(video_repo, models, "returns/accepts")
    Rel(project_repo, models, "returns/accepts")
    Rel(clip_repo, models, "returns/accepts")
```
