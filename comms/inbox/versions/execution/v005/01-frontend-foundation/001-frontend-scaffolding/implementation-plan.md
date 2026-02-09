# Implementation Plan - 001: Frontend Scaffolding

## Overview

Scaffold a React 18+ / TypeScript / Vite frontend project in `gui/`, configure FastAPI to serve the built frontend via `StaticFiles`, and add a `frontend` CI job. This is the foundation for all v005 GUI work.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/` | Create | Entire frontend project directory via `create-vite` |
| `gui/vite.config.ts` | Modify | Add dev proxy, `base: '/gui/'` |
| `gui/tailwind.config.js` | Create | Tailwind CSS configuration |
| `gui/postcss.config.js` | Create | PostCSS configuration for Tailwind |
| `gui/src/index.css` | Modify | Add Tailwind directives |
| `src/stoat_ferret/api/app.py` | Modify | Add `StaticFiles` mount after routers, add `gui_static_path` param to `create_app()` |
| `.github/workflows/ci.yml` | Modify | Add `frontend` job, update path filter with `gui/**` |
| `.gitignore` | Modify | Add `gui/node_modules/`, `gui/dist/` |

## Implementation Stages

### Stage 1: Scaffold Frontend Project

1. Run `npm create vite@latest gui -- --template react-ts` to scaffold the project
2. Install Tailwind CSS: `cd gui && npm install -D tailwindcss @tailwindcss/vite`
3. Configure Tailwind in `vite.config.ts` using the Vite plugin
4. Add Tailwind directives to `gui/src/index.css`
5. Configure `vite.config.ts` with `base: '/gui/'` and dev proxy for `/api/*`, `/health/*`, `/metrics`, `/ws`

**Verification:**
```bash
cd gui && npm run build && ls dist/index.html
cd gui && npx vitest run
```

### Stage 2: FastAPI Static File Serving

1. Add `gui_static_path` parameter to `create_app()` function signature
2. Store on `app.state.gui_static_path`
3. Mount `StaticFiles(directory=gui_static_path, html=True)` at `/gui` after all router registrations
4. Conditionally mount only if the directory exists (skip in tests without built frontend)

**Verification:**
```bash
cd gui && npm run build
uv run pytest tests/ -k "static or gui" -v
```

### Stage 3: CI Pipeline Update

1. Add `gui/**` and `gui/package*.json` to the `changes` path filter
2. Add `frontend` job: ubuntu-latest, Node.js setup, cache `node_modules`, `npm ci`, `npm run build`, `npx vitest run`
3. Add `frontend` to `ci-status` job `needs` list
4. Ensure `frontend` job runs parallel to existing `test` matrix

**Verification:**
```bash
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Test Infrastructure Updates

- Vitest configured via `create-vite` template (includes default smoke test)
- FastAPI static file serving test: verify `/gui/` returns HTML, verify API routes still work after mount

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
```

## Risks

- **R-2 (SPA routing):** `StaticFiles(html=True)` should handle flat routes. If issues arise, implement `SPAStaticFiles` subclass with explicit `index.html` fallback (see `004-research/external-research.md`).
- **R-5 (CI time):** Cache `node_modules/` and keep frontend job parallel. Monitor CI time after merge.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: scaffold React/Vite/TypeScript frontend with FastAPI static serving

- Scaffold gui/ project with create-vite react-ts template
- Configure Tailwind CSS, dev proxy, and base URL
- Mount StaticFiles in FastAPI app after API routers
- Add frontend CI job with node_modules caching

Implements BL-028, BL-003
```