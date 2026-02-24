# Development Setup

This guide walks through setting up a local development environment from scratch. Make sure you have all tools listed in [Prerequisites](01_prerequisites.md) installed before starting.

## 1. Clone the Repository

```bash
git clone <repo-url> stoat-and-ferret
cd stoat-and-ferret
```

## 2. Configure Environment

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

The defaults work for local development. See [Configuration](04_configuration.md) for all available settings.

## 3. Install Python Dependencies

Use `uv` to create a virtual environment and install all dependencies (including dev tools like pytest, ruff, mypy, and maturin):

```bash
uv sync
```

This reads `pyproject.toml` and `uv.lock` to install deterministic, reproducible dependencies. The virtual environment is created at `.venv/` in the project root.

## 4. Build the Rust Core Extension

The Rust core (`stoat_ferret_core`) provides filter generation, timeline calculations, FFmpeg command building, and input sanitization. Build it with maturin:

```bash
uv run maturin develop
```

> **IMPORTANT:** This command **must** be run from the project root directory. Do **not** run it from the `rust/` subdirectory or use `--manifest-path`. Running maturin from the wrong location creates a conflicting package in site-packages that causes import errors.

### Verify the Build

```bash
uv run python -c "from stoat_ferret_core import health_check; print(health_check())"
```

This should print a health check message confirming the Rust extension loaded successfully. If you see `RuntimeError: stoat_ferret_core native extension not built`, the maturin build did not complete correctly -- see [Troubleshooting](05_troubleshooting.md).

## 5. Install Frontend Dependencies

The GUI is a React/Vite/Tailwind application in the `gui/` directory:

```bash
cd gui
npm ci
```

`npm ci` performs a clean install from `package-lock.json` for reproducible builds.

### Build the Frontend

```bash
npm run build
```

This runs TypeScript compilation (`tsc -b`) followed by a Vite production build. Output goes to `gui/dist/`, which the FastAPI server serves at `/gui/`.

Return to the project root:

```bash
cd ..
```

## 6. Initialize the Database

The project uses SQLite with Alembic for schema migrations. Initialize the database:

```bash
uv run alembic upgrade head
```

This creates the database file at the default location (`data/stoat.db` when using the application settings, or `stoat_ferret.db` per `alembic.ini`). The `data/` directory may need to be created first:

```bash
mkdir -p data
uv run alembic upgrade head
```

To verify migrations are reversible (as CI does):

```bash
uv run alembic -x sqlalchemy.url=sqlite:///:memory: upgrade head
uv run alembic -x sqlalchemy.url=sqlite:///:memory: downgrade base
uv run alembic -x sqlalchemy.url=sqlite:///:memory: upgrade head
```

## 7. Start the Development Server

```bash
uv run uvicorn stoat_ferret.api.app:create_app --factory --reload
```

The server starts at `http://127.0.0.1:8000` by default. Key endpoints:

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000/api/v1/health/live` | Health check (liveness) |
| `http://127.0.0.1:8000/gui/` | Frontend GUI |
| `http://127.0.0.1:8000/docs` | FastAPI auto-generated API docs (Swagger UI) |
| `http://127.0.0.1:8000/metrics` | Prometheus metrics |
| `ws://127.0.0.1:8000/ws` | WebSocket endpoint |

The `--reload` flag watches for Python file changes and restarts the server automatically. Note that changes to Rust code require re-running `uv run maturin develop` and restarting the server.

### Frontend Development Server

For frontend development with hot module replacement (HMR), use the Vite dev server instead of the production build:

```bash
cd gui
npm run dev
```

This starts Vite's dev server (typically at `http://localhost:5173`). You will need to configure it to proxy API requests to the backend, or run the backend separately.

## 8. Running Tests

### Python Tests

```bash
uv run pytest tests/ -v
```

The test suite includes coverage reporting (minimum 80% required) and several test markers:

```bash
# Run only API tests
uv run pytest tests/ -m api

# Run only property-based tests
uv run pytest tests/ -m property

# Skip slow tests
uv run pytest tests/ -m "not slow"

# Skip tests requiring FFmpeg
uv run pytest tests/ -m "not requires_ffmpeg"
```

### Rust Tests

```bash
cargo test --manifest-path rust/stoat_ferret_core/Cargo.toml
```

### Frontend Tests

```bash
cd gui
npx vitest run
```

### End-to-End Tests

E2E tests use Playwright with Chromium. The full backend and built frontend must be available:

```bash
cd gui
npx playwright install chromium --with-deps
npx playwright test
```

Playwright is configured to start the backend server automatically (see `gui/playwright.config.ts`).

## 9. Code Quality

### Linting

```bash
# Python linting (ruff)
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# Rust linting
cargo fmt --manifest-path rust/stoat_ferret_core/Cargo.toml -- --check
cargo clippy --manifest-path rust/stoat_ferret_core/Cargo.toml -- -D warnings

# Frontend linting (ESLint)
cd gui && npm run lint
```

### Type Checking

```bash
# Python (mypy in strict mode, targeting Python 3.10)
uv run mypy src/

# Frontend (TypeScript compiler)
cd gui && npx tsc -b
```

## Project Structure Overview

```
stoat-and-ferret/
  src/
    stoat_ferret/         # Python application code
      api/                # FastAPI routers, middleware, settings
      db/                 # Database repositories, migrations support
      effects/            # Video effects registry
      ffmpeg/             # FFmpeg executor
      jobs/               # Async job queue
    stoat_ferret_core/    # Python package wrapping Rust extension
  rust/
    stoat_ferret_core/    # Rust source (PyO3 bindings)
  gui/                    # React/Vite/Tailwind frontend
  tests/                  # Python test suite
  stubs/                  # Type stubs for the Rust extension
  alembic/                # Database migration scripts
  scripts/                # Utility scripts
  data/                   # Runtime data (database, thumbnails)
```

## Next Steps

- See [Configuration](04_configuration.md) for environment variables and settings.
- See [Docker Setup](03_docker-setup.md) for containerized testing.
- See [Troubleshooting](05_troubleshooting.md) if you encounter build or runtime issues.
