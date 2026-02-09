## Context

When a FastAPI backend optionally serves a built frontend (e.g., React/Vite), the `StaticFiles` mount raises errors if the target directory doesn't exist — such as during backend-only tests or before the first frontend build.

## Learning

Only mount `StaticFiles` when the target directory actually exists. This conditional mount pattern decouples backend testing from frontend build state. Combined with auto-loading from settings when not explicitly provided, this enables both test isolation and seamless production serving.

## Evidence

- v005 Theme 01 (frontend-scaffolding): Conditional mount ensured `pytest` passed without requiring `npm run build` first
- v005 Theme 04 (playwright-setup): Modified `create_app()` to auto-load `gui_static_path` from settings when not explicitly provided, enabling `uvicorn --factory` to serve the built frontend for E2E tests
- Backend test suite (627 tests) ran without frontend build throughout all 11 features

## Application

- Any FastAPI/Starlette project that optionally serves a built SPA frontend
- Services where a frontend build artifact may or may not be present at runtime
- Pattern: check `Path(static_path).is_dir()` before mounting, and provide DI override for tests