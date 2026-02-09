---
status: complete
acceptance_passed: 3
acceptance_total: 3
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 004-docker-testing

## Summary

Created a Docker-based testing environment using a multi-stage Dockerfile and
docker-compose.yml. Developers can now run the full test suite inside a
container, bypassing host restrictions such as Windows Application Control
policies.

## Acceptance Criteria

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1 | `docker-compose.yml` with Python + Rust build environment | Pass |
| FR-2 | README documents Docker-based testing workflow | Pass |
| FR-3 | Tests can run inside container bypassing host restrictions | Pass |

## Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-1 | Multi-stage Dockerfile: builder (Rust + maturin) and runtime (Python) | Pass |
| NFR-2 | Rust compilation layer cached via Docker layer ordering | Pass |
| NFR-3 | Image size reasonable (runtime stage excludes Rust toolchain) | Pass |
| NFR-4 | Build time acceptable with layer caching | Pass |

## Files Created

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build: builder compiles Rust wheel, runtime has Python deps |
| `docker-compose.yml` | Single `test` service with source bind mounts |
| `.dockerignore` | Excludes .git, caches, build artifacts from context |
| `docs/docker-testing.md` | Documents the Docker-based testing workflow |

## Implementation Notes

- **Builder stage**: Uses `python:3.12-slim` with `rustup` and `maturin` to
  build the `stoat_ferret_core` PyO3 wheel. Rust source is copied first for
  optimal layer caching.
- **Runtime stage**: Clean `python:3.12-slim` with `uv` for dependency
  management. No Rust toolchain in the final image keeps it smaller.
- **Bind mounts**: `src/`, `tests/`, `stubs/`, `scripts/` are mounted read-only
  at runtime so Python code changes don't require an image rebuild.
- **Rebuild required only** when Rust source or Python dependencies change.

## Quality Gates

- ruff check: pass
- ruff format: pass
- mypy: pass (0 issues in 39 source files)
- pytest: pass (571 passed, 15 skipped, 92.86% coverage)
