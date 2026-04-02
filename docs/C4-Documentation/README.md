# C4 Architecture Documentation

C4 model documentation for stoat-and-ferret, an AI-driven video editor with hybrid Python/Rust architecture.

## Documentation Levels

### Code Level (`Code/`)

Detailed documentation of individual source modules organized by component:

| Directory | Component | Files | Description |
|-----------|-----------|-------|-------------|
| `API-Gateway/` | API Gateway | 29 | FastAPI app, routers (17), middleware, schemas, services, WebSocket |
| `Data-Access/` | Data Access | 12 | SQLite repositories (8), models, schema, audit logging |
| `Effects-Engine/` | Effects Engine | 2 | Effect definitions and registry |
| `FFmpeg-Integration/` | FFmpeg Integration | 5 | FFmpeg executors (sync + async), probe, metrics, observable wrapper |
| `Job-Queue/` | Job Queue | 1 | Async job queue for scan/render/proxy operations |
| `Observability/` | Observability | 1 | Structured logging with file rotation |
| `Render/` | Render Engine | 8 | Render service, executor, queue, models, repository, checkpoints, encoder cache, metrics |
| `Rust-Core/` | Rust Core | 9 | PyO3 bindings, timeline math, filters, layout, composition, preview quality, render support |
| `Web-GUI/` | Web GUI | 13 | React/TypeScript SPA with Zustand stores, preview, theater mode |

### Component Level (`Component/`)

Nine component documents synthesizing code-level details into architectural component descriptions with interfaces, responsibilities, and inter-component relationships.

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
| v027 | 2026-03-30 | Full regeneration for v011-v027 drift (BL-147): preview, proxy, thumbnails, waveform, theater mode, degraded health semantics (LRN-136), metric singleton pattern (LRN-137) |
| v029 | 2026-04-02 | Post-development regeneration for v029: render subsystem (service, executor, queue, models, repository, checkpoints, encoder cache, metrics), 8 render WebSocket events, 3 database tables, render health check, graceful shutdown |
