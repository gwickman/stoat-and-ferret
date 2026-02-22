# Architecture Overview

stoat-and-ferret is an AI-driven video editor built on a **hybrid Python/Rust architecture**. Python (FastAPI) provides the HTTP API layer for AI discoverability and orchestration, while Rust delivers high-performance compute cores for video processing operations via PyO3 bindings. A React/TypeScript SPA provides the web GUI.

## High-Level Components

```
┌─────────────────────────────────────────────────────────┐
│                      Clients                             │
│   AI Agent (Claude)  |  Web GUI (React)  |  CLI / API   │
└──────────────────────────┬──────────────────────────────┘
                           │
                   REST API + WebSocket
                           │
┌──────────────────────────┴──────────────────────────────┐
│              Python API Layer (FastAPI)                   │
│  Routes: /videos, /projects, /clips, /effects, /render,  │
│          /preview, /ws, /gui, /health, /metrics           │
│  Middleware: Correlation ID, Metrics, Error Handling       │
│  Effects: EffectRegistry with 9 built-in effects          │
│  Jobs: Async job queue (scan, render)                     │
└──────────────────────────┬──────────────────────────────┘
                           │
                      PyO3 Bindings
                           │
┌──────────────────────────┴──────────────────────────────┐
│             Rust Core (stoat_ferret_core)                 │
│  Timeline math  |  Filter/expression builders             │
│  Drawtext, speed, audio, transition builders              │
│  Input sanitization  |  Layout engine                     │
│  Hardware detection  |  Render coordination               │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│                  Processing & Storage                     │
│  FFmpeg subprocess  |  SQLite + FTS5  |  Project JSON     │
│  Audit log  |  Structured logging  |  Prometheus metrics  │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React, TypeScript, Vite, Zustand | Web GUI with real-time updates |
| API | FastAPI, Pydantic, structlog | REST API, validation, observability |
| Compute | Rust, PyO3, pyo3-stub-gen | High-performance filter/timeline math |
| Processing | FFmpeg, FFprobe | Video encoding, metadata extraction |
| Storage | SQLite (FTS5), JSON files | Video library, project persistence |
| Testing | pytest, cargo test, Vitest, Playwright | Multi-language test suites |

## Key Architectural Decisions

- **Non-destructive editing**: Source media files are never modified. All edits are stored as project metadata and applied at render time.
- **Rust for compute, Python for orchestration**: CPU-intensive operations (filter generation, timeline math, input sanitization) run in Rust for performance and safety. Python handles HTTP routing, database access, and subprocess management.
- **PyO3 bindings**: Rust types are exposed to Python via PyO3 with type stubs maintained in `stubs/`. CI enforces stub completeness.
- **Dependency injection**: Services use constructor injection via `app.state`, enabling testing with fakes and making dependencies explicit.
- **Transparency**: API responses include generated FFmpeg filter strings so users and AI agents can inspect what will be executed.
- **AI discoverability**: FastAPI auto-generates OpenAPI schemas. Effect definitions include AI hints and parameter schemas for agent integration.

## Further Reading

| Document | Description |
|----------|-------------|
| [docs/design/02-architecture.md](design/02-architecture.md) | Detailed architecture specification with data models and flows |
| [docs/design/05-api-specification.md](design/05-api-specification.md) | REST API design |
| [docs/design/07-quality-architecture.md](design/07-quality-architecture.md) | Quality attributes and implementation patterns |
| [docs/C4-Documentation/](C4-Documentation/README.md) | Generated C4 documentation (context, container, component, code levels) |
| [AGENTS.md](../AGENTS.md) | Developer guide with commands, standards, and workflows |
