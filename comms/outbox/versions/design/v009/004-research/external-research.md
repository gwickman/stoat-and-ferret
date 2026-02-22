# External Research — v009

## 1. SPA Fallback Routing in Starlette/FastAPI

### Question
Does `StaticFiles(html=True)` provide full SPA fallback routing for sub-paths?

### Finding: No
**Source:** DeepWiki — `encode/starlette` repository

`StaticFiles(html=True)` provides:
- Serving `index.html` for directory requests (e.g., `/gui/` serves `gui/dist/index.html`)
- Serving `404.html` for missing files (if present)
- Redirect for directory URLs without trailing slashes

It does **NOT** serve `index.html` for arbitrary non-existent paths like `/gui/library`. These return 404.

### Recommended Approach

Add a catch-all route before the StaticFiles mount that serves `index.html` for any `/gui/{path}` that doesn't match a static file:

```python
from starlette.responses import HTMLResponse

async def serve_spa(request):
    with open("gui/dist/index.html", "r") as f:
        content = f.read()
    return HTMLResponse(content)
```

For FastAPI specifically, add a route like:
```python
@app.get("/gui/{path:path}")
async def spa_fallback(path: str):
    return HTMLResponse(index_html_content)
```

This must be registered AFTER all API routes but the route must take priority over the StaticFiles mount for non-file paths. Alternatively, a custom middleware or a subclass of StaticFiles could handle this.

### Key Constraint
The SPA fallback must coexist with the conditional static mount (LRN-020) — only activate when `gui/dist/` exists and contains `index.html`.

## 2. RotatingFileHandler (stdlib)

### Question
What are the correct parameters for `logging.handlers.RotatingFileHandler`?

### Finding
**Source:** Python stdlib documentation (well-known API)

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    filename="logs/stoat-ferret.log",
    maxBytes=10 * 1024 * 1024,  # 10MB per AC
    backupCount=5,              # configurable
    encoding="utf-8",
)
```

No external dependencies required — part of Python stdlib `logging.handlers`.

## 3. WebSocket Broadcast Patterns in FastAPI

### Question
Best practice for injecting WebSocket manager into route handlers?

### Finding
The project already has the infrastructure in place:
- `ConnectionManager` stored on `app.state.ws_manager`
- `build_event()` utility for constructing event payloads
- Event types defined as enum

The standard pattern is to access via `request.app.state.ws_manager` from within route handlers, which is already the pattern used in the WebSocket endpoint itself (`routers/ws.py:38`).

No external research needed — the project's existing patterns are sufficient.
