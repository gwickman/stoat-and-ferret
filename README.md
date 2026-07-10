# stoat-and-ferret

[![CI](https://github.com/gwickman/stoat-and-ferret/actions/workflows/ci.yml/badge.svg)](https://github.com/gwickman/stoat-and-ferret/actions/workflows/ci.yml)
[![License: AGPL v3 or later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

stoat-and-ferret is an alpha video editor built specifically to be operated by chatbots and other programmatic agents. Its primary interface is not a timeline widget or a desktop UI; it is a discoverable HTTP API, OpenAPI schema, effect catalogue, schema endpoints, replayable WebSocket event stream, and agent-oriented workflow documentation.

The implementation combines a Python/FastAPI orchestration layer, a Rust/PyO3 media core, a React web GUI, SQLite persistence, and FFmpeg-based media processing. The project is not production-stable yet, but it is well past a prototype: it can scan media, build non-destructive timelines, apply and preview effects, generate proxies and previews, render outputs, run quality-control checks, and expose each step through machine-readable surfaces a chatbot can inspect and drive.

## What It Does

- Index local video files with FFmpeg probing, metadata extraction, thumbnails, waveform data, and optional proxy generation.
- Manage projects, clips, tracks, markers, transitions, project versions, subtitle assets, TTS cues, and delivery profiles.
- Apply a built-in effect registry of 40 FFmpeg-backed effects, including text, speed, fades, transitions, audio repair, mastering, panning, reverb, freeze frame, blur, sharpen, opacity, scale, keying, LUTs, lens effects, generators, zoom/pan, curves, vignette, hue rotation, and subtitles.
- Render projects through a queued render API with status polling, cancellation, retry, frame previews, render evidence, encoder discovery, batch rendering, and WebSocket progress events.
- Run post-render QC checks for loudness, true peak, clipping, silence, loop seams, tone presence, ducking, section arc, A/V sync, decode integrity, and chapters.
- Serve a React GUI with dashboard, library, projects, effects, timeline, preview, and render pages.
- Let a chatbot bootstrap itself from live endpoints: OpenAPI for routes, `/api/v1/effects` for effect semantics, `/api/v1/schema/{resource}` for response shapes, structured errors for self-correction, and `/ws` for progress.

## Chatbot-First Design

The project is designed around a local chatbot operator model: Claude Code, Codex, ChatGPT with local tools, or another agent can run beside the app, inspect the live API, make edits, monitor state, and summarize outcomes. The GUI remains important, but mainly as a human-visible verification surface rather than the only control surface.

The core contract is:

- **Control plane:** REST endpoints under `/api/v1` for videos, projects, clips, effects, timeline, preview, render, QC, assets, versions, and testing fixtures.
- **Discovery plane:** `GET /openapi.json`, `GET /api/v1/effects`, and `GET /api/v1/schema/{resource}` so an agent can learn capabilities from the running server instead of relying on stale hand-written docs.
- **Feedback plane:** WebSocket events on `/ws`, with globally monotonic `event_id` values, heartbeats, and `Last-Event-ID` replay for reconnects.
- **Verification plane:** GUI pages, render evidence, preview sessions, QC reports, frame previews, ffprobe-able outputs, logs, and metrics.
- **Ergonomics layer:** operator guide, prompt recipes, API examples, event vocabulary, and chatbot-driven testing specs that encode canonical workflows and failure handling.

The current design does not require a custom MCP server or other tool wrapper to be useful. A chatbot can start with direct HTTP, OpenAPI, WebSocket events, and small local helper scripts; higher-level wrappers are worth adding only when repeated workflow friction proves they will remove real complexity.

The practical consequence: a new agent can start with three live calls:

```bash
curl http://127.0.0.1:8765/openapi.json
curl http://127.0.0.1:8765/api/v1/effects
curl http://127.0.0.1:8765/api/v1/schema/project
```

From those, it can discover route shapes, effect types, parameter bounds, AI hints, example prompts, filter previews, and resource schemas before it mutates anything.

## Architecture

```text
Clients
  Chatbots, local agents, scripts, Web GUI, curl, other tools
        |
        v
FastAPI service
  Discoverable REST API, WebSocket events, jobs, render queue,
  structured errors, observability
        |
        v
Python services and repositories
  SQLite, audit log, previews, proxies, QC, TTS, assets
        |
        v
Rust core via PyO3
  Timeline math, clip validation, FFmpeg filter builders, QC parsers,
  render planning helpers, sanitization, layout and composition helpers
        |
        v
FFmpeg and local filesystem
  Media probing, previews, renders, waveforms, thumbnails, generated artifacts
```

The main product design choice is non-destructive editing: source media is not modified. Projects store references, frame ranges, timeline placement, effects, and render plans; FFmpeg is invoked to materialize previews and outputs. The main integration design choice is agent discoverability: a chatbot should be able to learn what the system can do, choose valid operations, watch progress, and recover from errors without scraping the UI.

## Requirements

- Python 3.10 or newer
- Rust stable toolchain, including `cargo`, `rustfmt`, and `clippy`
- Node.js 22 or newer for the GUI
- `uv` for Python dependency management
- `maturin` for building the Rust extension
- FFmpeg on `PATH` for real media probing, previews, renders, and QC checks

The API can start in a degraded mode when FFmpeg is unavailable, but real media workflows need FFmpeg.

## Quick Start

```bash
git clone https://github.com/gwickman/stoat-and-ferret.git
cd stoat-and-ferret

uv sync
uv run maturin develop

cd gui
npm ci
npm run build
cd ..

uv run python -m stoat_ferret.api
```

The server defaults to `http://127.0.0.1:8765`.

Useful endpoints:

- Web GUI: `http://127.0.0.1:8765/gui/`
- Swagger UI: `http://127.0.0.1:8765/docs`
- ReDoc: `http://127.0.0.1:8765/redoc`
- OpenAPI JSON: `http://127.0.0.1:8765/openapi.json`
- Liveness: `http://127.0.0.1:8765/health/live`
- Readiness: `http://127.0.0.1:8765/health/ready`
- Metrics: `http://127.0.0.1:8765/metrics/`
- WebSocket events: `ws://127.0.0.1:8765/ws`

For a reloadable backend during development:

```bash
uv run uvicorn stoat_ferret.api.app:create_app --factory --reload
```

Runtime data is written under `data/` by default. The application creates and migrates the local SQLite database on startup.

## First Chatbot-Operable Flow

This is the kind of sequence a chatbot can execute directly after discovering the live API. The agent should usually check `/health/ready`, fetch `/openapi.json`, fetch `/api/v1/effects`, then perform the task-specific calls.

Scan media:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/videos/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/absolute/path/to/videos", "recursive": true}'
```

Wait for the scan job:

```bash
curl "http://127.0.0.1:8765/api/v1/jobs/<job_id>/wait?timeout=30"
```

List indexed videos:

```bash
curl "http://127.0.0.1:8765/api/v1/videos?limit=10"
```

Create a project:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo", "output_width": 1920, "output_height": 1080, "output_fps": 30}'
```

Add a clip using frame-based coordinates:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/projects/<project_id>/clips \
  -H "Content-Type: application/json" \
  -d '{"source_video_id": "<video_id>", "in_point": 0, "out_point": 300, "timeline_position": 0}'
```

Preview an effect without changing the clip:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/effects/preview \
  -H "Content-Type: application/json" \
  -d '{"effect_type": "text_overlay", "parameters": {"text": "Hello", "position": "bottom_center"}}'
```

Start a render:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/render \
  -H "Content-Type: application/json" \
  -d '{"project_id": "<project_id>", "output_format": "mp4", "quality_preset": "standard", "render_plan": "{\"settings\": {}}"}'
```

Poll render status:

```bash
curl http://127.0.0.1:8765/api/v1/render/<render_job_id>
```

For fuller, validated workflows, use `docs/manual/operator-guide.md`, `docs/manual/prompt-recipes.md`, `docs/manual/ai-integration-patterns.md`, and `docs/manual/api-usage-examples.md`.

## GUI

Build the GUI with `npm run build` in `gui/`, then start the FastAPI app and open `/gui/`. For the chatbot-driven workflow, the GUI is the verification plane: it lets a human or browser-driving agent confirm that backend state is visible and usable. The shipped SPA includes:

- Dashboard for health, metrics, and activity.
- Library browsing, search, scan, thumbnails, waveform, and proxy state.
- Project and clip management.
- Effect Workshop with catalog, parameter forms, generated filter previews, and effect stack management.
- Timeline, preview, and render surfaces.

For frontend-only development:

```bash
cd gui
npm run dev
```

Run the backend separately when using the Vite dev server.

## Docker

Build and run the application container:

```bash
docker compose up --build app
```

Or directly:

```bash
docker build -t stoat-ferret .
docker run --rm -p 8765:8765 -v ./data:/app/data stoat-ferret
```

The supplied runtime image starts the API and serves the built GUI, but it does not install FFmpeg. Add FFmpeg in a custom image layer or provide it through your deployment environment if you need real media processing inside the container.

## Development Checks

Backend:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

Rust:

```bash
cd rust/stoat_ferret_core
cargo fmt --check
cargo clippy -- -D warnings
cargo test
```

Frontend:

```bash
cd gui
npx tsc -b
npx vitest run
npm run build
```

FFmpeg-gated tests:

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/ --no-cov --timeout=120 -v
```

OpenAPI and generated TypeScript types must stay in sync after API changes:

```bash
uv run python -m scripts.export_openapi
cd gui
npm run generate:types
```

Chatbot-driven testing is treated as a first-class validation mode. The design docs describe adaptive and larger evidence-producing rounds where a chatbot:

- reads the current API/operator docs,
- plans a test round,
- drives REST and WebSocket flows,
- uses the GUI and media outputs for verification,
- writes evidence packets to disk,
- records doc/runtime inconsistencies,
- and summarizes findings for a human supervisor.

See `docs/design/chatbot-driven-testing/` for the lightweight local design, example workflow, adaptive round, and massive round specs.

## Repository Layout

```text
src/stoat_ferret/              Python application code
src/stoat_ferret/api/          FastAPI app, routers, middleware, settings
src/stoat_ferret/db/           SQLite repositories and schema helpers
src/stoat_ferret/effects/      Effect registry and FFmpeg filter definitions
src/stoat_ferret/ffmpeg/       FFmpeg executors and process integration
src/stoat_ferret/preview/      HLS preview infrastructure
src/stoat_ferret/render/       Render queue, worker, service, checkpoints
src/stoat_ferret_core/         Python package and maintained type stubs for Rust bindings
rust/stoat_ferret_core/        Rust crate exposed through PyO3
gui/                           React, TypeScript, Vite frontend
tests/                         Python test suite, smoke tests, contracts, fixtures
scripts/                       Utility, validation, UAT, and example scripts
alembic/                       Database migrations
docs/                          Manual, setup docs, architecture, legal, operations
```

## Documentation Map

- `docs/setup/00_README.md` - local setup guide.
- `docs/manual/00_README.md` - user and operator manual index.
- `docs/manual/operator-guide.md` - compact HTTP/WebSocket guide for agents and operators.
- `docs/manual/ai-integration-patterns.md` - canonical discovery, schema, execution, batch, reconnect, and preview patterns.
- `docs/manual/08_ai-integration.md` - broader AI integration guide and natural-language-to-API examples.
- `docs/manual/prompt-recipes.md` - copy-paste API sequences for agent workflows.
- `docs/manual/ws-event-vocabulary.md` - WebSocket event envelope and event types.
- `docs/design/chatbot-driven-testing/README.md` - design direction for chatbot-driven local operation and testing.
- `docs/manual/configuration-reference.md` - `STOAT_*` settings and deployment implications.
- `docs/ARCHITECTURE.md` - architecture overview.
- `docs/C4-Documentation/README.md` - generated C4 architecture documentation.
- `docs/CHANGELOG.md` - release history.
- `CONTRIBUTING.md` - contribution policy.
- `NOTICE.md` - license notices and dependency-license findings.

Some deeper manual pages lag the code during active development. When in doubt, treat the live OpenAPI schema, `gui/openapi.json`, and the implementation as authoritative.

## Configuration

Configuration is read from environment variables with the `STOAT_` prefix and from `.env` files. Start from the included example:

```bash
cp .env.example .env
```

Common settings include:

- `STOAT_API_HOST` and `STOAT_API_PORT`
- `STOAT_DATABASE_PATH`
- `STOAT_GUI_STATIC_PATH`
- `STOAT_ALLOWED_SCAN_ROOTS`
- `STOAT_RENDER_MODE`
- `STOAT_RENDER_MAX_CONCURRENT`
- `STOAT_RENDER_OUTPUT_DIR`
- `STOAT_PREVIEW_OUTPUT_DIR`
- `STOAT_PROXY_OUTPUT_DIR`
- `STOAT_ASSETS_DIR`
- `STOAT_SOURCE_URL` and `STOAT_BUILD_COMMIT` for AGPL source-offer metadata

See `docs/manual/configuration-reference.md` and `docs/setup/04_configuration.md` for the full reference.

## Status

This is active alpha software. Expect API and data-model changes, incomplete documentation in some older manual pages, and rough edges around deployment hardening. The project is most suitable today for local experimentation, chatbot-driven testing, automated editing workflows, agent integration experiments, and development of a programmable video-editing backend.

## Contributing

This repository is maintained as a single-maintainer project. External code contributions are not generally accepted. Bug reports and feature requests may be opened as GitHub issues, but responses are not guaranteed. See `CONTRIBUTING.md`.

## License

stoat-and-ferret is licensed under the GNU Affero General Public License v3.0 or later. See `LICENSE` for the full license text.

If you deploy a modified version over a network, review AGPL section 13 obligations. The API includes a source-offer endpoint at `GET /api/v1/source`; configure `STOAT_SOURCE_URL` and `STOAT_BUILD_COMMIT` for your deployment.
