---
status: complete
acceptance_passed: 6
acceptance_total: 6
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-spa-routing

## Summary

Replaced the `StaticFiles` mount at `/gui` with catch-all FastAPI routes that serve static files when they exist and fall back to `index.html` for SPA routing. This fixes direct navigation and page refresh on GUI sub-paths like `/gui/library` and `/gui/projects`.

## Changes Made

### `src/stoat_ferret/api/app.py`
- Removed `StaticFiles` import, replaced with `FileResponse` import
- Replaced `app.mount("/gui", StaticFiles(...))` with two routes:
  - `@app.get("/gui")` — serves `index.html` for bare `/gui` path
  - `@app.get("/gui/{path:path}")` — serves existing files or falls back to `index.html`
- Both routes are conditional on `gui_dir.is_dir()` (same guard as before)

### `tests/test_api/test_spa_routing.py` (new)
- 9 tests covering SPA fallback, static file serving, bare path, conditional activation, and API route preservation

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | SPA fallback for GUI sub-paths | Pass |
| FR-002 | Static file serving | Pass |
| FR-003 | Bare /gui path | Pass |
| FR-004 | Page refresh preservation | Pass |
| FR-005 | Conditional activation | Pass |
| FR-006 | Remove StaticFiles mount | Pass |

## Test Results

- 919 passed, 20 skipped
- Coverage: 92.92% (threshold: 80%)
- All existing tests continue to pass (including `test_gui_static.py`)
