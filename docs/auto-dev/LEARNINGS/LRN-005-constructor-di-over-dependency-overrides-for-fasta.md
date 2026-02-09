## Context

FastAPI's `dependency_overrides` dict is the standard approach for replacing dependencies in tests, but it has drawbacks: it's global mutable state, requires cleanup, and the override mechanism is opaque.

## Learning

Use constructor-based dependency injection via `create_app()` parameters instead of `dependency_overrides`. Dependencies check `app.state` first and fall back to constructing production instances when parameters are `None`. This makes the test wiring explicit and eliminates global mutable state.

## Evidence

- v004 Theme 01 Feature 002 (dependency-injection): Replaced 4 `dependency_overrides` entries with `create_app(video_repository=..., project_repository=..., clip_repository=...)` parameter injection.
- Zero test failures during migration.
- Pattern extended naturally in Theme 03 with `create_app(job_queue=...)`.

## Application

- Prefer constructor/factory parameters over global override mechanisms for test dependency injection.
- Keep production defaults (None → construct real instance) so the same factory works for both production and test.
- This pattern composes well: each new injectable dependency is just another optional parameter.