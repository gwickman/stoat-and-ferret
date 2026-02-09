---
status: complete
acceptance_passed: 5
acceptance_total: 5
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 001-frontend-scaffolding

## Summary

Scaffolded a React 18+ / TypeScript / Vite frontend project in `gui/`, configured FastAPI to serve the built frontend via `StaticFiles` at `/gui`, and added a `frontend` CI job. All acceptance criteria are met and all quality gates pass.

## Acceptance Criteria Results

| ID | Criterion | Status |
|----|-----------|--------|
| FR-001 | `gui/` contains `package.json`, `tsconfig.json`, `vite.config.ts`, `src/` with React entry point | Pass |
| FR-002 | `npm run build` produces `gui/dist/index.html` and bundled assets | Pass |
| FR-003 | Vite dev proxy configured for `/api/*`, `/health/*`, `/metrics`, `/ws` | Pass |
| FR-004 | FastAPI serves `gui/dist/index.html` at `/gui/` and static assets; API routes still respond | Pass |
| FR-005 | CI `frontend` job runs in parallel with test matrix and passes | Pass |

## Changes Made

### New Files
- `gui/` - Full React/TypeScript/Vite project scaffolded with `create-vite react-ts`
- `gui/vite.config.ts` - Configured with `base: '/gui/'`, dev proxy, and Tailwind CSS plugin
- `gui/vitest.config.ts` - Vitest configuration with jsdom environment
- `gui/src/App.test.tsx` - Smoke test verifying App component renders
- `gui/src/index.css` - Updated with `@import "tailwindcss"` directive
- `tests/test_api/test_gui_static.py` - 5 integration tests for static file serving

### Modified Files
- `src/stoat_ferret/api/app.py` - Added `gui_static_path` parameter to `create_app()`, mounts `StaticFiles` at `/gui` when directory exists
- `.github/workflows/ci.yml` - Added `gui` path filter, `frontend` job (Node.js 22, npm ci, build, vitest), updated `ci-status` needs
- `.gitignore` - Added `gui/node_modules/` and `gui/dist/`

## Quality Gate Results

| Gate | Result |
|------|--------|
| `ruff check` | Pass |
| `ruff format` | Pass |
| `mypy` | Pass (0 issues in 39 files) |
| `pytest` | Pass (576 passed, 15 skipped, 92.91% coverage) |
| `vitest` | Pass (1 test passed) |

## Build Output

- Bundle size: ~61KB gzipped JS + ~2KB CSS + ~2KB SVG = ~65KB total (well under 500KB limit)
- Build time: 541ms
