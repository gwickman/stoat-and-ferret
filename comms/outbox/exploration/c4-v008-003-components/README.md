# C4 Component Synthesis — v008 Delta

This is a delta update: the component structure from v007 was preserved with targeted updates to the four components that contain the six changed code-level documentation files. No component boundary changes were needed — all six changed files already resided in well-bounded, semantically correct components. The main decision point was confirming that `c4-code-stoat-ferret.md` (package root with `configure_logging`) correctly belongs in the Data Access Layer rather than as a standalone infrastructure component, which was reaffirmed given its tight coupling to startup wiring.

## Components Identified: 8 (unchanged from v007)

1. **Rust Core Engine** -- Rust/PyO3 compute layer: timeline, clip validation, FFmpeg commands, filters, audio/transition builders, sanitization
2. **Python Bindings Layer** -- Python re-export of Rust types, type stubs, stub verification scripts
3. **Effects Engine** -- 9 built-in effect definitions with JSON Schema, AI hints, and Rust builder delegation
4. **API Gateway** -- FastAPI app factory, all REST/WebSocket endpoints, middleware, schemas, and settings (updated)
5. **Application Services** -- Scan, thumbnail, FFmpeg executor, job queue
6. **Data Access Layer** -- SQLite repositories for Video/Project/Clip, domain models, schema, audit, logging config (updated)
7. **Web GUI** -- React SPA with four views, 7 Zustand stores, 22 components, 15 E2E tests (updated)
8. **Test Infrastructure** -- 9 pytest test suites totaling ~532+ tests (updated)

## Code-to-Component Mapping

| Code-Level File | Component |
|-----------------|-----------|
| c4-code-rust-core | Rust Core Engine |
| c4-code-rust-ffmpeg | Rust Core Engine |
| c4-code-rust-stoat-ferret-core-src | Rust Core Engine |
| c4-code-rust-stoat-ferret-core-timeline | Rust Core Engine |
| c4-code-rust-stoat-ferret-core-clip | Rust Core Engine |
| c4-code-rust-stoat-ferret-core-ffmpeg | Rust Core Engine |
| c4-code-rust-stoat-ferret-core-sanitize | Rust Core Engine |
| c4-code-rust-stoat-ferret-core-bin | Rust Core Engine |
| c4-code-stoat-ferret-core | Python Bindings Layer |
| c4-code-stubs-stoat-ferret-core | Python Bindings Layer |
| c4-code-scripts | Python Bindings Layer |
| c4-code-python-effects | Effects Engine |
| c4-code-stoat-ferret-api | **API Gateway** (updated) |
| c4-code-python-api | API Gateway |
| c4-code-stoat-ferret-api-routers | **API Gateway** (updated) |
| c4-code-stoat-ferret-api-middleware | API Gateway |
| c4-code-stoat-ferret-api-schemas | API Gateway |
| c4-code-python-schemas | API Gateway |
| c4-code-stoat-ferret-api-websocket | API Gateway |
| c4-code-stoat-ferret-api-services | Application Services |
| c4-code-stoat-ferret-ffmpeg | Application Services |
| c4-code-stoat-ferret-jobs | Application Services |
| c4-code-stoat-ferret-db | **Data Access Layer** (updated) |
| c4-code-python-db | Data Access Layer |
| c4-code-stoat-ferret | **Data Access Layer** (updated) |
| c4-code-gui-src | Web GUI |
| c4-code-gui-components | Web GUI |
| c4-code-gui-hooks | Web GUI |
| c4-code-gui-pages | Web GUI |
| c4-code-gui-stores | Web GUI |
| c4-code-gui-components-tests | Web GUI |
| c4-code-gui-hooks-tests | Web GUI |
| c4-code-gui-e2e | **Web GUI** (updated) |
| c4-code-tests | **Test Infrastructure** (updated) |
| c4-code-tests-test-api | Test Infrastructure |
| c4-code-tests-test-blackbox | Test Infrastructure |
| c4-code-tests-test-contract | Test Infrastructure |
| c4-code-tests-test-coverage | Test Infrastructure |
| c4-code-tests-test-jobs | Test Infrastructure |
| c4-code-tests-test-doubles | Test Infrastructure |
| c4-code-tests-test-security | Test Infrastructure |
| c4-code-tests-examples | Test Infrastructure |

## Boundary Rationale

**API Gateway**: Routers, app factory, middleware, schemas, WebSocket manager, and settings all share the single responsibility of HTTP request/response handling and lifecycle management. The `ws_heartbeat_interval` setting now surfaces explicitly in both the settings model and the WebSocket endpoint, keeping all HTTP-facing configuration within this boundary.

**Data Access Layer**: The three repository types (Video, Project, Clip) naturally belong together — they share the same schema, the same aiosqlite dependency, the same protocol pattern, and all serve the same domain persistence concern. The `configure_logging()` function in the package root is infrastructure consumed at startup alongside DB initialization; keeping it here avoids a singleton infrastructure component.

**Web GUI**: The E2E Playwright tests live in `gui/e2e/` and test the GUI as a whole through the browser, making them part of the Web GUI component boundary rather than the Python Test Infrastructure, which tests the backend.

**Test Infrastructure**: Root-level Python test files include three new test modules in v008 (`test_database_startup.py`, `test_logging_startup.py`, `test_orphaned_settings.py`) that verify startup wiring and settings propagation. These belong here because they exercise the Python backend, not the GUI.

## Cross-Component Dependencies

Key dependency patterns (unchanged from v007 in structure, updated in detail):

- **API Gateway -> Data Access Layer**: All three repository types (Video, Project, Clip) are injected into the API Gateway via `create_app()` kwargs
- **API Gateway -> Effects Engine**: EffectRegistry injected for discovery, validation, and filter generation
- **API Gateway -> Application Services**: Scan handler and job queue injected for async video scanning
- **Data Access Layer -> Python Bindings**: `Clip.validate()` calls into Rust `validate_clip()` -- the only cross-layer Rust call from data models
- **Effects Engine -> Python Bindings**: All 9 effect build/preview functions delegate to Rust builders (DrawtextBuilder, SpeedControl, VolumeBuilder, etc.)
- **Web GUI -> API Gateway**: All UI data flows over HTTP REST and WebSocket -- no direct dependency on any backend Python module

## Delta Changes vs v007

| Component | Change Summary |
|-----------|----------------|
| **API Gateway** | Added `ws_heartbeat_interval` and `debug` to Settings; documented heartbeat loop in WebSocket router; added Prometheus effect application counters; documented `configure_logging` call in lifespan |
| **Data Access Layer** | Added `AsyncProjectRepository` and `AsyncClipRepository` protocol/impls/in-memory doubles; added `AuditEntry` dataclass and `AuditLogger`; updated description to reflect logging config wiring into lifespan |
| **Web GUI** | Updated E2E test count from previous to 15 (added 7 effect-workshop tests and 5 accessibility WCAG AA tests); noted keyboard navigation coverage |
| **Test Infrastructure** | Updated root test count from ~495 to ~532; documented 3 new test files (`test_database_startup`, `test_logging_startup`, `test_orphaned_settings`); added audio builder (~42) and transition builder (~46) parity tests |
| **Master Index** | Updated component descriptions to reflect v008 additions throughout |

## Output Files

All component documentation written to `docs/C4-Documentation/`:

- `docs/C4-Documentation/c4-component-api-gateway.md` (updated)
- `docs/C4-Documentation/c4-component-data-access.md` (updated)
- `docs/C4-Documentation/c4-component-web-gui.md` (updated)
- `docs/C4-Documentation/c4-component-test-infrastructure.md` (updated)
- `docs/C4-Documentation/c4-component.md` (updated master index)

Unchanged components (no delta in contained code files):
- `docs/C4-Documentation/c4-component-rust-core-engine.md`
- `docs/C4-Documentation/c4-component-python-bindings.md`
- `docs/C4-Documentation/c4-component-effects-engine.md`
- `docs/C4-Documentation/c4-component-application-services.md`
