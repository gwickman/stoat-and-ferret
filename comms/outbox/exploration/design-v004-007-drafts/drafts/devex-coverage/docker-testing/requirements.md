# Requirements — docker-testing

## Goal

Create Dockerfile and docker-compose.yml for containerized testing.

## Background

v002 retrospective identified that Windows Application Control policies can block local Python testing. A Docker-based option bypasses these restrictions and provides consistent dev environments. R7 assessed multi-stage Docker builds as acceptable complexity. U4: start with `python:3.12-slim` + `rustup`.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | `docker-compose.yml` with Python + Rust build environment | BL-014 |
| FR-2 | README documents Docker-based testing workflow | BL-014 |
| FR-3 | Tests can run inside container bypassing host restrictions | BL-014 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Multi-stage Dockerfile: Stage 1 builds Rust + maturin, Stage 2 is Python runtime |
| NFR-2 | Rust compilation layer cached for rebuild speed |
| NFR-3 | Image size reasonable (target 2-4 GB) |
| NFR-4 | Build time acceptable (target 2-5 minutes with cache) |

## Out of Scope

- Production Docker image — this is for testing only
- Docker-based CI (separate from GitHub Actions)
- Docker Compose services for databases or external dependencies
- Kubernetes deployment

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Integration | docker-compose up runs test suite successfully | 1 (manual) |
| (none) | Docker configuration, not test code | — |
