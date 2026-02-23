# Project Backlog

*Last updated: 2026-02-23 10:03*

**Total completed:** 59 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 0 |
| P1 | High | 0 |
| P2 | Medium | 4 |
| P3 | Low | 4 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-061-ref"></a>[BL-061](#bl-061) | P2 | l | Wire or remove execute_command() Rust-Python FFmpeg bridge | **Current state:** `execute_command()` was built in v002/... |
| <a id="bl-069-ref"></a>[BL-069](#bl-069) | P2 | xl | Update C4 architecture documentation for v009 changes | C4 documentation was last generated for v008. v009 introd... |
| <a id="bl-070-ref"></a>[BL-070](#bl-070) | P2 | m | Add Browse button for scan directory path selection | Currently the Scan Directory feature requires users to ma... |
| <a id="bl-071-ref"></a>[BL-071](#bl-071) | P2 | m | Add .env.example file for environment configuration template | The project has no .env.example file to guide new develop... |
| <a id="bl-019-ref"></a>[BL-019](#bl-019) | P3 | m | Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore | Add Windows bash null redirect guidance to AGENTS.md and ... |
| <a id="bl-066-ref"></a>[BL-066](#bl-066) | P3 | l | Add transition support to Effect Workshop GUI | **Current state:** `POST /projects/{id}/effects/transitio... |
| <a id="bl-067-ref"></a>[BL-067](#bl-067) | P3 | l | Audit and trim unused PyO3 bindings from v001 (TimeRange ops, input sanitization) | **Current state:** Several Rust functions are exposed via... |
| <a id="bl-068-ref"></a>[BL-068](#bl-068) | P3 | l | Audit and trim unused PyO3 bindings from v006 filter engine | **Current state:** Three v006 filter engine features (Exp... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| rust-python | 3 | BL-061, BL-067, BL-068 |
| wiring-gap | 2 | BL-061, BL-066 |
| gui | 2 | BL-066, BL-070 |
| dead-code | 2 | BL-067, BL-068 |
| api-surface | 2 | BL-067, BL-068 |
| documentation | 2 | BL-069, BL-071 |
| user-feedback | 2 | BL-070, BL-071 |
| windows | 1 | BL-019 |
| agents-md | 1 | BL-019 |
| gitignore | 1 | BL-019 |
| ffmpeg | 1 | BL-061 |
| effects | 1 | BL-066 |
| transitions | 1 | BL-066 |
| architecture | 1 | BL-069 |
| c4 | 1 | BL-069 |
| ux | 1 | BL-070 |
| library | 1 | BL-070 |
| devex | 1 | BL-071 |
| onboarding | 1 | BL-071 |

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

**Notes:** size: l — C4 regeneration following established process, auto-estimate inflated by detailed description listing all 5 drift areas with code evidence

[↑ Back to list](#bl-069-ref)

#### 📋 BL-070: Add Browse button for scan directory path selection

**Status:** open
**Tags:** gui, ux, library, user-feedback

Currently the Scan Directory feature requires users to manually type or paste a directory path. There is no file/folder browser dialog to help users navigate to and select the target directory. This creates friction - users must know the exact path and type it correctly, which is error-prone and a poor UX pattern for desktop-style file selection.

**Use Case:** When a user wants to scan a media directory, they need to navigate to it visually rather than remembering and typing the full path, especially on systems with deep directory hierarchies.

**Acceptance Criteria:**
- [ ] Scan Directory UI includes a Browse button next to the path input field
- [ ] Clicking Browse opens a folder selection dialog that allows navigating the filesystem
- [ ] Selecting a folder in the dialog populates the path input field with the chosen path
- [ ] Users can still manually type a path as an alternative to browsing

[↑ Back to list](#bl-070-ref)

#### 📋 BL-071: Add .env.example file for environment configuration template

**Status:** open
**Tags:** devex, documentation, onboarding, user-feedback

The project has no .env.example file to guide new developers or users through environment configuration. Anyone setting up the project must reverse-engineer which environment variables are needed by reading source code. This is a common onboarding friction point - without a template, users may miss required configuration and encounter confusing startup failures.

**Use Case:** When a new developer or user clones the repo, they need a clear reference for what environment variables to configure before the application will start correctly.

**Acceptance Criteria:**
- [ ] A .env.example file exists in the project root with all required/optional environment variables documented
- [ ] Each variable includes a comment explaining its purpose and acceptable values
- [ ] The file contains sensible defaults or placeholder values (not real secrets)
- [ ] README or setup documentation references .env.example as part of the getting-started workflow

[↑ Back to list](#bl-071-ref)

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
