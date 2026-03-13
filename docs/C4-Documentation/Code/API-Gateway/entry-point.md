# Entry Point and Server Launch

**Source:** `src/stoat_ferret/api/__main__.py`
**Component:** API Gateway

## Purpose

Entry point for running the API server via `python -m stoat_ferret.api`. Initializes settings, creates the FastAPI application, and starts the uvicorn ASGI server with graceful shutdown support.

## Public Interface

### Functions

- `main() -> None`: Reads settings via `get_settings()`, creates the FastAPI app via `create_app()`, and starts uvicorn with host/port from settings. Supports graceful shutdown via Ctrl+C.

## Key Implementation Details

- **Settings-driven configuration**: API host and port are read from `Settings.api_host` and `Settings.api_port` (defaults: 127.0.0.1:8765)
- **Log level**: uvicorn log level is set from `Settings.log_level` (lowercased for uvicorn format)
- **No custom uvicorn options**: Uses minimal uvicorn.run() invocation without additional workers or reload settings

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.app.create_app`: Application factory
- `stoat_ferret.api.settings.get_settings`: Settings retrieval

### External Dependencies

- `uvicorn`: ASGI server
