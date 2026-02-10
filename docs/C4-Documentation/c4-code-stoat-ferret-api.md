# C4 Code Level: API Application

## Overview
- **Name**: API Application
- **Description**: FastAPI application factory, settings, and entry point for the stoat-and-ferret video editor API
- **Location**: `src/stoat_ferret/api/`
- **Language**: Python
- **Purpose**: Configure and wire together all API components including routers, middleware, lifespan management, and static file serving

## Code Elements

### Functions/Methods

#### app.py

- `async lifespan(app: FastAPI) -> AsyncGenerator[None, None]`
  - Description: Manage application lifespan - open database, start job worker on startup; cancel worker, close database on shutdown. Skips DB setup when dependencies are injected (test mode).
  - Location: `src/stoat_ferret/api/app.py:38`
  - Dependencies: `aiosqlite`, `get_settings`, `AsyncSQLiteVideoRepository`, `ThumbnailService`, `RealFFmpegExecutor`, `AsyncioJobQueue`, `ConnectionManager`

- `create_app(*, video_repository, project_repository, clip_repository, job_queue, ws_manager, gui_static_path) -> FastAPI`
  - Description: Application factory - creates and configures FastAPI app with routers, middleware, metrics, WebSocket, and optional dependency injection for testing
  - Location: `src/stoat_ferret/api/app.py:90`
  - Dependencies: All routers, middleware, settings, `ConnectionManager`, `prometheus_client`, `StaticFiles`

#### settings.py

- `get_settings() -> Settings`
  - Description: Cached settings loader using lru_cache
  - Location: `src/stoat_ferret/api/settings.py:93`
  - Dependencies: `Settings`

#### __main__.py

- `main() -> None`
  - Description: Entry point - run API server with uvicorn using configured host/port
  - Location: `src/stoat_ferret/api/__main__.py:14`
  - Dependencies: `create_app`, `get_settings`, `uvicorn`

### Classes/Modules

#### settings.py

- `Settings(BaseSettings)`
  - Description: Application configuration with environment variable support (STOAT_ prefix)
  - Location: `src/stoat_ferret/api/settings.py:13`
  - Fields:
    - `database_path: str` (default "data/stoat.db")
    - `api_host: str` (default "127.0.0.1")
    - `api_port: int` (default 8000)
    - `debug: bool` (default False)
    - `log_level: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"]` (default "INFO")
    - `thumbnail_dir: str` (default "data/thumbnails")
    - `gui_static_path: str` (default "gui/dist")
    - `ws_heartbeat_interval: int` (default 30)
    - `allowed_scan_roots: list[str]` (default [])
  - Properties:
    - `database_path_resolved -> Path`
  - Dependencies: `pydantic_settings.BaseSettings`

## Dependencies

### Internal Dependencies
- `stoat_ferret.api.middleware` - CorrelationIdMiddleware, MetricsMiddleware
- `stoat_ferret.api.routers` - health, videos, projects, jobs routers
- `stoat_ferret.api.routers.ws` - websocket_endpoint
- `stoat_ferret.api.services` - scan handler, ThumbnailService
- `stoat_ferret.api.websocket` - ConnectionManager
- `stoat_ferret.db` - Repository implementations and protocols
- `stoat_ferret.ffmpeg.executor` - RealFFmpegExecutor
- `stoat_ferret.jobs.queue` - AsyncioJobQueue

### External Dependencies
- `fastapi` - FastAPI, StaticFiles
- `uvicorn` - ASGI server
- `aiosqlite` - Async SQLite database
- `structlog` - Structured logging
- `prometheus_client` - make_asgi_app for /metrics endpoint
- `pydantic_settings` - BaseSettings with env var support

## Relationships

```mermaid
---
title: Code Diagram for API Application
---
flowchart TB
    subgraph app.py
        create_app[create_app]
        lifespan[lifespan]
    end

    subgraph settings.py
        Settings
        get_settings
    end

    subgraph __main__.py
        main
    end

    main --> create_app
    main --> get_settings
    create_app --> lifespan
    lifespan --> Settings

    subgraph Registered Components
        routers[health, videos,<br/>projects, jobs routers]
        middleware[CorrelationId +<br/>Metrics middleware]
        ws_route[/ws endpoint]
        metrics_app[/metrics Prometheus]
        gui_mount[/gui static files]
    end

    create_app --> routers
    create_app --> middleware
    create_app --> ws_route
    create_app --> metrics_app
    create_app --> gui_mount

    subgraph Lifespan Resources
        db[aiosqlite connection]
        job_queue[AsyncioJobQueue]
        worker[background worker task]
        thumb_svc[ThumbnailService]
    end

    lifespan --> db
    lifespan --> job_queue
    lifespan --> worker
    lifespan --> thumb_svc
```
