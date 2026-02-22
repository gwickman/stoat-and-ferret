## Context

FastAPI's `StaticFiles` mount returns 404 for SPA sub-paths like `/gui/library` when users navigate directly or refresh the page. Single-page applications need all non-file paths to serve `index.html` for client-side routing to work.

## Learning

Replace `StaticFiles` mounts with two catch-all FastAPI route handlers: one for the bare path (`/gui`) and one for all sub-paths (`/gui/{path:path}`). The sub-path handler checks if the requested path maps to an actual static file; if so, it serves it via `FileResponse`, otherwise it falls back to `index.html`.

## Evidence

In v009, the SPA routing feature replaced `app.mount("/gui", StaticFiles(...))` with two `@app.get` handlers. This resolved direct navigation and page refresh on all GUI sub-paths while preserving static asset serving. The conditional `gui_dir.is_dir()` guard was maintained to keep the GUI optional.

## Application

When serving a SPA from FastAPI:
1. Remove the `StaticFiles` mount
2. Add `@app.get("/prefix")` to serve `index.html` for the bare path
3. Add `@app.get("/prefix/{path:path}")` that checks `(prefix_dir / path).is_file()` before serving
4. Return `FileResponse(index_html_path)` as fallback for non-file paths
5. Keep the conditional directory guard to make the SPA optional
6. Consider adding cache-control headers for static assets (StaticFiles may have provided these automatically)