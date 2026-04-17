# Multi-stage Dockerfile for containerized testing.
# Builds the Rust extension in a builder stage, then creates a slim
# runtime image with Python dependencies for running the test suite.
#
# Usage:
#   docker compose build
#   docker compose run test

# ---------------------------------------------------------------------------
# Stage 1: Builder — compile the Rust extension with maturin
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH="/usr/local/cargo/bin:$PATH"
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --default-toolchain stable --profile minimal

# Install maturin for building PyO3 wheels
RUN pip install --no-cache-dir maturin>=1.0

# Copy only the Rust source first to maximise layer caching.
WORKDIR /build
COPY rust/ rust/
COPY pyproject.toml .

# Build the wheel (abi3 for any CPython >=3.10)
RUN maturin build --release --manifest-path rust/stoat_ferret_core/Cargo.toml \
    --out /build/wheels

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lightweight test environment
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency metadata first for caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies (without the project itself yet)
RUN uv sync --frozen --no-install-project

# Install the pre-built Rust wheel from the builder stage
COPY --from=builder /build/wheels/*.whl /tmp/wheels/
RUN uv pip install /tmp/wheels/*.whl && rm -rf /tmp/wheels

# Copy the rest of the project source
COPY src/ src/
COPY tests/ tests/
COPY stubs/ stubs/
COPY scripts/ scripts/
COPY alembic/ alembic/
COPY alembic.ini .

# Default: run the test suite
CMD ["uv", "run", "pytest", "-v"]
