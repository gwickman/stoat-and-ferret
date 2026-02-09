# Requirements - 001: Frontend Scaffolding

## Goal

Scaffold a React/Vite/TypeScript frontend project in `gui/`, configure FastAPI to serve the built frontend via static files, and update the CI pipeline with a new frontend job.

## Background

No frontend project exists -- no `gui/` directory, `package.json`, or framework choice has been finalized. The design docs (`docs/design/08-gui-architecture.md`) use React patterns throughout (JSX, hooks, Zustand). All v005 GUI milestones (M1.10-M1.12) are blocked until a frontend project is in place. FastAPI must serve the built frontend at `/gui/*` routes for production deployment.

**Backlog Items:** BL-028, BL-003

## Functional Requirements

**FR-001: React project scaffolding**
Scaffold a React 18+ / TypeScript / Vite project in `gui/` directory using `create-vite` with `react-ts` template. Configure Tailwind CSS for styling.
- AC: `gui/` directory contains `package.json`, `tsconfig.json`, `vite.config.ts`, and `src/` with React entry point

**FR-002: Vite build configuration**
Configure Vite with `base: '/gui/'` for sub-path deployment and default `outDir: 'dist'`.
- AC: `npm run build` in `gui/` produces `gui/dist/index.html` and bundled assets

**FR-003: Dev proxy configuration**
Configure Vite dev server proxy to route `/api/*`, `/health/*`, `/metrics`, and `/ws` to FastAPI at `localhost:8000`.
- AC: Running Vite dev server proxies API calls to FastAPI backend with HMR working

**FR-004: FastAPI static file serving**
Mount `StaticFiles(directory="gui/dist", html=True)` at `/gui` in the FastAPI app, after all API routers.
- AC: FastAPI serves `gui/dist/index.html` at `/gui/` and all static assets; API routes still respond correctly

**FR-005: CI pipeline update**
Add a `frontend` job to `.github/workflows/ci.yml` on ubuntu-latest that runs `npm ci`, `npm run build`, and `npx vitest run`. Cache `node_modules/` via `actions/cache`. Add `gui/**` to the path filter.
- AC: CI `frontend` job runs in parallel with existing test matrix and passes

## Non-Functional Requirements

**NFR-001: Build performance**
Vite build completes in under 30 seconds on CI.
- Metric: CI frontend job total time < 2 minutes (including npm install)

**NFR-002: Bundle size**
Initial production bundle under 500KB gzipped (React + minimal dependencies).
- Metric: `gui/dist/` total gzipped size < 500KB

## Out of Scope

- Component library selection (deferred to Theme 03 features)
- State management setup (deferred to Theme 03)
- Actual GUI components beyond the default Vite template
- HTTPS or custom domain configuration

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests | Vitest smoke test (default from `create-vite` template) passes |
| Integration tests | FastAPI serves `gui/dist/index.html` at `/gui/` route; API routes still respond correctly after static mount |
| Contract tests | Vite build produces `gui/dist/index.html` and asset files |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.