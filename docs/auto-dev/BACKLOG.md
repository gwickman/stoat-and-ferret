# Project Backlog

*Last updated: 2026-02-21 15:39*

**Total completed:** 49 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 1 |
| P1 | High | 4 |
| P2 | Medium | 1 |
| P3 | Low | 1 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-055-ref"></a>[BL-055](#bl-055) | P0 | l | Fix flaky E2E test in project-creation.spec.ts (toBeHidden timeout) | The E2E test at gui/e2e/project-creation.spec.ts:31 inter... |
| <a id="bl-019-ref"></a>[BL-019](#bl-019) | P1 | m | Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore | Add Windows bash null redirect guidance to AGENTS.md and ... |
| <a id="bl-053-ref"></a>[BL-053](#bl-053) | P1 | l | Add PR vs BL routing guidance to AGENTS.md (stoat-and-ferret) | AGENTS.md in the stoat-and-ferret project lists both add_... |
| <a id="bl-054-ref"></a>[BL-054](#bl-054) | P1 | l | Add WebFetch safety rules to AGENTS.md | Mirror of auto-dev-mcp BL-517. Add WebFetch safety block ... |
| <a id="bl-056-ref"></a>[BL-056](#bl-056) | P1 | xl | Wire up structured logging at application startup | **Current state:** `configure_logging()` exists in `src/s... |
| <a id="bl-057-ref"></a>[BL-057](#bl-057) | P2 | l | Add file-based logging with rotation to logs/ directory | **Current state:** After BL-056, structured logging will ... |
| <a id="bl-011-ref"></a>[BL-011](#bl-011) | P3 | m | Consolidate Python/Rust build backends | v001 uses hatchling for Python package management and mat... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| agents-md | 3 | BL-019, BL-053, BL-054 |
| observability | 2 | BL-056, BL-057 |
| logging | 2 | BL-056, BL-057 |
| tooling | 1 | BL-011 |
| build | 1 | BL-011 |
| complexity | 1 | BL-011 |
| windows | 1 | BL-019 |
| gitignore | 1 | BL-019 |
| product-requests | 1 | BL-053 |
| documentation | 1 | BL-053 |
| decision-framework | 1 | BL-053 |
| webfetch | 1 | BL-054 |
| safety | 1 | BL-054 |
| hang-prevention | 1 | BL-054 |
| bug | 1 | BL-055 |
| e2e | 1 | BL-055 |
| ci | 1 | BL-055 |
| flaky-test | 1 | BL-055 |
| wiring-gap | 1 | BL-056 |

## Item Details

### P0: Critical

#### 📋 BL-055: Fix flaky E2E test in project-creation.spec.ts (toBeHidden timeout)

**Status:** open
**Tags:** bug, e2e, ci, flaky-test

The E2E test at gui/e2e/project-creation.spec.ts:31 intermittently fails with a toBeHidden assertion timeout on the project creation modal. The test fails on main (GitHub Actions run 22188785818) independent of any feature branch changes. During v007 execution, this caused the dynamic-parameter-forms feature to receive a 'partial' completion status despite 12/12 acceptance criteria passing and all other quality gates green. The execution pipeline halted, requiring manual restart. Any future feature touching the E2E CI job is at risk of the same false-positive halt.

**Acceptance Criteria:**
- [ ] project-creation.spec.ts:31 toBeHidden assertion passes reliably across 10 consecutive CI runs
- [ ] No E2E test requires retry loops to pass in CI
- [ ] Flaky test fix does not alter the tested project creation functionality

**Notes:** Discovered during v007 execution. PR #88 (dynamic-parameter-forms) was retried 3 times per AGENTS.md limit without resolution. Likely cause: timing-dependent modal animation or state cleanup between tests.

[↑ Back to list](#bl-055-ref)

### P1: High

#### 📋 BL-019: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore

**Status:** open
**Tags:** windows, agents-md, gitignore

Add Windows bash null redirect guidance to AGENTS.md and add `nul` to .gitignore. In bash contexts on Windows: Always use `/dev/null` for output redirection (Git Bash correctly translates this to the Windows null device). Never use bare `nul` which gets interpreted as a literal filename in MSYS/Git Bash environments. Correct: `command > /dev/null 2>&1`. Wrong: `command > nul 2>&1`.

**Use Case:** This feature addresses: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore. It improves the system by resolving the described requirement.

[↑ Back to list](#bl-019-ref)

#### 📋 BL-053: Add PR vs BL routing guidance to AGENTS.md (stoat-and-ferret)

**Status:** open
**Tags:** agents-md, product-requests, documentation, decision-framework

AGENTS.md in the stoat-and-ferret project lists both add_product_request and add_backlog_item in the tool inventory but provides no guidance on when to use which. Claude Code sessions following AGENTS.md have no routing guidance for capturing ideas vs filing structured bugs.

The exploration pr-vs-bl-guidance on auto-dev-mcp (Gap 4) identified that AGENTS.md across all managed projects has zero PR vs BL routing guidance. Since AGENTS.md is the first document Claude Code reads in every session, it is the highest-leverage location for this guidance.

Without this, Claude Code defaults to add_backlog_item for all discoveries, bypassing the lightweight product request pathway entirely.

**Use Case:** During any Claude Code session on stoat-and-ferret, the agent reads AGENTS.md first. When it discovers an improvement opportunity mid-implementation, it currently has no guidance on whether to file a PR or BL. With this change, AGENTS.md tells it to default to product requests for ideas and reserve backlog items for structured problems.

**Acceptance Criteria:**
- [ ] AGENTS.md contains a section documenting when to create a Product Request vs a Backlog Item
- [ ] Section includes the maturity gradient: PR for ideas/observations, BL for structured problems with acceptance criteria
- [ ] Section includes the default rule: when in doubt, start with a Product Request
- [ ] Section cross-references add_product_request and add_backlog_item tool_help for detailed guidance

**Notes:** Mirror of BL-510 (auto-dev-mcp). Keep the AGENTS.md addition concise — 3-5 lines max. Content should be identical across all managed projects for consistency.

[↑ Back to list](#bl-053-ref)

#### 📋 BL-054: Add WebFetch safety rules to AGENTS.md

**Status:** open
**Tags:** agents-md, webfetch, safety, hang-prevention

Mirror of auto-dev-mcp BL-517. Add WebFetch safety block to AGENTS.md. Exact text:

## WebFetch Safety (mandatory)
- NEVER WebFetch a URL you generated from memory — only WebFetch URLs returned by WebSearch
- Prefer WebSearch over WebFetch for research
- MANDATORY: Before every WebFetch call you MUST run: curl -sL --max-time 10 -o /dev/null -w "%{http_code}" &lt;url&gt; and ONLY proceed with WebFetch if curl returns 2xx/3xx

stoat-and-ferret v006 Task 004 was the first incident — 2 hung WebFetch calls froze the session for 3 hours.

**Use Case:** Same as BL-517: prevent WebFetch hangs from freezing sessions by requiring URL verification before every WebFetch call.

**Acceptance Criteria:**
- [ ] AGENTS.md contains a '## WebFetch Safety (mandatory)' section with all 3 rules verbatim
- [ ] The section is placed near top-level instructions, not buried at the end
- [ ] No other changes to AGENTS.md beyond the insertion

[↑ Back to list](#bl-054-ref)

#### 📋 BL-056: Wire up structured logging at application startup

**Status:** open
**Tags:** observability, logging, wiring-gap

**Current state:** `configure_logging()` exists in `src/stoat_ferret/logging.py` and 10 modules emit structlog calls, but `configure_logging()` is never called at startup. `settings.log_level` (via `STOAT_LOG_LEVEL` env var) is defined but never consumed. As a result, all `logger.info()` calls are silently dropped (Python's `lastResort` handler only shows WARNING+), and the only functioning log output is uvicorn's hardcoded `log_level="info"`.

**Gap:** The logging infrastructure was built in v002/v003 but never wired together. The function, the setting, and the log call sites all exist independently with no connection between them.

**Impact:** No application-level logging is visible. Correlation IDs, job lifecycle events, effect registration, websocket events, and all structured log data are lost. Debugging production issues requires code changes to enable any logging.

**Use Case:** During development and incident debugging, any developer or the auto-dev execution pipeline needs visible structured log output to diagnose failures without modifying code.

**Acceptance Criteria:**
- [ ] Application calls configure_logging() during startup lifespan before any request handling
- [ ] settings.log_level value is passed to configure_logging() and controls the root logger level
- [ ] STOAT_LOG_LEVEL=DEBUG produces visible debug output on stdout
- [ ] All existing logger.info() calls across the 10 modules produce visible structured output at INFO level
- [ ] uvicorn log_level uses settings.log_level instead of hardcoded 'info'
- [ ] Existing tests continue to pass with logging active

**Notes:** Scope: wires up existing stdout-only logging infrastructure. File-based logging is a separate follow-on item.

[↑ Back to list](#bl-056-ref)

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

### P3: Low

#### 📋 BL-011: Consolidate Python/Rust build backends

**Status:** open
**Tags:** tooling, build, complexity

v001 uses hatchling for Python package management and maturin for Rust/PyO3 builds. This dual-backend approach adds complexity. Evaluate whether the build system can be simplified.

**Use Case:** This feature addresses: Consolidate Python/Rust build backends. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Evaluate if hatchling + maturin can be unified
- [ ] Document build system architecture and rationale
- [ ] Simplify if possible without breaking functionality
- [ ] Update developer documentation

[↑ Back to list](#bl-011-ref)
