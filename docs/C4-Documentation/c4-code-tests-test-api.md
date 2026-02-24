# C4 Code Level: API Tests

## Overview

- **Name**: API Tests
- **Description**: Comprehensive pytest test suite for all REST API endpoints of the stoat-and-ferret video editor
- **Location**: `tests/test_api/`
- **Language**: Python (pytest, async)
- **Purpose**: Validates HTTP endpoint behavior, request/response contracts, middleware, DI wiring, settings, effects CRUD, transitions, filesystem browsing, SPA routing, WebSocket broadcasts, and static file serving
- **Parent Component**: TBD

## Code Elements

### Test Inventory (215 tests across 17 files)

| File | Tests | Coverage |
|------|-------|----------|
| conftest.py | 0 (7 fixtures, 2 helper classes) | Shared test infrastructure |
| test_app.py | 7 | create_app(), FastAPI instance, OpenAPI docs |
| test_clips.py | 13 | Clip CRUD (POST/GET/PATCH/DELETE .../clips) |
| test_di_wiring.py | 7 | Dependency injection via create_app() kwargs |
| test_effects.py | 64 | Effect discovery, preview, CRUD, transitions |
| test_factory_api.py | 5 | ProjectFactory, ApiFactory integration |
| test_filesystem.py | 8 | GET /api/v1/filesystem/directories |
| test_gui_static.py | 5 | /gui static file mount, index.html serving |
| test_health.py | 6 | GET /health/live, GET /health/ready |
| test_jobs.py | 10 | GET/POST /api/v1/jobs/{id}, cancel workflow |
| test_middleware.py | 9 | CorrelationIdMiddleware, MetricsMiddleware |
| test_projects.py | 12 | Project CRUD (POST/GET/DELETE /api/v1/projects) |
| test_settings.py | 17 | Settings class, env overrides, validation |
| test_spa_routing.py | 9 | SPA catch-all routing at /gui |
| test_thumbnail_endpoint.py | 5 | GET /api/v1/videos/{id}/thumbnail |
| test_videos.py | 33 | Video CRUD, search, scan (POST/GET/DELETE /api/v1/videos) |
| test_websocket_broadcasts.py | 10 | WebSocket event broadcasting for scan/project events |

### Key Fixtures (conftest.py)

- `video_repository() -> AsyncInMemoryVideoRepository` -- Empty in-memory video store
- `project_repository() -> AsyncInMemoryProjectRepository` -- Empty in-memory project store
- `clip_repository() -> AsyncInMemoryClipRepository` -- Empty in-memory clip store
- `job_queue() -> InMemoryJobQueue` -- Job queue with scan handler registered
- `app() -> FastAPI` -- App wired with all in-memory test doubles via create_app() kwargs
- `client() -> Generator[TestClient]` -- Synchronous test client with TestClient context manager
- `api_factory() -> ApiFactory` -- Builder for creating test data via HTTP

### Helper Classes (conftest.py)

- `ApiFactory(client, video_repository)` -- Provides `.project()` method returning builder
- `_ApiProjectBuilder(client, video_repository)` -- Fluent builder for projects and clips with auto video seeding

### test_effects.py (64 tests)

Tests the entire effects subsystem through the API:
- Effect discovery: GET /api/v1/effects lists all built-in effects
- Effect preview: POST /api/v1/effects/preview with valid/invalid params
- Effect CRUD on clips: POST/PATCH/DELETE .../clips/{id}/effects/{index}
- Transitions: POST .../effects/transition with adjacency validation
- Error handling: unknown effect types, invalid parameters, non-adjacent clips

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.app` (create_app)
- `stoat_ferret.api.middleware.correlation` (CorrelationIdMiddleware)
- `stoat_ferret.api.settings` (Settings, get_settings)
- `stoat_ferret.api.services.scan` (SCAN_JOB_TYPE, make_scan_handler)
- `stoat_ferret.api.services.thumbnail` (ThumbnailService)
- `stoat_ferret.db.async_repository` (AsyncInMemoryVideoRepository)
- `stoat_ferret.db.clip_repository` (AsyncInMemoryClipRepository)
- `stoat_ferret.db.project_repository` (AsyncInMemoryProjectRepository)
- `stoat_ferret.db.models` (Clip, Project, Video)
- `stoat_ferret.effects.definitions` (create_default_registry)
- `stoat_ferret.effects.registry` (EffectRegistry)
- `stoat_ferret.jobs.queue` (InMemoryJobQueue, JobOutcome, JobStatus)
- `tests.factories` (make_test_video, ProjectFactory)

### External Dependencies

- `pytest`, `pytest-asyncio`
- `fastapi` (FastAPI, TestClient)
- `pydantic` (ValidationError)
- `unittest.mock` (patch, AsyncMock, MagicMock)

## Relationships

```mermaid
classDiagram
    namespace ApiTestSuite {
        class Conftest {
            +video_repository()
            +project_repository()
            +clip_repository()
            +job_queue()
            +app()
            +client()
            +api_factory()
        }
        class ApiFactory {
            -_client TestClient
            -_video_repository AsyncInMemoryVideoRepository
            +project() _ApiProjectBuilder
        }
    }
    class RestApi {
        GET /health/*
        CRUD /api/v1/projects
        CRUD .../clips
        CRUD .../effects
        POST .../effects/transition
        CRUD /api/v1/videos
        GET /api/v1/jobs/{id}
        POST .../jobs/{id}/cancel
        GET /api/v1/effects
        POST /api/v1/effects/preview
        GET /api/v1/filesystem/directories
    }

    Conftest --> ApiFactory : provides
    Conftest --> RestApi : test fixtures inject doubles
    ApiFactory --> RestApi : exercises via HTTP
```

## Notes

- All tests use in-memory test doubles for repositories and job queue for deterministic, fast execution
- The `app` fixture uses create_app() parameter injection (not dependency_overrides) to wire test doubles
- TestClient context manager handles lifespan events automatically
- ApiFactory pattern enables fluent API test data creation with automatic video seeding
- test_effects.py is the largest test file (64 tests) covering the full effects and transitions subsystem
- test_websocket_broadcasts.py (10 tests) validates real-time event broadcasting
- test_filesystem.py (8 tests) validates directory browsing with scan root security
