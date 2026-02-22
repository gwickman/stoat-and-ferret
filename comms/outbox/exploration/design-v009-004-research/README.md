# Exploration: design-v009-004-research

Research and investigation for v009 version design, covering all 6 backlog items across 2 themes (observability-pipeline, gui-runtime-fixes).

## What Was Produced

All artifacts saved to `comms/outbox/versions/design/v009/004-research/`:

| File | Description |
|------|-------------|
| `README.md` | Research scope, questions, findings summary, recommendations |
| `codebase-patterns.md` | 8 patterns documented with file paths and code snippets |
| `external-research.md` | SPA fallback research via DeepWiki, RotatingFileHandler, WebSocket patterns |
| `evidence-log.md` | Concrete values with sources, 13 learning verifications (all VERIFIED) |
| `impact-analysis.md` | Dependencies, breaking changes (none), test needs, doc updates |
| `persistence-analysis.md` | BL-057 log files and BL-060 audit entries analyzed |

## Key Findings

1. **SPA fallback (BL-063):** `StaticFiles(html=True)` does NOT provide SPA routing. A catch-all route is needed.
2. **All referenced classes verified:** ObservableFFmpegExecutor, AuditLogger, AsyncProjectRepository, ConnectionManager — all exist with expected interfaces.
3. **All 13 learnings VERIFIED** — none stale, all patterns still present in codebase.
4. **No unresolvable unknowns** — all research questions answered with evidence.
5. **No breaking changes** — all v009 changes are additive.
