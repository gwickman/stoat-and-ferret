# FastAPI Testing Patterns for v003

## Summary

This exploration documents testing patterns for FastAPI endpoints in stoat-and-ferret v003. The recommended architecture integrates with the existing pytest infrastructure while supporting async operations and dependency injection for test doubles.

## Recommended Testing Architecture

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (existing + new API fixtures)
├── test_api/                # NEW: API endpoint tests
│   ├── __init__.py
│   ├── conftest.py          # API-specific fixtures
│   ├── test_videos.py       # Video endpoint tests
│   └── test_health.py       # Health check tests
├── test_repository_contract.py  # Existing
├── test_executor.py             # Existing
└── ...
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test client | `TestClient` (sync) | Simpler, works with existing pytest patterns |
| Async tests | `@pytest.mark.anyio` + `AsyncClient` | Only when testing async operations directly |
| Dependency injection | `app.dependency_overrides` | Standard FastAPI pattern |
| Test doubles | `InMemoryVideoRepository`, `FakeFFmpegExecutor` | Already exist in codebase |
| Markers | `pytest.mark.api` | Distinguish API tests from unit tests |

### Test Double Strategy

The codebase already has test doubles that can be injected via FastAPI's dependency override system:

1. **InMemoryVideoRepository** - In-memory video storage (existing in `repository.py`)
2. **FakeFFmpegExecutor** - Replays recorded FFmpeg interactions (existing in `executor.py`)

These follow the contract testing pattern already established in `test_repository_contract.py`.

## Files in This Exploration

| File | Description |
|------|-------------|
| `testclient-usage.md` | TestClient patterns with sync/async examples |
| `dependency-injection.md` | Dependency override patterns for test doubles |
| `conftest-additions.md` | Concrete fixtures to add to conftest.py |
| `pytest-config.md` | Required pytest/pyproject.toml configuration |

## Quick Start Example

```python
# tests/test_api/test_videos.py
from fastapi.testclient import TestClient
from stoat_ferret.api.app import app
from stoat_ferret.db.repository import InMemoryVideoRepository

def test_list_videos(client: TestClient, video_repository: InMemoryVideoRepository):
    """GET /videos returns empty list when no videos exist."""
    response = client.get("/videos")
    assert response.status_code == 200
    assert response.json() == {"videos": [], "total": 0}
```

## Integration with Existing Infrastructure

The existing `conftest.py` provides:
- `sample_video_path` (session-scoped) - Generated test video file
- `video_only_path` (session-scoped) - Video without audio
- `requires_ffmpeg` / `requires_ffprobe` markers

New fixtures will work alongside these, inheriting the session-scoped video fixtures when needed for integration tests.

## Next Steps for v003

1. Add `fastapi` and `httpx` to dependencies
2. Implement fixtures from `conftest-additions.md`
3. Add pytest configuration from `pytest-config.md`
4. Create `tests/test_api/` directory structure
5. Write first endpoint tests using patterns from `testclient-usage.md`
