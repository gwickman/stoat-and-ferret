# Docker-Based Testing

Run the full test suite inside a container to bypass host restrictions
(e.g. Windows Application Control policies) and get a consistent Linux
environment.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with Compose v2)

## Quick Start

```bash
# Build the test image (first run downloads Rust toolchain — ~2-5 min)
docker compose build

# Run the test suite
docker compose run test
```

## Common Commands

```bash
# Run a specific test
docker compose run test uv run pytest -k "test_health"

# Run with verbose output
docker compose run test uv run pytest -v --tb=short

# Lint
docker compose run test uv run ruff check src/ tests/

# Format check
docker compose run test uv run ruff format --check src/ tests/

# Type check
docker compose run test uv run mypy src/
```

## How It Works

The `Dockerfile` uses a multi-stage build:

1. **Builder stage** — installs the Rust toolchain and `maturin`, compiles the
   `stoat_ferret_core` PyO3 extension into a wheel.
2. **Runtime stage** — starts from a clean `python:3.12-slim`, installs Python
   dependencies with `uv`, and copies the pre-built wheel. No Rust toolchain in
   the final image.

Source directories (`src/`, `tests/`, `stubs/`, `scripts/`) are bind-mounted at
runtime so you can edit code on the host and re-run tests without rebuilding.

## When to Rebuild

Rebuild the image (`docker compose build`) when:

- Rust source code in `rust/` changes
- Python dependencies in `pyproject.toml` or `uv.lock` change

You do **not** need to rebuild for changes to Python source or tests — the
bind mounts handle that automatically.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails downloading Rust | Check network/proxy settings |
| `maturin build` fails | Ensure `pyproject.toml` and `rust/` are in sync |
| Tests pass locally but fail in container | Check for OS-specific path handling |
| Slow builds | Subsequent builds use Docker layer cache for Rust compilation |
