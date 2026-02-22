# C4 Architecture Documentation

**Last Updated:** 2026-02-22 UTC
**Generated for Version:** v008
**Generation Mode:** delta
**Generator:** auto-dev-mcp C4 documentation prompt

## Quick Reference

| Level | Document | Description |
|-------|----------|-------------|
| Context | [c4-context.md](./c4-context.md) | System context, personas, user journeys |
| Container | [c4-container.md](./c4-container.md) | Deployment containers, APIs, infrastructure |
| Component | [c4-component.md](./c4-component.md) | Component index and relationships |
| Code | c4-code-*.md | Per-directory code analysis |

## C4 Levels Explained

- **Context** (c4-context.md): Who uses the system and what other systems does it talk to? Start here for orientation.
- **Container** (c4-container.md): What are the running processes, databases, and services? Read this for deployment understanding.
- **Component** (c4-component.md + c4-component-*.md): What are the logical modules inside each container? Read for development context.
- **Code** (c4-code-*.md): What functions and classes exist in each directory? Reference during implementation.

## API Specifications

- [api-server-api.yaml](./apis/api-server-api.yaml) -- OpenAPI 3.1 specification for the REST API

## Contents

### Components

| File | Description |
|------|-------------|
| [c4-component-rust-core-engine.md](./c4-component-rust-core-engine.md) | Frame-accurate timeline math, clip validation, FFmpeg command building, filter graphs, expressions, audio/transition builders, input sanitization |
| [c4-component-python-bindings.md](./c4-component-python-bindings.md) | Python re-export package, type stubs, and stub verification for Rust core |
| [c4-component-effects-engine.md](./c4-component-effects-engine.md) | Effect definition registry with 9 built-in effects, JSON Schema parameters, AI hints, and filter preview |
| [c4-component-api-gateway.md](./c4-component-api-gateway.md) | FastAPI REST/WebSocket endpoints, configurable heartbeat, middleware, schemas, effects CRUD, and transition application |
| [c4-component-application-services.md](./c4-component-application-services.md) | Video scanning, thumbnail generation, FFmpeg execution, async job queue |
| [c4-component-data-access.md](./c4-component-data-access.md) | SQLite repository pattern for Video, Project, Clip; domain models with effects/transitions as JSON; schema; audit logging; structured logging config |
| [c4-component-web-gui.md](./c4-component-web-gui.md) | React SPA with dashboard, video library, project management, effect workshop (apply/edit/remove lifecycle), WCAG AA accessibility, and real-time monitoring |
| [c4-component-test-infrastructure.md](./c4-component-test-infrastructure.md) | Unit, integration, contract, black-box, security, property-based, PyO3 binding parity, startup integration, and orphaned settings test suites |

### Code-Level Documents

| File | Description |
|------|-------------|
| [c4-code-rust-core.md](./c4-code-rust-core.md) | Crate root (lib.rs), PyO3 module registration, custom exceptions, health check |
| [c4-code-rust-ffmpeg.md](./c4-code-rust-ffmpeg.md) | FFmpegCommand builder, Filter, FilterChain, FilterGraph, Expr/PyExpr, DrawtextBuilder, SpeedControl |
| [c4-code-rust-stoat-ferret-core-src.md](./c4-code-rust-stoat-ferret-core-src.md) | Crate root (lib.rs), PyO3 module registration |
| [c4-code-rust-stoat-ferret-core-timeline.md](./c4-code-rust-stoat-ferret-core-timeline.md) | Timeline module: FrameRate, Position, Duration, TimeRange |
| [c4-code-rust-stoat-ferret-core-clip.md](./c4-code-rust-stoat-ferret-core-clip.md) | Clip module: Clip struct, validation |
| [c4-code-rust-stoat-ferret-core-ffmpeg.md](./c4-code-rust-stoat-ferret-core-ffmpeg.md) | FFmpeg module: command builder, filters, audio builders, transition builders |
| [c4-code-rust-stoat-ferret-core-sanitize.md](./c4-code-rust-stoat-ferret-core-sanitize.md) | Sanitize module: input validation, path safety |
| [c4-code-rust-stoat-ferret-core-bin.md](./c4-code-rust-stoat-ferret-core-bin.md) | Stub generator binary |
| [c4-code-stoat-ferret-core.md](./c4-code-stoat-ferret-core.md) | Python bindings package (stoat_ferret_core) |
| [c4-code-stubs-stoat-ferret-core.md](./c4-code-stubs-stoat-ferret-core.md) | Python type stubs for Rust bindings |
| [c4-code-scripts.md](./c4-code-scripts.md) | Scripts (stub verification) |
| [c4-code-python-effects.md](./c4-code-python-effects.md) | Effects module: EffectDefinition, EffectRegistry, 9 built-in effects |
| [c4-code-python-api.md](./c4-code-python-api.md) | Higher-level API layer overview with routers, schemas, services, and WebSocket |
| [c4-code-python-schemas.md](./c4-code-python-schemas.md) | Schema definitions overview with effect and job schemas |
| [c4-code-python-db.md](./c4-code-python-db.md) | SQLAlchemy ORM models, generic BaseRepository, async repositories |
| [c4-code-stoat-ferret-api.md](./c4-code-stoat-ferret-api.md) | API application factory, settings (debug, ws_heartbeat_interval), lifespan with structured logging, entry point |
| [c4-code-stoat-ferret-api-routers.md](./c4-code-stoat-ferret-api-routers.md) | API route handlers (health, videos, projects, jobs, effects with CRUD, ws with configurable heartbeat) |
| [c4-code-stoat-ferret-api-middleware.md](./c4-code-stoat-ferret-api-middleware.md) | API middleware (correlation ID, metrics) |
| [c4-code-stoat-ferret-api-schemas.md](./c4-code-stoat-ferret-api-schemas.md) | API Pydantic request/response schemas |
| [c4-code-stoat-ferret-api-websocket.md](./c4-code-stoat-ferret-api-websocket.md) | WebSocket connection manager, events |
| [c4-code-stoat-ferret-api-services.md](./c4-code-stoat-ferret-api-services.md) | API services (scan, thumbnail, FFmpeg) |
| [c4-code-stoat-ferret-ffmpeg.md](./c4-code-stoat-ferret-ffmpeg.md) | FFmpeg integration (subprocess wrapper) |
| [c4-code-stoat-ferret-jobs.md](./c4-code-stoat-ferret-jobs.md) | Async job queue |
| [c4-code-stoat-ferret-db.md](./c4-code-stoat-ferret-db.md) | Database layer (repositories, models, audit, schema creation on startup) |
| [c4-code-stoat-ferret.md](./c4-code-stoat-ferret.md) | Package root (stoat_ferret) with version metadata and configure_logging() |
| [c4-code-gui-src.md](./c4-code-gui-src.md) | GUI application root, routing |
| [c4-code-gui-components.md](./c4-code-gui-components.md) | GUI React components (22 components) |
| [c4-code-gui-hooks.md](./c4-code-gui-hooks.md) | GUI custom hooks (health, WebSocket, metrics, videos, projects, effects) |
| [c4-code-gui-pages.md](./c4-code-gui-pages.md) | GUI page components (Dashboard, Library, Projects, Effects) |
| [c4-code-gui-stores.md](./c4-code-gui-stores.md) | GUI Zustand stores (activity, library, project, effectCatalog, effectForm, effectPreview, effectStack) |
| [c4-code-gui-components-tests.md](./c4-code-gui-components-tests.md) | GUI component tests (101 tests, 20 files) |
| [c4-code-gui-hooks-tests.md](./c4-code-gui-hooks-tests.md) | GUI hook tests (30 tests, 6 files) |
| [c4-code-gui-e2e.md](./c4-code-gui-e2e.md) | GUI E2E Playwright tests (15 tests) |
| [c4-code-tests.md](./c4-code-tests.md) | Test suite root (~532 tests including startup integration and orphaned settings) |
| [c4-code-tests-test-api.md](./c4-code-tests-test-api.md) | API integration tests |
| [c4-code-tests-test-blackbox.md](./c4-code-tests-test-blackbox.md) | Black-box tests |
| [c4-code-tests-test-contract.md](./c4-code-tests-test-contract.md) | Contract tests |
| [c4-code-tests-test-coverage.md](./c4-code-tests-test-coverage.md) | Coverage / import fallback tests |
| [c4-code-tests-test-jobs.md](./c4-code-tests-test-jobs.md) | Job queue tests |
| [c4-code-tests-test-doubles.md](./c4-code-tests-test-doubles.md) | Test doubles |
| [c4-code-tests-test-security.md](./c4-code-tests-test-security.md) | Security tests |
| [c4-code-tests-examples.md](./c4-code-tests-examples.md) | Example / property-based tests |

## Generation History

| Version | Mode | Date | Notes |
|---------|------|------|-------|
| v005 | full | 2026-02-10 | Complete C4 documentation across all levels. No gaps. |
| v006 | delta | 2026-02-19 | Delta update for effects engine. Added c4-component-effects-engine.md. Updated 6 code-level files, 5 component files, container, context, API spec. Added 6 new code-level files for v006 modules. |
| v007 | delta | 2026-02-19 | Delta update for v007: effect workshop GUI, quality validation, API spec update. Updated component files (web-gui, test-infrastructure, api-gateway), added GUI code-level files (e2e, components-tests, hooks-tests, stores, pages, hooks, components, src), added test code-level files, updated API spec to v0.7.0. 42 code-level files total. |
| v008 | delta | 2026-02-22 | Delta update for v008: application startup wiring, CI stability, structured logging. Updated 6 code-level files (stoat-ferret, stoat-ferret-api, stoat-ferret-api-routers, stoat-ferret-db, gui-e2e, tests), 4 component files (api-gateway, data-access, test-infrastructure, web-gui), component index, container, context, and API spec. No new files added; 42 code-level files total. |

## Regeneration

To regenerate, run the C4 documentation prompt:
- **Full:** Set MODE=full to regenerate everything
- **Delta:** Set MODE=delta to update only changed directories (requires existing C4 docs from a previous full run)
- **Auto:** Set MODE=auto to let the prompt decide (uses delta if possible, falls back to full)
- **Prompt location:** docs/auto-dev/PROMPTS/c4_documentation_prompt/
