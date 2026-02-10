# C4 Code Level: Black Box Tests

## Overview

- **Name**: Black Box Tests
- **Description**: End-to-end REST API tests exercising complete workflows without knowledge of internal implementation
- **Location**: `tests/test_blackbox/`
- **Language**: Python (pytest)
- **Purpose**: Validates full project/clip/video lifecycle, error handling, edge cases, pagination, and concurrent access through the HTTP API

## Code Elements

### Test Inventory (60 tests across 3 test files)

| File | Tests | Coverage |
|------|-------|----------|
| conftest.py | 0 (6 fixtures, 3 helper functions) | Shared infrastructure with full DI |
| test_core_workflow.py | 14 | Project CRUD, clip lifecycle |
| test_error_handling.py | 24 | 404 (NOT_FOUND), 422 (validation), 400 errors |
| test_edge_cases.py | 22 | Empty results, duplicates, concurrency, pagination, search |

### Fixtures (conftest.py)

- `video_repository() -> AsyncInMemoryVideoRepository` — Empty in-memory video repo
- `project_repository() -> AsyncInMemoryProjectRepository` — Empty in-memory project repo
- `clip_repository() -> AsyncInMemoryClipRepository` — Empty in-memory clip repo
- `job_queue() -> InMemoryJobQueue` — InMemoryJobQueue with scan handler registered
- `app() -> FastAPI` — FastAPI app with all test doubles injected via create_app()
- `client() -> Generator[TestClient]` — TestClient for black box API requests
- `seeded_video() -> dict[str, Any]` — Single video pre-populated in repository (async fixture)

### Helper Functions (conftest.py)

- `create_project_via_api(client: TestClient, name: str = "Test Project", **kwargs) -> dict[str, Any]` (line 92)
  - Creates project via POST /api/v1/projects
  - Accepts name and additional fields (output_width, output_height, output_fps)
  - Asserts 201 status, returns project response dict

- `add_clip_via_api(client: TestClient, project_id: str, source_video_id: str, in_point: int = 0, out_point: int = 100, timeline_position: int = 0) -> dict[str, Any]` (line 111)
  - Adds clip to project via POST /api/v1/projects/{project_id}/clips
  - Asserts 201 status, returns clip response dict

### Test Classes

- `TestProjectLifecycle` — Create, retrieve, list, delete projects through REST API (7 tests)
- `TestProjectClipWorkflow` — End-to-end project creation and clip addition (7 tests)
- `TestNotFoundErrors` — 404 responses for nonexistent resources (6 tests)
- `TestValidationErrors` — 422/400 for invalid input, constraint violations (6 tests)
- `TestClipValidationErrors` — Rust-core validation errors from _core FFmpeg layer (2 tests)
- `TestEmptyResults` — API behavior with no data (5 tests)
- `TestDuplicateHandling` — Duplicate resource handling and uniqueness (2 tests)
- `TestConcurrentRequests` — ThreadPoolExecutor concurrent access without races (2 tests)
- `TestPagination` — Paginated listing and search results (3 tests)

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.app` (create_app)
- `stoat_ferret.api.services.scan` (SCAN_JOB_TYPE, make_scan_handler)
- `stoat_ferret.db.async_repository` (AsyncInMemoryVideoRepository)
- `stoat_ferret.db.clip_repository` (AsyncInMemoryClipRepository)
- `stoat_ferret.db.project_repository` (AsyncInMemoryProjectRepository)
- `stoat_ferret.db.models` (Clip, Project, Video)
- `stoat_ferret.jobs.queue` (InMemoryJobQueue)
- `tests.factories` (make_test_video)

### External Dependencies

- `pytest`, `fastapi.testclient` (TestClient)
- `concurrent.futures` (ThreadPoolExecutor)

## Relationships

```mermaid
classDiagram
    namespace BlackBoxTestSuite {
        class Conftest {
            +video_repository()
            +project_repository()
            +clip_repository()
            +job_queue()
            +app()
            +client()
            +seeded_video()
            +create_project_via_api()
            +add_clip_via_api()
        }
        class TestProjectLifecycle {
            +test_create_and_retrieve_project()
            +test_create_project_with_custom_output()
            +test_list_projects()
            +test_delete_project()
        }
        class TestProjectClipWorkflow {
            +test_create_project_with_clips()
            +test_add_clip_to_project()
        }
        class TestErrorHandling {
            +TestNotFoundErrors
            +TestValidationErrors
            +TestClipValidationErrors
        }
        class TestEdgeCases {
            +TestEmptyResults
            +TestDuplicateHandling
            +TestConcurrentRequests
            +TestPagination
        }
    }
    class RestApiLayer {
        <<interface>>
        POST /api/v1/projects
        GET /api/v1/projects
        GET /api/v1/projects/{id}
        DELETE /api/v1/projects/{id}
        POST /api/v1/projects/{id}/clips
        POST /api/v1/videos
        GET /api/v1/videos
    }

    Conftest --> RestApiLayer : creates fixtures, test helpers
    TestProjectLifecycle --> Conftest : uses fixtures and helpers
    TestProjectClipWorkflow --> Conftest : uses fixtures and helpers
    TestErrorHandling --> Conftest : uses fixtures and helpers
    TestEdgeCases --> Conftest : uses fixtures and helpers
    TestProjectLifecycle --> RestApiLayer : exercises via HTTP
    TestProjectClipWorkflow --> RestApiLayer : exercises via HTTP
    TestErrorHandling --> RestApiLayer : verifies error responses
    TestEdgeCases --> RestApiLayer : tests edge cases
```

## Notes

- Marked with `pytest.mark.blackbox` decorator for selective test execution
- All tests use in-memory repositories for fast, deterministic execution
- No internal module knowledge required; all interaction through HTTP API
- seeded_video fixture is async and auto-used by tests requiring pre-populated video
