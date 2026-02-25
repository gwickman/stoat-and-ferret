# Project Backlog

*Last updated: 2026-02-25 11:42*

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

**Notes:** Additional drift from v012:\n\n16. **11 PyO3 bindings removed but still listed in C4 docs**: v012 Theme 01 removed `find_gaps`, `merge_ranges`, `total_coverage`, `validate_crf`, `validate_speed` (Python-facing wrappers), `PyExpr`, `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge`, and `execute_command` + `CommandExecutionError`. These are still listed as Python-facing API in c4-container.md (lines 158-163), c4-code-rust-core.md, c4-code-stoat-ferret-core.md, c4-code-stubs-stoat-ferret-core.md, c4-code-rust-ffmpeg.md, c4-code-rust-stoat-ferret-core-ffmpeg.md, c4-code-rust-stoat-ferret-core-timeline.md, c4-code-rust-stoat-ferret-core-sanitize.md, c4-code-stoat-ferret-ffmpeg.md, and c4-component-application-services.md. Note: the Rust-internal functions still exist; only the PyO3 wrappers were removed. Evidence: PRs #113, #114, #115.\n\n17. **integration.py deleted but still documented**: `src/stoat_ferret/ffmpeg/integration.py` (containing `execute_command` bridge function) was deleted. Still referenced in c4-code-stoat-ferret-ffmpeg.md (lines 27, 31, 86, 90). Evidence: file no longer exists.\n\n18. **test_integration.py deleted but still documented**: `tests/test_integration.py` was deleted. Still referenced in c4-code-tests.md (line 34). Evidence: file no longer exists.\n\n19. **Component count now 25, store count now 9**: v012 Theme 02 added TransitionPanel component and transitionStore. Previous drift (notes 12-15) recorded 24 components and 8 stores; now 25 components (gui/src/components/ has 25 .tsx files) and 9 stores (gui/src/stores/ has 9 .ts files). c4-component-web-gui.md still says \"22 React components\" and \"7 Zustand stores\".\n\n20. **TransitionPanel and transitionStore not in C4 GUI docs**: New files gui/src/components/TransitionPanel.tsx and gui/src/stores/transitionStore.ts are not documented in c4-component-web-gui.md or c4-code-gui-components.md/c4-code-gui-stores.md. Evidence: PR #116.\n\n21. **ClipSelector pair-mode extension undocumented**: ClipSelector now supports optional pair-mode props (pairMode, selectedFromId, selectedToId, onSelectPair) for transition clip selection. C4 docs describe only single-select mode. Evidence: gui/src/components/ClipSelector.tsx, PR #116.

[↑ Back to list](#bl-069-ref)
