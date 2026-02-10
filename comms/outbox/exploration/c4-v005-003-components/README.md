# C4 Component Synthesis — Task 003 Results

Synthesized 35 code-level documentation files into 7 logical components. The main boundary decisions were separating the Rust core from its Python binding layer (since they serve different concerns — computation vs. API surface), and distinguishing the API Gateway (HTTP routing) from Application Services (business logic). The package root (`stoat_ferret/`) was grouped with the Data Access Layer since it provides foundational infrastructure (logging, versioning) rather than forming a standalone component.

## Components Identified: 7

1. **Rust Core Engine** (6 code elements) — The Rust crate providing frame-accurate timeline mathematics, clip validation, FFmpeg command building, and input sanitization with PyO3 bindings
2. **Python Bindings Layer** (3 code elements) — Python re-export package, manually maintained type stubs, and CI verification script bridging Rust to Python
3. **API Gateway** (5 code elements) — FastAPI application with REST/WebSocket endpoints, middleware, Pydantic schemas, and configuration
4. **Application Services** (3 code elements) — Business logic for video scanning, thumbnail generation, FFmpeg execution abstraction, and async job queue
5. **Data Access Layer** (2 code elements) — SQLite repository pattern, domain models, FTS5 search, audit logging, and structured logging configuration
6. **Web GUI** (7 code elements) — React SPA with dashboard, video library, project management, custom hooks, Zustand stores, and frontend test suites
7. **Test Infrastructure** (9 code elements) — ~450 Python tests across unit, API, black-box, contract, security, job queue, test double, fallback, and property-based suites

## Code-to-Component Mapping

| Component | Code Files |
|-----------|-----------|
| Rust Core Engine | rust-stoat-ferret-core-src, rust-stoat-ferret-core-timeline, rust-stoat-ferret-core-clip, rust-stoat-ferret-core-ffmpeg, rust-stoat-ferret-core-sanitize, rust-stoat-ferret-core-bin |
| Python Bindings Layer | stoat-ferret-core, stubs-stoat-ferret-core, scripts |
| API Gateway | stoat-ferret-api, stoat-ferret-api-routers, stoat-ferret-api-middleware, stoat-ferret-api-schemas, stoat-ferret-api-websocket |
| Application Services | stoat-ferret-api-services, stoat-ferret-ffmpeg, stoat-ferret-jobs |
| Data Access Layer | stoat-ferret-db, stoat-ferret |
| Web GUI | gui-src, gui-components, gui-hooks, gui-pages, gui-stores, gui-components-tests, gui-hooks-tests |
| Test Infrastructure | tests, tests-test-api, tests-test-blackbox, tests-test-contract, tests-test-coverage, tests-test-jobs, tests-test-doubles, tests-test-security, tests-examples |

All 35 code-level files are assigned. No orphans.

## Boundary Rationale

- **Rust Core Engine vs Python Bindings**: Separated because they serve fundamentally different purposes — the Rust crate is about computation and correctness, while the Python layer is about API surface, type safety for Python consumers, and graceful degradation. They also use different languages and build systems.

- **API Gateway vs Application Services**: The API Gateway handles HTTP/WebSocket concerns (routing, validation, middleware, serialization), while Application Services encapsulate business logic (scanning, FFmpeg execution, job processing). This follows a clean layered architecture where routers delegate to services.

- **Application Services vs Data Access**: Services depend on repository protocols from the Data Access Layer but don't know about SQLite specifics. This inversion of control enables the test infrastructure to substitute in-memory doubles.

- **Data Access Layer includes package root**: The `stoat_ferret` package root (version + logging) is infrastructure consumed by all Python layers. It was grouped with Data Access rather than becoming a 1-element component, as both serve as foundational Python infrastructure.

- **Web GUI includes frontend tests**: GUI component and hook tests are tightly coupled to the frontend code they validate and use the same toolchain (Vitest, testing-library). They belong with the GUI rather than the backend Test Infrastructure.

- **Test Infrastructure as a component**: The Python test suites are extensive (~450 tests), well-organized, and establish reusable patterns (factories, contract testing, recording/replay). They merit component-level documentation.

## Cross-Component Dependencies

Key dependency patterns:

1. **Rust → Python flow**: Rust Core Engine → Python Bindings → consumed by API Gateway, Application Services, and Data Access Layer (for Clip.validate)
2. **API layering**: API Gateway → Application Services → Data Access Layer (strict downward dependencies)
3. **Frontend → Backend**: Web GUI → API Gateway (HTTP/WebSocket only, no direct Python imports)
4. **Test coverage**: Test Infrastructure exercises all backend components through various testing strategies (unit, integration, contract, E2E)
5. **FFmpeg bridge**: Application Services uses both Python FFmpeg execution and Rust-built FFmpegCommand objects, bridged via the integration module

## Delta Changes

N/A — this is the initial `full` mode component synthesis for version v005. No previous component structure exists.
