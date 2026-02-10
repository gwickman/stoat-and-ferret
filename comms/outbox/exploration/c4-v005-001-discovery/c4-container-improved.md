---
title: "C4 Container Level — System Deployment"
---

# C4 Container Level: System Deployment

## Container Diagram

```mermaid
C4Container
title Container Diagram — stoat-and-ferret Video Editor

Person(user, "Editor User", "Uses the video editor in a web browser")

System_Boundary(app, "stoat-and-ferret (single-host deployment)") {

  Container(gui, "Web GUI (SPA)", "TypeScript / React / Vite",
    "Dashboard, video library, project & clip management")

  Container(api, "API Server", "Python / FastAPI / Uvicorn",
    "REST + WebSocket API, serves SPA assets, runs background jobs")

  ContainerDb(db, "SQLite Database (embedded)", "SQLite / aiosqlite",
    "Videos, projects, clips, audit log, FTS5 index")

  Container(store, "Local File Storage", "Filesystem",
    "Source videos, thumbnails, database file")

  %% This is not a running process/container, but an in-process native extension.
  Container(core, "Rust Core (in-process)", "Rust / PyO3",
    "Timeline math, clip validation, safe FFmpeg command building, sanitization")
}

System_Ext(ffmpeg, "FFmpeg / ffprobe", "Video processing & metadata extraction")
System_Ext(prom, "Prometheus (optional)", "Metrics scraping and storage")

Rel(user, gui, "Uses", "HTTPS")
Rel(gui, api, "Calls API", "HTTP/JSON + WebSocket")
Rel(api, db, "Reads/Writes", "SQL (aiosqlite)")
Rel(api, store, "Reads/Writes", "File I/O")
Rel(api, core, "Invokes", "Python ↔ native extension (PyO3)")
Rel(api, ffmpeg, "Executes", "Subprocess")
Rel(prom, api, "Scrapes /metrics", "HTTP")

%% Optional styling hints (supported by many Mermaid renderers)
UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")

UpdateElementStyle(app, $borderColor="#4b5563", $fontColor="#111827")
UpdateElementStyle(api, $bgColor="#eef2ff", $borderColor="#6366f1")
UpdateElementStyle(gui, $bgColor="#ecfeff", $borderColor="#06b6d4")
UpdateElementStyle(core, $bgColor="#fff7ed", $borderColor="#f97316")
UpdateElementStyle(db,  $bgColor="#f0fdf4", $borderColor="#22c55e")
UpdateElementStyle(store, $bgColor="#f8fafc", $borderColor="#94a3b8")
UpdateElementStyle(ffmpeg, $bgColor="#fef2f2", $borderColor="#ef4444")
UpdateElementStyle(prom, $bgColor="#fdf4ff", $borderColor="#d946ef")
```

## Containers

### API Server
- **Name**: API Server  
- **Description**: Hosts REST endpoints, WebSocket events, background jobs, and serves the built SPA as static files. Single running process.  
- **Type**: API / Web Application  
- **Tech**: Python 3.10+, FastAPI, Uvicorn, Starlette, Pydantic, asyncio  
- **Deployment**: `python -m stoat_ferret.api` (Uvicorn on port 8000). Dockerfile available for containerized testing.

**Responsibilities**
- REST API under `/api/v1/` (videos, projects, clips, jobs)
- WebSocket events at `/ws`
- Health endpoints: `/health/live`, `/health/ready`
- Prometheus metrics at `/metrics`
- Serves GUI at `/gui`
- Runs in-process async jobs (e.g., directory scanning)

**Dependencies**
- SQLite (embedded) via aiosqlite
- Local File Storage for videos/thumbnails/db file
- Rust Core (PyO3 native extension)
- FFmpeg/ffprobe subprocess calls
- Prometheus (optional) scrapes `/metrics`

---

### Web GUI (SPA)
- **Name**: Web GUI (SPA)  
- **Description**: React SPA built with Vite, served by API Server; dev mode via Vite dev server with proxy.  
- **Type**: Web Application  
- **Tech**: TypeScript, React, Vite, Tailwind, Zustand, React Router  
- **Deployment**: Built to `gui/dist/` and served at `/gui`.

**Dependencies**
- API Server (REST + WebSocket + health + metrics)

---

### Rust Core (in-process)
- **Name**: Rust Core (in-process)  
- **Description**: Native extension loaded by the API Server at import time; not a separate runtime process.  
- **Type**: Library (native extension)  
- **Tech**: Rust, PyO3, maturin  
- **Deployment**: Built via `maturin develop` (dev) or `maturin build --release` (packaged wheel).

**Responsibilities**
- Timeline math, clip validation
- Safe FFmpeg command construction
- Input sanitization to mitigate command injection risk

---

### SQLite Database (embedded)
- **Name**: SQLite Database (embedded)  
- **Description**: File-based embedded DB accessed in-process by API Server.  
- **Type**: Database (embedded)  
- **Tech**: SQLite, aiosqlite, Alembic migrations  
- **Deployment**: Default `data/stoat.db` (configurable).

---

### Local File Storage
- **Name**: Local File Storage  
- **Description**: Filesystem directories for source videos, thumbnails, and DB file.  
- **Type**: Storage  
- **Deployment**: `data/` plus configured scan roots.

---

## External Systems
- **FFmpeg / ffprobe**: Host-installed binaries executed by API Server for processing and metadata extraction.
- **Prometheus (optional)**: Scrapes `/metrics` from API Server.

---

## Container–Component Mapping

| Container | Components |
|---|---|
| API Server | API Gateway, Application Services, Data Access Layer, Python Bindings Layer |
| Web GUI (SPA) | Web GUI |
| Rust Core (in-process) | Rust Core Engine |
| SQLite Database (embedded) | Data Access Layer (schema portion) |
| Local File Storage | Infrastructure only |

---

## Why this version is better

- **Diagram matches reality more closely**: “Rust Core” is explicitly represented as *in-process* (a native extension), avoiding the common misunderstanding that it is a separately deployed service.
- **Clearer system boundary**: The boundary is labeled as a *single-host deployment*, aligning with SQLite + local filesystem constraints and making “what runs where” obvious.
- **More scannable relationships**: Relationship verbs are consistent (“Uses”, “Calls API”, “Reads/Writes”, “Executes”) and each relationship includes protocol/transport.
- **Visual hierarchy and emphasis**: Styling differentiates primary runtime vs. storage vs. external tools, improving readability in docs and reviews.
- **Lower cognitive load**: Container names include short qualifiers (“(SPA)”, “(embedded)”, “(in-process)”) so deployment semantics are clear without hunting through prose.
