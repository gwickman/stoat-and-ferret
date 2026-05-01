# Production Dockerfile for stoat-and-ferret
#
# Multi-stage build: the builder stage compiles the Rust extension and
# frontend assets; the runtime stage is a minimal Python image that
# serves the API with a non-root user and liveness health check.
#
# Usage:
#   docker build -t stoat-ferret .
#   docker run -p 8765:8765 stoat-ferret

# ---------------------------------------------------------------------------
# Stage 1: Builder — compile Rust extension and frontend assets
# ---------------------------------------------------------------------------
FROM python:3.10 AS builder

# Install system build dependencies and Node.js 22 (matches CI)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        pkg-config \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (minimal profile)
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH="/usr/local/cargo/bin:$PATH"
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --default-toolchain stable --profile minimal

# Install maturin for building the PyO3 Rust extension wheel
RUN pip install --no-cache-dir "maturin>=1.0,<2.0"

# Copy project metadata first for maximum layer caching on Rust builds
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY rust/ rust/

# Build the Rust extension wheel from the project root.
# Guardrail: do NOT pass --manifest-path on the CLI; maturin reads it from
# pyproject.toml ([tool.maturin] manifest-path). Running from the project
# root is required per AGENTS.md to avoid conflicting site-packages entries.
RUN maturin build --release --out /wheels

# Copy remaining source for Python dependency sync and frontend build
COPY src/ src/
COPY gui/ gui/

# Build the frontend (Node.js 22 installed above)
WORKDIR /build/gui
RUN npm ci && npm run build

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal production image
# ---------------------------------------------------------------------------
FROM python:3.10-slim AS runtime

# curl is required for the HEALTHCHECK CMD
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary for fast Python dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency metadata and install Python runtime dependencies.
# --no-install-project: do not build/install the project itself (hatchling
#   cannot produce the Rust extension; the wheel is installed separately).
# --no-dev: exclude development-only packages (pytest, mypy, ruff, etc.).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Install the pre-built Rust extension wheel from the builder stage
COPY --from=builder /wheels/*.whl /tmp/wheels/
RUN uv pip install /tmp/wheels/*.whl && rm -rf /tmp/wheels

# Copy application source (stoat_ferret only).
# stoat_ferret_core is provided by the installed wheel — do not copy
# src/stoat_ferret_core to avoid shadowing the compiled extension via PYTHONPATH.
COPY src/stoat_ferret/ src/stoat_ferret/
COPY alembic/ alembic/
COPY alembic.ini ./

# Copy compiled frontend assets from builder
COPY --from=builder /build/gui/dist /app/gui/dist

# Create non-root user (uid 1000) and runtime data directories,
# then transfer ownership of the entire /app tree before switching users
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data/thumbnails \
    && chown -R appuser:appuser /app

EXPOSE 8765

# Liveness probe — server responds if it is running
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8765/health/live || exit 1

USER appuser

# Activate the uv-managed virtual environment and set Python source path
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    STOAT_API_HOST=0.0.0.0 \
    STOAT_DATABASE_PATH=/app/data/stoat.db \
    STOAT_GUI_STATIC_PATH=/app/gui/dist \
    STOAT_THUMBNAIL_DIR=/app/data/thumbnails

CMD ["python", "-m", "stoat_ferret.api"]
