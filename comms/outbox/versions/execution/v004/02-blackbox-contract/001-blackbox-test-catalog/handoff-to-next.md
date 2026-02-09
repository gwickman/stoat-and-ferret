# Handoff: 001-blackbox-test-catalog → next feature

## What Was Done

- Created `tests/test_blackbox/` package with 30 black box tests
- All tests use `@pytest.mark.blackbox` and can be run with `pytest -m blackbox`
- Tests use in-memory test doubles via `create_app()` DI — no FFmpeg or database needed
- Conftest provides `client`, repository fixtures, `seeded_video`, and helper functions

## Patterns to Reuse

### Creating test data via API
```python
from tests.test_blackbox.conftest import create_project_via_api, add_clip_via_api

project = create_project_via_api(client, name="My Project")
clip = add_clip_via_api(client, project_id=project["id"], source_video_id=video_id)
```

### Seeding videos (async fixture)
Videos need to be seeded directly into the repository since the scan endpoint requires real files:
```python
@pytest.fixture
async def _seed_video(self, video_repository):
    video = make_test_video()
    await video_repository.add(video)
    return {"id": video.id}
```

## What Remains

- Full scan workflow tests (with real video files and FFmpeg) — belongs to BL-024 contract tests
- Performance/load testing of black box scenarios — belongs to BL-026
- Additional edge cases as new API endpoints are added in future versions
