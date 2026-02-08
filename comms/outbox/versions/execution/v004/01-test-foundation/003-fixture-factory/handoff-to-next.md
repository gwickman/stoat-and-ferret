# Handoff: 003-fixture-factory → next feature

## What Was Done

- Created `tests/factories.py` with `ProjectFactory` (builder pattern) and `make_test_video()` helper
- Added `project_factory` pytest fixture (available globally) and `api_factory` fixture (available in `tests/test_api/`)
- Factory supports `build()` for domain objects and `create_via_api(client)` for HTTP path testing

## How to Use

### Unit tests (no HTTP)
```python
from tests.factories import ProjectFactory

# Simple project
project = ProjectFactory().with_name("My Project").build()

# Project with clips and videos (for seeding repositories)
project, videos, clips = (
    ProjectFactory()
    .with_clip(in_point=0, out_point=100)
    .with_clip(in_point=100, out_point=200, timeline_position=100)
    .build_with_clips()
)
```

### Integration tests (full HTTP path)
```python
# Using ProjectFactory directly (must pre-seed videos)
result = ProjectFactory().with_name("Test").create_via_api(client)

# Using ApiFactory fixture (auto-seeds videos)
builder = api_factory.project().with_name("Test")
await builder.with_clip(in_point=0, out_point=100)
result = builder.create()
```

## Incremental Migration

Existing tests were NOT migrated — the factory is available for new tests and incremental adoption. When modifying existing tests, consider switching them to use the factory.

## Future Work

- Add `with_text_overlay()` when TextOverlay domain model is implemented
- Migrate remaining inline Project/Clip construction in existing tests as they are touched
