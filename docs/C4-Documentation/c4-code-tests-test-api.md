# C4 Code Level: API Tests

## Overview

- **Name**: API Tests
- **Description**: Comprehensive pytest test suite for all REST API endpoints of the stoat-and-ferret video editor
- **Location**: `tests/test_api/`
- **Language**: Python (pytest, async)
- **Purpose**: Validates HTTP endpoint behavior, request/response contracts, middleware, DI wiring, settings, and static file serving

## Code Elements

### Test Inventory (117 tests across 14 files)

| File | Tests | Coverage |
|------|-------|----------|
| conftest.py | 0 (7 fixtures, 2 helper classes) | Shared test infrastructure |
| test_middleware.py | 18 | CorrelationIdMiddleware, MetricsMiddleware |
| test_clips.py | 4 | Clip CRUD (POST/GET/PATCH/DELETE /api/v1/projects/{id}/clips) |
| test_projects.py | 7 | Project CRUD (POST/GET/DELETE /api/v1/projects) |
| test_app.py | 7 | create_app(), FastAPI instance, OpenAPI docs |
| test_di_wiring.py | 3 | Dependency injection via create_app() kwargs |
| test_health.py | 6 | GET /health/live, GET /health/ready |
| test_factory_api.py | 6 | ProjectFactory, ApiFactory integration |
| test_jobs.py | 5 | GET /api/v1/jobs/{id}, async scan workflow |
| test_gui_static.py | 10 | /gui static file mount, index.html serving |
| test_settings.py | 34 | Settings class, env overrides, validation |
| test_thumbnail_endpoint.py | 1 | GET /api/v1/videos/{id}/thumbnail |
| test_videos.py | 16 | Video CRUD, search, scan (POST/GET/DELETE /api/v1/videos) |

### Key Fixtures (conftest.py)

- `video_repository() -> AsyncInMemoryVideoRepository` — Empty in-memory video store
- `project_repository() -> AsyncInMemoryProjectRepository` — Empty in-memory project store
- `clip_repository() -> AsyncInMemoryClipRepository` — Empty in-memory clip store
- `job_queue() -> InMemoryJobQueue` — Job queue with scan handler registered
- `app() -> FastAPI` — App wired with all in-memory test doubles via create_app() kwargs
- `client() -> Generator[TestClient]` — Synchronous test client with TestClient context manager
- `api_factory() -> ApiFactory` — Builder for creating test data via HTTP

### Helper Classes (conftest.py)

- `ApiFactory(client, video_repository)` — Provides `.project()` method returning builder
  - `__init__(client: TestClient, video_repository: AsyncInMemoryVideoRepository)`
  - `project() -> _ApiProjectBuilder` — Start building a project for API creation

- `_ApiProjectBuilder(client, video_repository)` — Fluent builder for projects and clips
  - `with_name(name: str) -> _ApiProjectBuilder` — Set project name
  - `with_output(width: int, height: int, fps: int) -> _ApiProjectBuilder` — Set output dimensions
  - `with_clip(in_point: int, out_point: int, timeline_position: int) -> _ApiProjectBuilder` — Add clip with auto-seeded video
  - `create() -> dict[str, Any]` — Create project via API, returns response dict

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
- `stoat_ferret.jobs.queue` (InMemoryJobQueue, JobOutcome, JobStatus)
- `stoat_ferret.ffmpeg.probe` (VideoMetadata)
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
        class _ApiProjectBuilder {
            -_factory ProjectFactory
            -_client TestClient
            -_video_repository AsyncInMemoryVideoRepository
            -_video_ids list
            +with_name(name) self
            +with_output(width, height, fps) self
            +with_clip(in_point, out_point, timeline_position) self
            +create() dict
        }
    }
    class RestApi {
        GET /health/live
        GET /health/ready
        POST /api/v1/projects
        GET /api/v1/projects/{id}
        DELETE /api/v1/projects/{id}
        POST /api/v1/projects/{id}/clips
        GET /api/v1/videos
        POST /api/v1/videos
        GET /api/v1/videos/{id}
        GET /api/v1/videos/{id}/thumbnail
        GET /api/v1/jobs/{id}
        GET /gui/static files
    }

    Conftest --> ApiFactory : provides
    Conftest --> RestApi : test fixtures inject doubles
    ApiFactory --> _ApiProjectBuilder : creates
    _ApiProjectBuilder --> RestApi : exercises via HTTP
```

## Notes

- All tests use in-memory test doubles for repositories and job queue for deterministic, fast execution
- The `app` fixture uses create_app() parameter injection (not dependency_overrides) to wire test doubles
- TestClient context manager handles lifespan events automatically
- ApiFactory pattern enables fluent API test data creation with automatic video seeding
