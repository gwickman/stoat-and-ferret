# Project Backlog

*Last updated: 2026-02-25 11:26*

**Total completed:** 74 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 0 |
| P1 | High | 0 |
| P2 | Medium | 1 |
| P3 | Low | 0 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-069-ref"></a>[BL-069](#bl-069) | P2 | xl | Update C4 architecture documentation for v009 changes | C4 documentation was last generated for v008. v009 introd... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| architecture | 1 | BL-069 |
| c4 | 1 | BL-069 |
| documentation | 1 | BL-069 |

## Tag Conventions

Use only approved tags when creating or updating backlog items. This reduces fragmentation and improves tag-based filtering.

### Approved Tags

| Tag | Description |
|-----|-------------|
| `process` | Process improvements, workflow changes, governance |
| `tooling` | MCP tools, CLI tooling, development infrastructure |
| `cleanup` | Code cleanup, refactoring, tech debt removal |
| `documentation` | Documentation improvements and maintenance |
| `execution` | Version/feature execution pipeline |
| `feature` | New feature development |
| `knowledge-management` | Learnings, institutional memory, bug tracking |
| `reliability` | System reliability, health checks, resilience, performance |
| `plugins` | Plugin integration and development |
| `testing` | Test infrastructure, test quality, code quality audits |
| `architecture` | Architecture documentation and decisions (incl. C4) |
| `notifications` | Notifications and alerting |
| `skills` | Chatbot skills and hierarchy |
| `integration` | External system integration |
| `research` | Research and investigation tasks |
| `claude-code` | Claude Code CLI-specific concerns |
| `async` | Async patterns and operations |
| `dx` | Developer/operator experience |

### Consolidation Rules

When a tag is not in the approved list, map it to the nearest approved tag:

| Retired Tag | Use Instead |
|-------------|-------------|
| `automation`, `design`, `design-workflow`, `guardrails`, `safety`, `permissions`, `capabilities`, `safeguard`, `chatbot-discipline` | `process` |
| `cli`, `logging`, `infrastructure`, `mcp-tools`, `mcp-protocol`, `bootstrap`, `exploration`, `multi-project` | `tooling` |
| `deprecation`, `refactoring`, `maintenance`, `audit`, `DRY`, `YAGNI` | `cleanup` |
| `setup` | `documentation` |
| `version-execution`, `watchdog`, `containers` | `execution` |
| `enhancement`, `discovery` | `feature` |
| `knowledge-extraction`, `troubleshooting` | `knowledge-management` |
| `health-check`, `dependencies`, `resilience`, `performance` | `reliability` |
| `quality`, `code-quality` | `testing` |
| `c4` | `architecture` |
| `skill` | `skills` |
| `ux` | `dx` |
| `efficiency`, `async-cli` | `async` |

### Version-Specific Tags

Tags like `v070-tech-debt` are acceptable temporarily to group related items from a specific version. Once all items with that tag are completed, the tag naturally expires. Prefer using `cleanup` plus a version reference in the item description over creating new version-specific tags.

## Item Details

### P2: Medium

#### 📋 BL-069: Update C4 architecture documentation for v009 changes

**Status:** open
**Tags:** architecture, c4, documentation

C4 documentation was last generated for v008. v009 introduced 6 features across 2 themes (observability-pipeline, gui-runtime-fixes) that created architecture drift in 5 areas:

1. **configure_logging() now includes RotatingFileHandler**: C4 Data Access component describes logging config as "JSON/console logging setup" but code now includes file-based logging with rotation (log_dir parameter, 10MB rotation, 5 backups). Evidence: src/stoat_ferret/logging.py:18-21,78-80.

2. **Project Repository missing count() method**: C4 Data Access lists Project Repository operations as "add, get, list_projects, update, delete" — missing the new count() method added for pagination. Evidence: src/stoat_ferret/db/project_repository.py:87,190,254.

3. **SPA routing uses catch-all routes, not StaticFiles mount**: C4 API Gateway states "Static File Serving: GUI static files mounted at /gui" but StaticFiles was replaced with @app.get("/gui") and @app.get("/gui/{path:path}") catch-all routes serving files with SPA fallback. Evidence: src/stoat_ferret/api/app.py:206-211.

4. **ObservableFFmpegExecutor and AuditLogger wired into create_app() lifespan**: These were pre-existing dead code documented in v008 C4 but are now actively wired as DI components in the lifespan — ObservableFFmpegExecutor wrapping RealFFmpegExecutor, AuditLogger with separate sync SQLite connection. Evidence: src/stoat_ferret/api/app.py:86-94.

5. **WebSocket broadcasts actively wired**: v008 C4 listed SCAN_STARTED, SCAN_COMPLETED, PROJECT_CREATED event types but broadcast() calls were not wired. v009 added active broadcast calls in scan handler and project creation router. Evidence: src/stoat_ferret/api/services/scan.py:84,94 and src/stoat_ferret/api/routers/projects.py:150.

The version retrospective also notes C4 regeneration was attempted but failed for v009.

**Use Case:** During version planning and onboarding, developers and the design agent consult C4 documentation to understand the current architecture. Stale documentation leads to incorrect assumptions about component capabilities and wiring, causing design decisions based on outdated information.

**Acceptance Criteria:**
- [ ] C4 Data Access component documents configure_logging() file rotation capability with log_dir parameter
- [ ] C4 Data Access component lists count() in Project Repository operations
- [ ] C4 API Gateway component describes SPA catch-all routing pattern instead of StaticFiles mount
- [ ] C4 API Gateway component reflects ObservableFFmpegExecutor and AuditLogger as DI-managed lifespan components
- [ ] C4 container/context docs reflect that WebSocket broadcast events are actively wired (not just defined)

**Notes:** Additional drift from v010:\n\n1. **ffprobe_video() converted to async**: C4 documents it as sync using subprocess. Now uses `async def ffprobe_video()` with `asyncio.create_subprocess_exec()` + 30s timeout + process cleanup. Evidence: src/stoat_ferret/ffmpeg/probe.py:45-83.\n\n2. **AsyncJobQueue Protocol expanded with set_progress() and cancel()**: C4 lists only submit/get_status/get_result. Protocol now includes `set_progress(job_id, value)` and `cancel(job_id)`. Evidence: src/stoat_ferret/jobs/queue.py:102-117.\n\n3. **New CANCELLED job status**: C4 lists PENDING/RUNNING/COMPLETE/FAILED/TIMEOUT. Code now includes CANCELLED. Evidence: src/stoat_ferret/jobs/queue.py:25.\n\n4. **JobResult includes progress field**: C4 lists job_id/status/result/error. Code adds `progress: float | None`. Evidence: src/stoat_ferret/jobs/queue.py:52.\n\n5. **New REST endpoint POST /api/v1/jobs/{id}/cancel**: Returns 200/404/409. Not in C4 container API interfaces. Evidence: src/stoat_ferret/api/routers/jobs.py:51.\n\n6. **scan_directory() expanded with progress_callback and cancel_event kwargs**: C4 shows only path/recursive/repository/thumbnail_service params. Evidence: src/stoat_ferret/api/services/scan.py:121-128.\n\n7. **make_scan_handler() expanded with ws_manager and queue kwargs**: C4 shows only repository and thumbnail_service. Evidence: src/stoat_ferret/api/services/scan.py:57-62.\n\n8. **_check_ffmpeg() converted to async**: C4 lists it as sync. Now uses asyncio.to_thread(subprocess.run). Evidence: src/stoat_ferret/api/routers/health.py:86-97.\n\n9. **AsyncioJobQueue.process_jobs() injects _job_id and _cancel_event into handler payload**: Undocumented dispatch pattern. Evidence: src/stoat_ferret/jobs/queue.py:464-469.\n\n10. **Frontend ScanModal includes cancel button**: C4 GUI component doesn't mention scan cancellation. Evidence: gui/src/components/ScanModal.tsx:58.\n\n11. **C4 context Async Job Processing feature description outdated**: Lists statuses without cancelled, doesn't mention progress or cancellation capabilities.\n\nAdditional count drift from v011 (C4 regenerated but higher-level summaries not updated):\n\n12. **Component count stale at higher C4 levels**: c4-component-web-gui.md and c4-container.md say "22 React components" but there are 24 (DirectoryBrowser and ClipFormModal added in v011). Code-level docs (c4-code-gui-components.md) document both correctly, but component/container-level summary counts were not updated during delta regeneration. Evidence: gui/src/components/ contains 24 .tsx files.\n\n13. **Store count stale at higher C4 levels**: c4-component-web-gui.md and c4-container.md say "7 Zustand stores" but there are 8 (clipStore added in v011). Code-level docs (c4-code-gui-stores.md) document clipStore correctly, but component/container-level summary counts and lists were not updated. Evidence: gui/src/stores/ contains 8 .ts files.\n\n14. **Component name list incomplete in c4-component-web-gui.md**: Line 32 explicitly lists 22 component names, omitting DirectoryBrowser and ClipFormModal.\n\n15. **Store name list incomplete in c4-component-web-gui.md**: Line 35 explicitly lists 7 store names, omitting clipStore.

[↑ Back to list](#bl-069-ref)
