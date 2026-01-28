# FastAPI App Setup

## Goal
Create FastAPI application with uvicorn, lifespan management, and graceful shutdown.

## Requirements

### FR-001: Application Factory
Create `src/stoat_ferret/api/app.py` with:
- `create_app()` function returning FastAPI instance
- Lifespan context manager for resource management
- API version prefix `/api/v1`

### FR-002: Lifespan Management
Lifespan must:
- Open database connection on startup
- Close database connection on shutdown
- Store connection in `app.state.db`

### FR-003: Entry Point
Create `src/stoat_ferret/api/__main__.py`:
- Run uvicorn with configurable host/port
- Enable graceful shutdown

### FR-004: Dependencies
Add to pyproject.toml:
- `fastapi>=0.109`
- `uvicorn[standard]>=0.27`
- `httpx>=0.26` (dev - for TestClient)

### FR-005: Test Directory Structure
Create `tests/test_api/` directory with:
- `__init__.py`
- `conftest.py` (shared API test fixtures)

## Acceptance Criteria
- [ ] `create_app()` returns configured FastAPI instance
- [ ] Database connection managed via lifespan
- [ ] `python -m stoat_ferret.api` starts server
- [ ] Ctrl+C triggers graceful shutdown
- [ ] `tests/test_api/conftest.py` exists with shared fixtures