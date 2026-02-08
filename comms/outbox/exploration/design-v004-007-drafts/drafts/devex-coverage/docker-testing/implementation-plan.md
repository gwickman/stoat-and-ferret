# Implementation Plan — docker-testing

## Overview

Create multi-stage Dockerfile and docker-compose.yml for containerized testing environment.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Create | `Dockerfile` | Multi-stage build for test environment |
| Create | `docker-compose.yml` | Service definition for testing |
| Create | `.dockerignore` | Exclude unnecessary files from build context |
| Modify | `README.md` or create `docs/docker-testing.md` | Document Docker-based workflow |

## Implementation Stages

### Stage 1: Dockerfile
Create multi-stage Dockerfile:
- **Stage 1 (builder)**: `python:3.12-slim` base, install `rustup` and Rust toolchain, install `maturin`, build Rust extension.
- **Stage 2 (runtime)**: `python:3.12-slim` base, copy built wheel from Stage 1, install Python dependencies with `uv`, copy source code.

### Stage 2: Docker Compose
Create `docker-compose.yml` with a single `test` service. Mount source code for development iteration. Default command: `uv run pytest`.

### Stage 3: .dockerignore
Exclude `.git`, `__pycache__`, `.venv`, `target/`, `.mypy_cache/`, and other build artifacts from context.

### Stage 4: Documentation
Document the Docker-based testing workflow:
- `docker compose build` to build image
- `docker compose run test` to run tests
- `docker compose run test uv run ruff check .` for linting

## Quality Gates

- Dockerfile builds successfully
- `docker compose run test` passes all tests
- Image size within 2-4 GB range
- Build time acceptable with caching
- Documentation complete

## Risks

| Risk | Mitigation |
|------|------------|
| R7: Docker image complexity | Multi-stage build; cache Rust layer |
| U4: Base image selection | Start with python:3.12-slim + rustup; iterate if needed |
| Large image size from Rust toolchain | Builder stage only; runtime stage excludes toolchain |

## Commit Message

```
feat: add Docker-based testing environment with multi-stage build
```
