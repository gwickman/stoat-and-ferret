# Handoff: 001-frontend-scaffolding

## What Was Done

- React/TypeScript/Vite project scaffolded in `gui/` with Tailwind CSS v4
- FastAPI serves built frontend at `/gui` via `StaticFiles(html=True)`
- CI `frontend` job validates build and tests on every PR

## Key Decisions

- **Separate vitest.config.ts**: Vite 7 + vitest 4 don't support inline `test` config in `vite.config.ts` (TypeScript error). A separate `vitest.config.ts` is used instead.
- **Conditional mount**: `StaticFiles` is only mounted when `gui_static_path` points to an existing directory. This avoids errors in test mode or when the frontend isn't built.
- **Tailwind CSS v4**: Uses the new `@tailwindcss/vite` plugin and `@import "tailwindcss"` syntax (no `tailwind.config.js` needed with v4).

## For Next Feature

- The `gui/src/App.tsx` contains the default Vite template. Replace with actual application components.
- State management (Zustand) and component libraries are deferred to Theme 03.
- The dev proxy is configured for `/api/*`, `/health/*`, `/metrics`, and `/ws` — update if new API prefixes are added.
