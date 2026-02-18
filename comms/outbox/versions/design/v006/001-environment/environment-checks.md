# Environment Checks — v006 Design

## 1. MCP Health Check

```
success: true
status: healthy
version: 6.0.0
uptime_seconds: 2407
```

### Services
| Service | Status |
|---------|--------|
| config | ok |
| state | ok |
| execution | ok |

### External Dependencies
| Dependency | Available | Details |
|------------|-----------|---------|
| git | yes | C:\Program Files\Git\cmd\git.EXE |
| gh | yes | Authenticated, C:\Program Files\GitHub CLI\gh.EXE |

### Security
- Tool key authorization: enabled
- Active keys: 2
- Orphaned keys: 0
- Enforcement: active

### Source Sync
- Status: **out of sync**
- File: `services/version_execution.py`
- Impact: Non-blocking for design tasks. Only affects version execution operations.

## 2. Project Configuration

```
project: stoat-and-ferret
path: C:/Users/grant/Documents/projects/stoat-and-ferret
active_theme: null
completed_themes: 17
destructive_test_target: false
timeout_minutes: 180
execution_backend_mode: legacy
```

Description: AI-driven video editor with hybrid Python/Rust architecture. FastAPI REST API, Rust core (stoat_ferret_core) via PyO3.

No active themes or in-progress execution — project is idle and ready for new version design.

## 3. Git Status

```
branch: main
tracking: origin/main
ahead: 0
behind: 0
is_clean: false
```

### Modified Files
| File | Reason |
|------|--------|
| comms/state/explorations/design-v006-001-env-1771448598849.json | MCP exploration state tracking (expected) |

No staged or untracked files. The single modified file is the MCP's own exploration state — this is expected during exploration execution and does not indicate uncommitted user work.

## 4. C4 Architecture Documentation

- **Location:** `docs/C4-Documentation/`
- **Last Updated:** 2026-02-10 UTC
- **Generated for:** v005
- **Mode:** full (no gaps)

### Available Documents
| Level | File | Status |
|-------|------|--------|
| Context | c4-context.md | Present |
| Container | c4-container.md | Present |
| Component | c4-component.md + 7 component files | Present |
| Code | 26 code-level files | Present |
| API | api-server-api.yaml (OpenAPI 3.1 v0.3.0) | Present |

### Relevance to v006
The C4 docs cover the existing Rust core engine (timeline, clip, FFmpeg modules) and API gateway. v006 will add new Rust modules (filter expression engine, graph validation) and new API endpoints (effect discovery). The existing FFmpeg command builder documentation (`c4-code-rust-stoat-ferret-core-ffmpeg.md`) will be the primary integration point for new filter builders.

## Summary

| Check | Result | Notes |
|-------|--------|-------|
| MCP Server | PASS | Healthy, all services ok |
| Project Config | PASS | Idle, ready for design |
| Git Status | PASS | On main, synced, no user changes |
| C4 Docs | PASS | Full coverage through v005 |
| **Overall** | **READY** | No blockers for v006 design |
