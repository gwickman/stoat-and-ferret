# C4 Architecture Documentation — stoat-and-ferret

- **Last Updated**: 2026-04-07
- **Generated for Version**: v031
- **Generation Mode**: full
- **Last Source Commit**: 1b13f1e
- **Generator**: auto-dev-mcp C4 documentation prompt

## Quick Reference

| Level | File | Description |
|-------|------|-------------|
| Context | [c4-context.md](./c4-context.md) | System context, personas, user journeys, external dependencies |
| Container | [c4-container.md](./c4-container.md) | Deployment containers, interfaces, infrastructure |
| Component | [c4-component.md](./c4-component.md) | Master index of all components and code-level mappings |
| Code | `c4-code-*.md` (69 files) | Function-level documentation for each code module |
| API Specs | [apis/](./apis/) | OpenAPI specifications |

## C4 Levels Explained

The [C4 model](https://c4model.com/) documents software architecture at four levels of abstraction:

1. **Context** — How the system fits into the world: users, external systems, and high-level relationships.
2. **Container** — The deployment units (applications, databases, file stores) that make up the system and how they communicate.
3. **Component** — The internal building blocks within each container: libraries, services, engines, and their responsibilities.
4. **Code** — Function-level detail: signatures, dependencies, data structures, and implementation notes for each code module.

## API Specifications

| Spec | Format | Description |
|------|--------|-------------|
| [api-server-api.yaml](./apis/api-server-api.yaml) | OpenAPI 3.x | REST API specification for the API Server (78+ endpoints) |

## Contents

### Component Documents (8)

| Component | Description |
|-----------|-------------|
| [API Gateway](./c4-component-api-gateway.md) | FastAPI REST/WebSocket endpoints, middleware, schemas, effects CRUD, transitions, render and preview routing |
| [Application Services](./c4-component-application-services.md) | Video scanning, media generation (thumbnails/waveforms/proxies), FFmpeg execution, job queue, render pipeline, HLS preview system |
| [Data Access Layer](./c4-component-data-access.md) | SQLite repository pattern for Video/Project/Clip/Preview/Proxy; domain models; Alembic migrations; structured logging |
| [Effects Engine](./c4-component-effects-engine.md) | EffectRegistry with 9 built-in effects, JSON Schema validation, AI hints |
| [Python Bindings Layer](./c4-component-python-bindings.md) | Python re-export package and manually maintained type stubs bridging Rust core to Python |
| [Rust Core Engine](./c4-component-rust-core-engine.md) | Frame-accurate timeline math, clip validation, FFmpeg command building, filter graphs, layout, composition, preview, render, sanitization |
| [Test Infrastructure](./c4-component-test-infrastructure.md) | Python test suites: unit, API, smoke, black-box, contract, security, job queue, test doubles, property-based |
| [Web GUI](./c4-component-web-gui.md) | React SPA: 7 pages, 13 Zustand stores, 12 hooks, timeline editor, HLS preview, render management, effect workshop |

### Code-Level Documents (69)

#### Rust Core (13 files)

| Document | Scope |
|----------|-------|
| [c4-code-rust-core.md](./c4-code-rust-core.md) | Crate root, PyO3 module registration, custom exceptions |
| [c4-code-rust-ffmpeg.md](./c4-code-rust-ffmpeg.md) | FFmpegCommand builder, Filter, FilterChain, FilterGraph, Expr, Drawtext, SpeedControl |
| [c4-code-rust-stoat-ferret-core-src.md](./c4-code-rust-stoat-ferret-core-src.md) | Crate root with module declarations and type registration |
| [c4-code-rust-stoat-ferret-core-timeline.md](./c4-code-rust-stoat-ferret-core-timeline.md) | FrameRate, Position, Duration, TimeRange types |
| [c4-code-rust-stoat-ferret-core-clip.md](./c4-code-rust-stoat-ferret-core-clip.md) | Clip struct, ValidationError, validate_clip functions |
| [c4-code-rust-stoat-ferret-core-ffmpeg.md](./c4-code-rust-stoat-ferret-core-ffmpeg.md) | FFmpeg module: audio builders, transition builders |
| [c4-code-rust-stoat-ferret-core-sanitize.md](./c4-code-rust-stoat-ferret-core-sanitize.md) | Input sanitization: escape_filter_text, validate_path, validate_crf/speed/volume/codec/preset |
| [c4-code-rust-stoat-ferret-core-layout.md](./c4-code-rust-stoat-ferret-core-layout.md) | LayoutPosition, LayoutPreset enum (PiP, SideBySide, Grid) |
| [c4-code-rust-stoat-ferret-core-compose.md](./c4-code-rust-stoat-ferret-core-compose.md) | Composition graph builders: sequential, layout, xfade, overlay |
| [c4-code-rust-stoat-ferret-core-preview.md](./c4-code-rust-stoat-ferret-core-preview.md) | Preview optimization: filter simplification, cost estimation, quality selection |
| [c4-code-rust-stoat-ferret-core-render.md](./c4-code-rust-stoat-ferret-core-render.md) | RenderSettings, RenderPlan, hardware encoder detection, progress parsing |
| [c4-code-rust-stoat-ferret-core-benches.md](./c4-code-rust-stoat-ferret-core-benches.md) | Criterion benchmarks for drawtext, speed, audio, transitions |
| [c4-code-rust-stoat-ferret-core-bin.md](./c4-code-rust-stoat-ferret-core-bin.md) | stub_gen binary for Python type stub generation |

#### Python Bindings (2 files)

| Document | Scope |
|----------|-------|
| [c4-code-stoat-ferret-core.md](./c4-code-stoat-ferret-core.md) | Python re-export package for Rust bindings |
| [c4-code-stubs-stoat-ferret-core.md](./c4-code-stubs-stoat-ferret-core.md) | Manually maintained .pyi type stubs |

#### Effects Engine (2 files)

| Document | Scope |
|----------|-------|
| [c4-code-python-effects.md](./c4-code-python-effects.md) | Effects module overview |
| [c4-code-stoat-ferret-effects.md](./c4-code-stoat-ferret-effects.md) | EffectRegistry, 9 built-in effect definitions |

#### API Gateway (7 files)

| Document | Scope |
|----------|-------|
| [c4-code-stoat-ferret-api.md](./c4-code-stoat-ferret-api.md) | FastAPI app factory, settings, entry point |
| [c4-code-python-api.md](./c4-code-python-api.md) | API module overview |
| [c4-code-stoat-ferret-api-routers.md](./c4-code-stoat-ferret-api-routers.md) | 16 REST route modules |
| [c4-code-stoat-ferret-api-middleware.md](./c4-code-stoat-ferret-api-middleware.md) | CorrelationId and Metrics middleware |
| [c4-code-stoat-ferret-api-schemas.md](./c4-code-stoat-ferret-api-schemas.md) | Pydantic request/response schemas |
| [c4-code-python-schemas.md](./c4-code-python-schemas.md) | Schema module overview |
| [c4-code-stoat-ferret-api-websocket.md](./c4-code-stoat-ferret-api-websocket.md) | WebSocket connection manager and events |

#### Application Services (7 files)

| Document | Scope |
|----------|-------|
| [c4-code-stoat-ferret-api-services.md](./c4-code-stoat-ferret-api-services.md) | Scan, media gen, FFmpeg executor, job queue services |
| [c4-code-stoat-ferret-ffmpeg.md](./c4-code-stoat-ferret-ffmpeg.md) | FFmpeg/ffprobe execution wrapper |
| [c4-code-stoat-ferret-jobs.md](./c4-code-stoat-ferret-jobs.md) | AsyncioJobQueue with scan/proxy handlers |
| [c4-code-stoat-ferret-render.md](./c4-code-stoat-ferret-render.md) | Render pipeline: queue, executor, checkpoint manager |
| [c4-code-stoat-ferret-preview.md](./c4-code-stoat-ferret-preview.md) | HLS preview: PreviewManager, HLSGenerator, PreviewCache |
| [c4-code-benchmarks.md](./c4-code-benchmarks.md) | Python benchmark scripts |
| [c4-code-scripts.md](./c4-code-scripts.md) | Dev/build scripts |

#### Data Access Layer (6 files)

| Document | Scope |
|----------|-------|
| [c4-code-stoat-ferret-db.md](./c4-code-stoat-ferret-db.md) | Repository pattern: Video, Project, Clip, Render, Preview, Proxy |
| [c4-code-python-db.md](./c4-code-python-db.md) | Database module overview |
| [c4-code-stoat-ferret-db-new.md](./c4-code-stoat-ferret-db-new.md) | New database types/schemas |
| [c4-code-alembic.md](./c4-code-alembic.md) | Alembic migration config |
| [c4-code-alembic-versions.md](./c4-code-alembic-versions.md) | 7 migration versions |
| [c4-code-stoat-ferret.md](./c4-code-stoat-ferret.md) | Package root, domain models, logging config |

#### Web GUI (21 files)

| Document | Scope |
|----------|-------|
| [c4-code-gui.md](./c4-code-gui.md) | Build config: Vite, Vitest, Playwright, tsconfig |
| [c4-code-gui-src.md](./c4-code-gui-src.md) | App root, 7-route routing, global styles |
| [c4-code-gui-generated.md](./c4-code-gui-generated.md) | Generated OpenAPI types (api-types.ts, types.ts) |
| [c4-code-gui-components.md](./c4-code-gui-components.md) | Main React components: Shell, Navigation, Timeline, Effects, Preview |
| [c4-code-gui-components-library.md](./c4-code-gui-components-library.md) | ProxyStatusBadge component |
| [c4-code-gui-components-render.md](./c4-code-gui-components-render.md) | StatusBadge, RenderJobCard, StartRenderModal |
| [c4-code-gui-components-theater.md](./c4-code-gui-components-theater.md) | TheaterMode with HUD auto-hide, AIActionIndicator |
| [c4-code-gui-hooks.md](./c4-code-gui-hooks.md) | 12 hooks: useHealth, useWebSocket, useMetrics, useDebounce, etc. |
| [c4-code-gui-pages.md](./c4-code-gui-pages.md) | 7 pages: Dashboard, Library, Projects, Effects, Timeline, Preview, Render |
| [c4-code-gui-stores.md](./c4-code-gui-stores.md) | 13 Zustand stores: render, preview, theater, timeline, transition, etc. |
| [c4-code-gui-utils.md](./c4-code-gui-utils.md) | Timeline utilities: timeToPixel, pixelToTime, formatRulerTime |
| [c4-code-gui-src-tests.md](./c4-code-gui-src-tests.md) | MockWebSocket utility for tests |
| [c4-code-gui-components-tests.md](./c4-code-gui-components-tests.md) | 318 component tests across 38 test files |
| [c4-code-gui-components-library-tests.md](./c4-code-gui-components-library-tests.md) | 7 ProxyStatusBadge tests |
| [c4-code-gui-components-render-tests.md](./c4-code-gui-components-render-tests.md) | 48 StatusBadge/RenderJobCard/StartRenderModal tests |
| [c4-code-gui-components-theater-tests.md](./c4-code-gui-components-theater-tests.md) | 26 TheaterMode/HUD tests |
| [c4-code-gui-hooks-tests.md](./c4-code-gui-hooks-tests.md) | 82 hook tests |
| [c4-code-gui-pages-tests.md](./c4-code-gui-pages-tests.md) | 23 page tests (PreviewPage, RenderPage) |
| [c4-code-gui-utils-tests.md](./c4-code-gui-utils-tests.md) | 24 timeline utility tests |
| [c4-code-gui-stores-tests.md](./c4-code-gui-stores-tests.md) | Zustand store tests |
| [c4-code-gui-e2e.md](./c4-code-gui-e2e.md) | 15 Playwright E2E tests |

#### Test Infrastructure (11 files)

| Document | Scope |
|----------|-------|
| [c4-code-tests.md](./c4-code-tests.md) | Test suite overview and conftest |
| [c4-code-tests-test-api.md](./c4-code-tests-test-api.md) | API integration tests |
| [c4-code-tests-smoke.md](./c4-code-tests-smoke.md) | Smoke tests against running server |
| [c4-code-tests-test-blackbox.md](./c4-code-tests-test-blackbox.md) | Black-box API tests |
| [c4-code-tests-test-contract.md](./c4-code-tests-test-contract.md) | Contract tests (DB, schema) |
| [c4-code-tests-unit.md](./c4-code-tests-unit.md) | Unit tests |
| [c4-code-tests-test-security.md](./c4-code-tests-test-security.md) | Security tests |
| [c4-code-tests-test-jobs.md](./c4-code-tests-test-jobs.md) | Job queue tests |
| [c4-code-tests-test-doubles.md](./c4-code-tests-test-doubles.md) | Test doubles and fakes |
| [c4-code-tests-test-coverage.md](./c4-code-tests-test-coverage.md) | Coverage configuration |
| [c4-code-tests-examples.md](./c4-code-tests-examples.md) | Example/fixture tests |

## Generation History

| Version | Mode | Date | Source Commit | Files |
|---------|------|------|---------------|-------|
| v031 | full | 2026-04-07 | 1b13f1e | 82 (1 context + 1 container + 9 component + 69 code + 1 API spec + 1 README) |
| v034 | delta | 2026-04-11 | HEAD | encoder_cache.py gap; post-v031 GUI drift (BL-241) |

## Regeneration Instructions

To regenerate this documentation:

1. **Full regeneration**: Run the auto-dev-mcp C4 documentation prompt with `MODE=full`. This rebuilds all levels from scratch.
2. **Delta regeneration**: Run with `MODE=delta` and the `Last Source Commit` above (`1b13f1e`). This only regenerates files affected by changes since that commit.
3. After generation, review the README for updated stats and commit to the artifacts repository.
