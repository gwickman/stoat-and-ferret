# test_api — HTTP-layer test coverage pattern (LRN-719)

## Overview

Each router module in `src/stoat_ferret/api/routers/` must have a corresponding
`tests/test_api/test_<router>.py` that exercises all endpoints via FastAPI's
synchronous `TestClient`.

## Pattern

```python
from fastapi.testclient import TestClient
from stoat_ferret.api.app import create_app
from stoat_ferret.db.<foo>_repository import AsyncInMemory<Foo>Repository

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = create_app(foo_repository=AsyncInMemory<Foo>Repository(), ...)
    with TestClient(app) as c:
        yield c
```

Key rules:

- **Pass `video_repository=AsyncInMemoryVideoRepository()` (or another repo) to
  trigger DI mode**, which sets `app.state._deps_injected = True` and skips the
  lifespan DB setup entirely.
- **Patch raw-DB helpers** (e.g. `_validate_voice_track`) that access
  `request.app.state.db` — unavailable in DI mode — using `AsyncMock`.
- **Set `_settings` manually** inside the `with TestClient(app) as c:` block
  when the router reads `request.app.state._settings` (e.g. TTS voices).
- Each test file covers: create (201), list (200), get by id (200), get 404,
  patch/update (200), delete (204 + subsequent 404), error paths (422/503).

## Definition of Done

New API router must ship with at least one `tests/test_api/test_<router>.py`
covering the happy path for each endpoint and one regression test for any
known field-mapping bug.

## Background

BL-577 shipped because the `audio_path` ↔ `generated_asset_id` serialisation
path had no HTTP-layer test. This gap was first codified in LRN-719 and closed
by BL-580 (`test_tts.py`).
