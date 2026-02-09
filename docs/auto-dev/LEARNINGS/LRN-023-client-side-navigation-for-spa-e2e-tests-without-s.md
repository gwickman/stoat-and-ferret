## Context

When a FastAPI backend serves a React SPA via `StaticFiles`, the server doesn't handle SPA fallback routing. Direct URL navigation to sub-paths like `/gui/library` returns 404 because `StaticFiles` looks for a literal file at that path.

## Learning

E2E tests for SPAs served via static file mounts must navigate via client-side routing (clicking UI elements) starting from the root path, not via direct URL navigation to sub-paths. This accurately reflects how users interact with the application and avoids false failures from missing server-side routing.

## Evidence

- v005 Theme 04 (e2e-test-suite): All E2E tests navigate by starting at `/gui/` and clicking tab elements
- Direct URL navigation to `/gui/library` or `/gui/projects` would fail with FastAPI's `StaticFiles` mount
- Tests accurately reflect user behavior (click-based navigation)
- This limitation also means bookmarks to sub-routes won't work — identified as tech debt (SPA fallback routing)

## Application

- Any SPA served via static file hosting without server-side routing (FastAPI StaticFiles, nginx without try_files, etc.)
- Design E2E tests to navigate via UI interactions from the root path
- Consider adding a catch-all route serving `index.html` for production deployments to support deep linking