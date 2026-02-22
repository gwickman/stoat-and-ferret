# C4 Component Level: System Overview

## System Components

| Component | Description | Code Elements | Documentation |
|-----------|-------------|---------------|---------------|
| Rust Core Engine | Frame-accurate timeline math, clip validation, FFmpeg command building, filter graphs, expressions, audio builders, transition builders, and input sanitization | 8 files | [c4-component-rust-core-engine.md](./c4-component-rust-core-engine.md) |
| Python Bindings Layer | Python re-export package (including audio/transition builders), type stubs, and stub verification for Rust core | 3 files | [c4-component-python-bindings.md](./c4-component-python-bindings.md) |
| Effects Engine | Effect definition registry with 9 built-in effects, JSON Schema validation, AI hints, and preview functions | 1 file | [c4-component-effects-engine.md](./c4-component-effects-engine.md) |
| API Gateway | FastAPI REST/WebSocket endpoints, configurable heartbeat, middleware, schemas, effects CRUD, and transition application | 7 files | [c4-component-api-gateway.md](./c4-component-api-gateway.md) |
| Application Services | Video scanning, thumbnail generation, FFmpeg execution with Rust command bridge, async job queue | 3 files | [c4-component-application-services.md](./c4-component-application-services.md) |
| Data Access Layer | SQLite repository pattern for Video, Project, Clip; domain models with effects/transitions as JSON; schema; audit logging; structured logging config | 3 files | [c4-component-data-access.md](./c4-component-data-access.md) |
| Web GUI | React SPA with dashboard, video library, project management, effect workshop (apply/edit/remove lifecycle), WCAG AA accessibility, and real-time monitoring | 8 files | [c4-component-web-gui.md](./c4-component-web-gui.md) |
| Test Infrastructure | Unit, integration, contract, black-box, security, property-based, PyO3 binding parity, audio/transition builder parity, startup integration, and orphaned settings test suites | 9 files | [c4-component-test-infrastructure.md](./c4-component-test-infrastructure.md) |

## Component Relationships

```mermaid
C4Component
    title System Component Overview — stoat-and-ferret

    Container_Boundary(system, "stoat-and-ferret Video Editor") {
        Component(gui, "Web GUI", "React/TypeScript", "Dashboard, library, projects, effect workshop, WCAG AA E2E tests")
        Component(api, "API Gateway", "Python/FastAPI", "REST/WebSocket endpoints, configurable heartbeat, effects CRUD, transitions")
        Component(effects, "Effects Engine", "Python", "9 built-in effects, JSON Schema validation, AI hints")
        Component(services, "Application Services", "Python", "Scan, thumbnail, FFmpeg, job queue")
        Component(data, "Data Access Layer", "Python/SQLite", "Repositories for Video/Project/Clip, models, audit, logging config")
        Component(bindings, "Python Bindings", "Python", "Re-exports, type stubs, verification")
        Component(rust, "Rust Core Engine", "Rust/PyO3", "Timeline, validation, commands, filters, audio, transitions, sanitization")
        Component(tests, "Test Infrastructure", "Python/pytest", "~532 Python tests across 9 suites including startup and orphaned settings")
    }

    Rel(gui, api, "HTTP/REST + WebSocket")
    Rel(api, effects, "list/apply/update/remove effects")
    Rel(api, services, "delegates business logic")
    Rel(api, data, "reads/writes via repos")
    Rel(api, bindings, "clip validation, transitions")
    Rel(effects, bindings, "Rust builders for all 9 effects")
    Rel(services, data, "persists scanned data")
    Rel(services, bindings, "FFmpegCommand bridge")
    Rel(data, bindings, "Clip.validate()")
    Rel(bindings, rust, "imports compiled _core module")
    Rel(tests, api, "tests via TestClient")
    Rel(tests, services, "tests directly")
    Rel(tests, data, "contract tests")
    Rel(tests, bindings, "binding parity verification")
```

## Component-to-Code Mapping

| Code-Level File | Component |
|-----------------|-----------|
| `c4-code-rust-core` | Rust Core Engine |
| `c4-code-rust-ffmpeg` | Rust Core Engine |
| `c4-code-rust-stoat-ferret-core-src` | Rust Core Engine |
| `c4-code-rust-stoat-ferret-core-timeline` | Rust Core Engine |
| `c4-code-rust-stoat-ferret-core-clip` | Rust Core Engine |
| `c4-code-rust-stoat-ferret-core-ffmpeg` | Rust Core Engine |
| `c4-code-rust-stoat-ferret-core-sanitize` | Rust Core Engine |
| `c4-code-rust-stoat-ferret-core-bin` | Rust Core Engine |
| `c4-code-stoat-ferret-core` | Python Bindings Layer |
| `c4-code-stubs-stoat-ferret-core` | Python Bindings Layer |
| `c4-code-scripts` | Python Bindings Layer |
| `c4-code-python-effects` | Effects Engine |
| `c4-code-stoat-ferret-api` | API Gateway |
| `c4-code-python-api` | API Gateway |
| `c4-code-stoat-ferret-api-routers` | API Gateway |
| `c4-code-stoat-ferret-api-middleware` | API Gateway |
| `c4-code-stoat-ferret-api-schemas` | API Gateway |
| `c4-code-python-schemas` | API Gateway |
| `c4-code-stoat-ferret-api-websocket` | API Gateway |
| `c4-code-stoat-ferret-api-services` | Application Services |
| `c4-code-stoat-ferret-ffmpeg` | Application Services |
| `c4-code-stoat-ferret-jobs` | Application Services |
| `c4-code-stoat-ferret-db` | Data Access Layer |
| `c4-code-python-db` | Data Access Layer |
| `c4-code-stoat-ferret` | Data Access Layer |
| `c4-code-gui-src` | Web GUI |
| `c4-code-gui-components` | Web GUI |
| `c4-code-gui-hooks` | Web GUI |
| `c4-code-gui-pages` | Web GUI |
| `c4-code-gui-stores` | Web GUI |
| `c4-code-gui-components-tests` | Web GUI |
| `c4-code-gui-hooks-tests` | Web GUI |
| `c4-code-gui-e2e` | Web GUI |
| `c4-code-tests` | Test Infrastructure |
| `c4-code-tests-test-api` | Test Infrastructure |
| `c4-code-tests-test-blackbox` | Test Infrastructure |
| `c4-code-tests-test-contract` | Test Infrastructure |
| `c4-code-tests-test-coverage` | Test Infrastructure |
| `c4-code-tests-test-jobs` | Test Infrastructure |
| `c4-code-tests-test-doubles` | Test Infrastructure |
| `c4-code-tests-test-security` | Test Infrastructure |
| `c4-code-tests-examples` | Test Infrastructure |
