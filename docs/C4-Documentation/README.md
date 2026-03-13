# C4 Architecture Documentation

C4 model documentation for stoat-and-ferret, an AI-driven video editor with hybrid Python/Rust architecture.

## Documentation Levels

### Code Level (`Code/`)

Detailed documentation of individual source modules organized by component:

| Directory | Component | Files | Description |
|-----------|-----------|-------|-------------|
| `API-Gateway/` | API Gateway | 22 | FastAPI app, routers, middleware, schemas, services, WebSocket |
| `Data-Access/` | Data Access | 9 | SQLite repositories, models, schema, audit logging |
| `Effects-Engine/` | Effects Engine | 2 | Effect definitions and registry |
| `FFmpeg-Integration/` | FFmpeg Integration | 4 | FFmpeg executor, probe, metrics, observable wrapper |
| `Job-Queue/` | Job Queue | 1 | Async job queue for scan/render operations |
| `Observability/` | Observability | 1 | Structured logging with file rotation |
| `Rust-Core/` | Rust Core | 8 | PyO3 bindings, timeline math, filters, layout, composition |
| `Web-GUI/` | Web GUI | 11 | React/TypeScript SPA with Zustand stores |

### Component Level (`Component/`)

Eight component documents synthesizing code-level details into architectural component descriptions with interfaces, responsibilities, and inter-component relationships.

### Container Level (`Container/`)

Two documents describing deployment containers, their hosted components, and inter-container interfaces:

| File | Description |
|------|-------------|
| `containers.md` | Container diagram, container descriptions, component mapping, WebSocket events |
| `interfaces.md` | Detailed inter-container interface documentation (REST API, WebSocket, database, FFmpeg) |

See also [docs/ARCHITECTURE.md](../ARCHITECTURE.md) for a high-level architecture overview.

### Context Level (`Context/`)

System context showing the system boundary, personas, capabilities, and external dependencies:

| File | Description |
|------|-------------|
| `system-context.md` | System context diagram, personas, capability summary, external dependencies |

See also [docs/design/02-architecture.md](../design/02-architecture.md) for detailed architecture specification.

## Version History

| Version | Date | Description |
|---------|------|-------------|
| v018 | 2026-03-13 | Full regeneration for v009-v017 drift (BL-069) |
