# Stoat & Ferret User Manual

Stoat & Ferret is an AI-driven programmatic video editor built on a hybrid Python/Rust architecture. It provides a REST API for video library management, timeline-based clip editing, and an extensible FFmpeg effects system -- all designed for programmatic control by AI agents or developer tooling.

**Version:** 0.3.0 | **License:** MIT | **Python:** >=3.10

## Architecture at a Glance

- **Python (FastAPI)** -- REST API, async job processing, WebSocket events
- **Rust (PyO3)** -- Frame-accurate timeline math, clip validation, FFmpeg filter builders
- **SQLite** -- Persistent storage for videos, projects, clips, and effects
- **FFmpeg** -- Video probing, thumbnail generation, and filter string execution
- **React** -- Web GUI for browsing, editing, and effect configuration

## Manual Contents

| Guide | Description |
|-------|-------------|
| [Getting Started](01_getting-started.md) | Start the server, make your first API call, create a project |
| [API Overview](02_api-overview.md) | Base URL, error format, pagination, endpoint groups |
| [API Reference](03_api-reference.md) | Detailed endpoint documentation with curl examples |
| [Effects Guide](04_effects-guide.md) | Available effects, parameter details, previewing and applying |
| [Timeline Guide](05_timeline-guide.md) | Projects, clips, frame-based editing, video library |
| [GUI Guide](06_gui-guide.md) | Web interface: Dashboard, Library, Projects, Effect Workshop |
| [Rendering Guide](07_rendering-guide.md) | **[Planned]** Export and rendering pipeline |
| [AI Integration](08_ai-integration.md) | AI-driven workflows, OpenAPI schema, effect discovery |
| [Glossary](09_glossary.md) | Definitions of key terms and concepts |

## Quick Links

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`
- **Web GUI:** `http://localhost:8000/gui/`
- **Prometheus Metrics:** `http://localhost:8000/metrics`

## Prerequisites

Before using this manual, ensure you have completed the project setup:

- Python 3.10 or later
- Rust toolchain (for building the `stoat_ferret_core` extension)
- FFmpeg installed and available on PATH
- Dependencies installed via `pip install -e ".[dev]"` and `maturin develop`

See the project README and setup documentation for full installation instructions.
