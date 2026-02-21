# Docker Setup

The project includes a Docker configuration primarily designed for **containerized testing**. It builds the Rust extension and runs the Python test suite in an isolated environment, which is useful for CI-like validation without installing the full toolchain locally.

> **Note:** This Docker setup is for testing, not for production serving. There is no production Docker image or compose configuration at this time.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop on Windows/macOS, or Docker Engine on Linux)
- [Docker Compose](https://docs.docker.com/compose/install/) (included with Docker Desktop; may need separate installation on Linux)

## How It Works

The `Dockerfile` uses a multi-stage build:

1. **Stage 1 (Builder):** Installs the Rust toolchain and maturin in a `python:3.12-slim` image, then builds the Rust extension wheel with `maturin build --release`. The wheel uses the stable ABI (`abi3-py310`), so it works with any CPython 3.10+.

2. **Stage 2 (Runtime):** Starts from a clean `python:3.12-slim` image, installs Python dependencies via `uv sync`, copies the pre-built wheel from Stage 1, and installs it. The project source, tests, stubs, scripts, and alembic config are copied in. The default command runs `uv run pytest -v`.

## Building the Image

```bash
docker compose build
```

This builds the `test` service defined in `docker-compose.yml`. The first build takes several minutes due to Rust compilation; subsequent builds are faster thanks to Docker layer caching.

## Running the Test Suite

```bash
docker compose run test
```

This runs the full pytest suite (`uv run pytest -v`) inside the container. Output is streamed to your terminal.

### Running Specific Tests

Override the default command to run a subset of tests:

```bash
# Run a specific test file
docker compose run test uv run pytest tests/test_api/test_health.py -v

# Run tests matching a pattern
docker compose run test uv run pytest -k "test_clip" -v

# Run only fast tests (skip slow-marked tests)
docker compose run test uv run pytest -m "not slow" -v
```

### Running Other Commands

You can run any command inside the container:

```bash
# Open a shell
docker compose run test bash

# Run linting
docker compose run test uv run ruff check src/ tests/

# Run type checking
docker compose run test uv run mypy src/

# Verify alembic migrations
docker compose run test uv run alembic -x sqlalchemy.url=sqlite:///:memory: upgrade head
```

## Volume Mounts

The `docker-compose.yml` mounts several directories as read-only volumes:

```yaml
volumes:
  - ./src:/app/src:ro
  - ./tests:/app/tests:ro
  - ./stubs:/app/stubs:ro
  - ./scripts:/app/scripts:ro
```

This means you can edit Python source, tests, stubs, or scripts locally and re-run `docker compose run test` without rebuilding the image. Changes are reflected immediately.

However, if you modify any of the following, you **must** rebuild the image:

- `pyproject.toml` or `uv.lock` (Python dependency changes)
- Any Rust source files under `rust/` (requires recompilation)
- `Dockerfile` or `docker-compose.yml` itself
- `alembic/` migration scripts (these are baked into the image, not mounted)

To rebuild:

```bash
docker compose build
```

Or combine build and run:

```bash
docker compose build && docker compose run test
```

## Cleaning Up

```bash
# Remove the test container
docker compose down

# Remove the test container and its image
docker compose down --rmi local

# Remove all stopped containers and unused images (broader cleanup)
docker system prune
```

## Limitations

- The Docker image does **not** include FFmpeg, so tests marked with `@pytest.mark.requires_ffmpeg` will be skipped inside the container.
- The frontend (GUI) is not built or served by the Docker setup.
- The Docker setup uses Python 3.12 only; it does not replicate the full CI matrix across Python 3.10/3.11/3.12 and multiple operating systems.
- Database files created inside the container are ephemeral and lost when the container exits.

## See Also

- [Development Setup](02_development-setup.md) for local development without Docker.
- [Troubleshooting](05_troubleshooting.md) for common build issues.
