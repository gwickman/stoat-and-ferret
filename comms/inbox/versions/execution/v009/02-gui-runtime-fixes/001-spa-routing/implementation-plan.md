# Implementation Plan: spa-routing

## Overview

Replace the `StaticFiles` mount at `/gui` with catch-all routes that serve both static files and SPA fallback. The handler checks if the requested path maps to a real file in `gui/dist/` — if yes, serve the file; if no, serve `index.html`. Routes are conditional on `gui_dir.is_dir()`.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/stoat_ferret/api/app.py` | Modify | Remove StaticFiles mount, add catch-all SPA routes conditional on gui_dir |
| `tests/test_api/test_spa_routing.py` | Create | Tests for SPA fallback, static file serving, bare /gui path, conditional activation |

## Test Files

`tests/test_api/test_spa_routing.py`

## Implementation Stages

### Stage 1: Replace StaticFiles with catch-all routes

1. Remove `app.mount("/gui", StaticFiles(directory=gui_dir, html=True), name="gui")`
2. Add `@app.get("/gui/{path:path}")` route after API routers:
   - If `gui_dir / path` is an existing file → return `FileResponse(gui_dir / path)`
   - Otherwise → return `FileResponse(gui_dir / "index.html")`
3. Add `@app.get("/gui")` route for bare `/gui` path → return `FileResponse(gui_dir / "index.html")`
4. Both routes are conditional on `gui_dir.is_dir()` (same guard as existing StaticFiles mount)
5. Remove `StaticFiles` import if no longer used

**Verification:**
```bash
uv run mypy src/
uv run pytest tests/test_api/ -x
```

### Stage 2: Add tests

1. Create a temporary `gui/dist/` directory with `index.html` and a test static file for test fixtures
2. Test `/gui/library` returns 200 with index.html content
3. Test `/gui/projects` returns 200 with index.html content
4. Test `/gui/any-sub-path` returns SPA content
5. Test `/gui/assets/test.js` (existing file) returns the test file content
6. Test `/gui` bare path returns index.html
7. Test that without `gui/dist/`, no `/gui/*` routes exist (404)

**Verification:**
```bash
uv run pytest tests/test_api/test_spa_routing.py -x
```

## Test Infrastructure Updates

- Tests need a temporary directory structure mimicking `gui/dist/` with `index.html` and a sample asset file
- Use `tmp_path` fixture and pass `gui_static_path` kwarg to `create_app()`

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Route must serve correct content-type for static assets — `FileResponse` handles this via file extension. See `006-critical-thinking/risk-assessment.md`.
- Path traversal safety — `FileResponse` with path validation ensures no directory escape.

## Commit Message

```
feat(gui): add SPA routing fallback for GUI sub-paths

BL-063: Replace StaticFiles mount with catch-all routes that serve static
files when they exist and fall back to index.html for SPA routing. Routes
are conditional on gui/dist/ directory existing.
```