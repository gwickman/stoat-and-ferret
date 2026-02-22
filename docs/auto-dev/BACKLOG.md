# Project Backlog

*Last updated: 2026-02-22 10:24*

**Total completed:** 53 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 0 |
| P1 | High | 2 |
| P2 | Medium | 5 |
| P3 | Low | 4 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-059-ref"></a>[BL-059](#bl-059) | P1 | l | Wire ObservableFFmpegExecutor into dependency injection | **Current state:** `ObservableFFmpegExecutor` exists with... |
| <a id="bl-063-ref"></a>[BL-063](#bl-063) | P1 | l | Add SPA routing fallback for GUI sub-paths | **Current state:** FastAPI serves the GUI via `StaticFile... |
| <a id="bl-057-ref"></a>[BL-057](#bl-057) | P2 | l | Add file-based logging with rotation to logs/ directory | **Current state:** After BL-056, structured logging will ... |
| <a id="bl-060-ref"></a>[BL-060](#bl-060) | P2 | l | Wire AuditLogger into repository dependency injection | **Current state:** `AuditLogger` class exists and reposit... |
| <a id="bl-061-ref"></a>[BL-061](#bl-061) | P2 | l | Wire or remove execute_command() Rust-Python FFmpeg bridge | **Current state:** `execute_command()` was built in v002/... |
| <a id="bl-064-ref"></a>[BL-064](#bl-064) | P2 | l | Fix projects endpoint pagination total count | **Current state:** `GET /api/v1/projects` returns `total=... |
| <a id="bl-065-ref"></a>[BL-065](#bl-065) | P2 | l | Wire WebSocket broadcast calls into API operations | **Current state:** The backend defines WebSocket event ty... |
| <a id="bl-019-ref"></a>[BL-019](#bl-019) | P3 | m | Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore | Add Windows bash null redirect guidance to AGENTS.md and ... |
| <a id="bl-066-ref"></a>[BL-066](#bl-066) | P3 | l | Add transition support to Effect Workshop GUI | **Current state:** `POST /projects/{id}/effects/transitio... |
| <a id="bl-067-ref"></a>[BL-067](#bl-067) | P3 | l | Audit and trim unused PyO3 bindings from v001 (TimeRange ops, input sanitization) | **Current state:** Several Rust functions are exposed via... |
| <a id="bl-068-ref"></a>[BL-068](#bl-068) | P3 | l | Audit and trim unused PyO3 bindings from v006 filter engine | **Current state:** Three v006 filter engine features (Exp... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| wiring-gap | 7 | BL-059, BL-060, BL-061, BL-063, ... |
| observability | 3 | BL-057, BL-059, BL-060 |
| rust-python | 3 | BL-061, BL-067, BL-068 |
| gui | 3 | BL-063, BL-065, BL-066 |
| ffmpeg | 2 | BL-059, BL-061 |
| dead-code | 2 | BL-067, BL-068 |
| api-surface | 2 | BL-067, BL-068 |
| windows | 1 | BL-019 |
| agents-md | 1 | BL-019 |
| gitignore | 1 | BL-019 |
| logging | 1 | BL-057 |
| database | 1 | BL-060 |
| routing | 1 | BL-063 |
| api | 1 | BL-064 |
| pagination | 1 | BL-064 |
| websocket | 1 | BL-065 |
| effects | 1 | BL-066 |
| transitions | 1 | BL-066 |

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

### P1: High

#### 📋 BL-059: Wire ObservableFFmpegExecutor into dependency injection

**Status:** open
**Tags:** wiring-gap, observability, ffmpeg

**Current state:** `ObservableFFmpegExecutor` exists with full metrics and structured logging instrumentation, but is never instantiated. The application uses the base executor directly, bypassing all observability.

**Gap:** Created in v002/04-ffmpeg-integration but never wired into the dependency injection chain. The metrics and logging decorators are dead code.

**Impact:** No visibility into FFmpeg execution — no duration metrics, no structured logs for render operations, no correlation ID tracking for debugging failed renders.

**Acceptance Criteria:**
- [ ] ObservableFFmpegExecutor is instantiated and injected as the FFmpeg executor during startup
- [ ] FFmpeg operations emit structlog calls with duration, command preview, and correlation ID
- [ ] Prometheus metrics for FFmpeg execution count and duration are populated after render operations
- [ ] Recording test double remains available for test injection

[↑ Back to list](#bl-059-ref)

#### 📋 BL-063: Add SPA routing fallback for GUI sub-paths

**Status:** open
**Tags:** wiring-gap, gui, routing

**Current state:** FastAPI serves the GUI via `StaticFiles(html=True)`, but this does not fall back to `index.html` for unknown sub-paths. Navigating directly to `/gui/library` or refreshing on `/gui/projects` returns 404. React Router handles client-side navigation fine, but only when starting from the root.

**Gap:** Standard SPA routing fallback was not implemented in v005/01-frontend-foundation. The e2e test suite explicitly works around this by navigating via tab clicks only.

**Impact:** Bookmarks, page refreshes, and shared URLs to any GUI sub-page are broken.

**Acceptance Criteria:**
- [ ] Direct navigation to /gui/library, /gui/projects, and other GUI sub-paths returns the SPA index.html instead of 404
- [ ] Page refresh on any GUI sub-path preserves the current view
- [ ] Bookmarked and shared GUI URLs load the correct page

[↑ Back to list](#bl-063-ref)

### P2: Medium

#### 📋 BL-057: Add file-based logging with rotation to logs/ directory

**Status:** open
**Tags:** observability, logging

**Current state:** After BL-056, structured logging will be wired up but outputs to stdout only. There is no persistent log output — when the process stops, all log history is lost.

**Gap:** No file-based logging exists. Debugging issues after the fact requires the developer to have been watching stdout at the time. There's no way to review historical log output.

**Impact:** Post-hoc debugging is impossible without log persistence. Auto-dev execution pipeline output is lost when sessions end.

**Acceptance Criteria:**
- [ ] configure_logging() adds a RotatingFileHandler writing to logs/ directory at project root
- [ ] Log files rotate at 10MB with a configurable backup count
- [ ] logs/ directory is created automatically on startup if it doesn't exist
- [ ] logs/ is added to .gitignore
- [ ] File handler uses the same structlog formatter and log level as the stdout handler
- [ ] Stdout logging continues to work alongside file logging

**Notes:** Depends on BL-056 (wire up stdout logging first). Use RotatingFileHandler with maxBytes=10MB. Log directory: {project_root}/logs/. Must add logs/ to .gitignore.

[↑ Back to list](#bl-057-ref)

#### 📋 BL-060: Wire AuditLogger into repository dependency injection

**Status:** open
**Tags:** wiring-gap, observability, database

**Current state:** `AuditLogger` class exists and repository constructors accept it as a parameter, but it's never instantiated — the parameter is always None. No audit trail is produced for any database operation.

**Gap:** Created in v002/03-database-foundation but never wired into the DI chain.

**Impact:** No audit trail for data mutations. Debugging "what changed and when" requires manual database inspection.

**Acceptance Criteria:**
- [ ] AuditLogger is instantiated and injected into repositories that accept it
- [ ] Database mutations (create, update, delete) produce audit log entries
- [ ] Audit entries include correlation ID, resource type, and operation type

[↑ Back to list](#bl-060-ref)

#### 📋 BL-061: Wire or remove execute_command() Rust-Python FFmpeg bridge

**Status:** open
**Tags:** wiring-gap, ffmpeg, rust-python

**Current state:** `execute_command()` was built in v002/04-ffmpeg-integration as the bridge between the Rust command builder and the Python FFmpeg executor. It has zero callers in production code.

**Gap:** The function exists and is tested in isolation but is never used in any render or export workflow.

**Impact:** The Rust-to-Python FFmpeg pipeline has no integration point. Either the bridge needs wiring into a real workflow, or it's dead code that should be removed to reduce maintenance burden.

**Acceptance Criteria:**
- [ ] execute_command() is called by at least one render/export code path connecting Rust command builder output to Python FFmpeg executor
- [ ] Render workflow produces a working output file via the Rust→Python bridge
- [ ] If execute_command() is genuinely unnecessary, it is removed along with its tests

[↑ Back to list](#bl-061-ref)

#### 📋 BL-064: Fix projects endpoint pagination total count

**Status:** open
**Tags:** wiring-gap, api, pagination

**Current state:** `GET /api/v1/projects` returns `total=len(projects)` which equals the current page size, not the true database total. A `count()` method was added to `AsyncVideoRepository` but not to `AsyncProjectRepository`.

**Gap:** Pagination total count implementation was incomplete in v005/02-backend-services — only one of two repositories received the method.

**Impact:** Frontend pagination metadata is incorrect when there are more projects than the page limit. Users see wrong page counts and may not discover all their projects.

**Acceptance Criteria:**
- [ ] AsyncProjectRepository has a count() method matching AsyncVideoRepository's implementation
- [ ] GET /api/v1/projects returns correct total count reflecting all projects in the database, not just the current page
- [ ] Frontend pagination displays correct page count when projects exceed the page limit

[↑ Back to list](#bl-064-ref)

#### 📋 BL-065: Wire WebSocket broadcast calls into API operations

**Status:** open
**Tags:** wiring-gap, websocket, gui

**Current state:** The backend defines WebSocket event types (SCAN_STARTED, SCAN_COMPLETED, PROJECT_CREATED, HEALTH_STATUS) and the frontend ActivityLog listens for them, but no API operation ever calls `ConnectionManager.broadcast()`. The only messages sent are heartbeat pings.

**Gap:** WebSocket infrastructure was built in v005 across 02-backend-services and 03-gui-components, but the broadcast calls were never added to the API operations that should trigger them.

**Impact:** The Dashboard ActivityLog renders correctly but only ever shows heartbeat entries. Real-time feedback for scan progress, project creation, and other operations is non-functional.

**Acceptance Criteria:**
- [ ] Library scan operations trigger SCAN_STARTED and SCAN_COMPLETED WebSocket broadcasts
- [ ] Project creation triggers PROJECT_CREATED WebSocket broadcast
- [ ] Dashboard ActivityLog displays real application events, not just heartbeat pings
- [ ] WebSocket event payloads include relevant context (project ID, scan path, etc.)

[↑ Back to list](#bl-065-ref)

### P3: Low

#### 📋 BL-019: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore

**Status:** open
**Tags:** windows, agents-md, gitignore

Add Windows bash null redirect guidance to AGENTS.md and add `nul` to .gitignore. In bash contexts on Windows: Always use `/dev/null` for output redirection (Git Bash correctly translates this to the Windows null device). Never use bare `nul` which gets interpreted as a literal filename in MSYS/Git Bash environments. Correct: `command > /dev/null 2>&1`. Wrong: `command > nul 2>&1`.

**Use Case:** This feature addresses: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore. It improves the system by resolving the described requirement.

**Notes:** The .gitignore half is already done (nul added to .gitignore). Remaining scope: add Windows bash /dev/null redirect guidance to AGENTS.md.

[↑ Back to list](#bl-019-ref)

#### 📋 BL-066: Add transition support to Effect Workshop GUI

**Status:** open
**Tags:** wiring-gap, gui, effects, transitions

**Current state:** `POST /projects/{id}/effects/transition` endpoint is implemented and functional, but the Effect Workshop GUI only handles per-clip effects. There is no GUI surface for the transition API.

**Gap:** The transition API was built in v007/02-effect-registry-api but the Effect Workshop GUI in v007/03 was scoped to per-clip effects only.

**Impact:** Transitions are only accessible via direct API calls. Users have no way to discover or apply transitions through the GUI.

**Acceptance Criteria:**
- [ ] Effect Workshop GUI includes a transition section or mode for applying transitions between clips
- [ ] GUI calls POST /projects/{id}/effects/transition endpoint
- [ ] User can preview and apply at least one transition type through the GUI

[↑ Back to list](#bl-066-ref)

#### 📋 BL-067: Audit and trim unused PyO3 bindings from v001 (TimeRange ops, input sanitization)

**Status:** open
**Tags:** dead-code, rust-python, api-surface

**Current state:** Several Rust functions are exposed via PyO3 but have zero production callers in Python. TimeRange list operations (find_gaps, merge_ranges, total_coverage) are design-ahead code for future timeline editing. Input sanitization functions (validate_crf, validate_speed) overlap with internal Rust validation in FFmpegCommand.build().

**Gap:** Functions were exposed "just in case" in v001 without a consuming code path. They're tested but unused.

**Impact:** Inflated public API surface increases maintenance burden and PyO3 binding complexity. Unclear to consumers which functions are intended for use vs aspirational.

**Acceptance Criteria:**
- [ ] TimeRange list operations (find_gaps, merge_ranges, total_coverage) are either used by a production code path or removed from PyO3 bindings
- [ ] Input sanitization functions (validate_crf, validate_speed, etc.) are either called from Python production code or removed from PyO3 bindings if Rust-internal validation covers the same checks
- [ ] Stub file reflects the final public API surface

[↑ Back to list](#bl-067-ref)

#### 📋 BL-068: Audit and trim unused PyO3 bindings from v006 filter engine

**Status:** open
**Tags:** dead-code, rust-python, api-surface

**Current state:** Three v006 filter engine features (Expression Engine, Graph Validation, Filter Composition) expose Python bindings via PyO3 that are only used in parity tests, never in production code. The Rust code uses these capabilities internally (e.g., DrawtextBuilder uses Expr for alpha fades, DuckingPattern uses composition).

**Gap:** PyO3 bindings were created in v006/01-filter-engine for all three features but no Python production code consumes them. The Rust-internal usage works fine without the Python bindings.

**Impact:** Six unused Python binding functions inflate the public API surface. Maintaining PyO3 wrappers for internally-consumed Rust code adds build complexity without value.

**Acceptance Criteria:**
- [ ] Expression Engine (Expr), Graph Validation (validate, validated_to_string), and Filter Composition (compose_chain, compose_branch, compose_merge) PyO3 bindings are either used by Python production code or removed from the public API
- [ ] If bindings are retained for future use, they are documented as such in the stub file
- [ ] Parity tests are updated to reflect any binding changes

[↑ Back to list](#bl-068-ref)
