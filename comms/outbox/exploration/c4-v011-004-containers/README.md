# Task 004: Container Synthesis -- Results

## Containers Identified: 5

| Container | Type | Technology | Runtime |
|-----------|------|------------|---------|
| **API Server** | API / Web Application | Python 3.10+, FastAPI, uvicorn | Single process on port 8000 |
| **Web GUI** | Web Application (SPA) | TypeScript, React 19, Vite 7 | Static files served by API Server (or Vite dev server in dev) |
| **Rust Core Library** | In-process library | Rust, PyO3, maturin | Loaded as Python C extension within API Server process |
| **SQLite Database** | Embedded database | SQLite 3, aiosqlite, Alembic | File at `data/stoat.db`, accessed in-process |
| **File Storage** | Local filesystem | OS filesystem | Directories for videos, thumbnails, database |

Note: The Rust Core Library and SQLite Database are not standalone processes -- they are embedded within the API Server. The Web GUI is pre-built to static files and served by the API Server in production. Only the API Server is a true standalone running process.

## Infrastructure Files Found

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: Stage 1 compiles Rust extension with maturin, Stage 2 creates slim Python 3.12 runtime with uv |
| `docker-compose.yml` | Test service with source volume mounts for iteration |
| `.github/workflows/ci.yml` | 9-matrix test (3 OS x 3 Python), Rust coverage, frontend build+test, Playwright E2E |
| `pyproject.toml` | Python package config, maturin build settings, dev tools (ruff, mypy, pytest) |
| `gui/package.json` | Frontend dependencies and scripts (dev, build, lint, preview) |
| `gui/vite.config.ts` | Vite config with `/gui/` base path, API proxy to localhost:8000 |
| `alembic.ini` | Database migration configuration |

## API Specifications Generated: 1

| File | Format | Endpoints |
|------|--------|-----------|
| `docs/C4-Documentation/apis/api-server-api.yaml` | OpenAPI 3.1.0 | 26 operations across 7 tag groups |

### v011 Delta (changes from v0.8.0 to v0.11.0)

**New endpoints added:**
- `GET /api/v1/filesystem/directories` -- Browse subdirectories with security validation against allowed scan roots
- `POST /api/v1/jobs/{job_id}/cancel` -- Request cancellation of a running job (409 if already terminal)

**Schema changes:**
- `JobStatusResponse.status` enum: added `CANCELLED` value
- New schemas: `DirectoryEntry`, `DirectoryListResponse`
- New error codes: `NOT_A_DIRECTORY`, `PATH_NOT_FOUND`, `ALREADY_TERMINAL`
- Added `JobId` reusable parameter component

## External Systems: 2

| System | Protocol | Required |
|--------|----------|----------|
| **FFmpeg / ffprobe** | subprocess invocation | Yes -- video processing and metadata extraction |
| **Prometheus** | HTTP scrape of `/metrics` endpoint | No -- optional metrics collection |

## Container-Component Mapping

| Container | Components Deployed |
|-----------|-------------------|
| API Server | API Gateway (8 routers incl. filesystem), Effects Engine (9 effects), Application Services (scan, thumbnail, FFmpeg, jobs), Data Access Layer (repos, models, audit, logging), Python Bindings Layer |
| Web GUI | Web GUI (22 components, 8 hooks, 7 stores, 4 pages) |
| Rust Core Library | Rust Core Engine (timeline, clip, FFmpeg, filter graph, expressions, builders, sanitization), Python Bindings Layer (re-exports, stubs) |
| SQLite Database | Data Access Layer (schema, tables, indexes, FTS5 triggers) |
| File Storage | (infrastructure -- no application components) |

## Documents Updated

- `docs/C4-Documentation/c4-container.md` -- Added filesystem browser to API Server description and interfaces, added job cancel endpoint, updated container diagram
- `docs/C4-Documentation/apis/api-server-api.yaml` -- Version bumped to 0.11.0, added filesystem and job cancel endpoints with schemas
