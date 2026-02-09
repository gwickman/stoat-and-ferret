## Context

Test suites need different levels of integration: unit tests want domain objects directly, while integration tests need to exercise the full HTTP stack.

## Learning

Implement test fixture factories with a builder pattern that supports two output modes: `build()` for creating domain objects directly (unit tests) and `create_via_api()` for exercising the full HTTP path (integration/blackbox tests). This avoids forcing a single testing style while providing consistent test data construction.

## Evidence

- v004 Theme 01 Feature 003 (fixture-factory): `ProjectFactory` with `.with_clip()` chaining, `build()` returning domain objects, and `create_via_api()` using TestClient.
- Theme 02 blackbox tests consumed `create_via_api()` for all integration tests.
- `build_with_clips()` provided `(project, videos, clips)` tuples for seeding InMemory repositories.

## Application

- Design test factories with at least two output modes: direct object construction and full-stack integration.
- Use builder/chaining pattern for readable, composable test data setup.
- Keep sync `seed()` helpers on test doubles to reduce async boilerplate in unit tests.