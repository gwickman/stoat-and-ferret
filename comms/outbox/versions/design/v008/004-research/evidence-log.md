# Evidence Log — v008

## Playwright Default Assertion Timeout

- **Value**: 5000ms (5 seconds)
- **Source**: DeepWiki query on `microsoft/playwright` — assertion timeout precedence documentation
- **Data**: "The default timeout for assertions is 5000ms (5 seconds)." Timeout precedence: per-assertion > expect.configure() > expect.timeout in config > default 5000ms.
- **Rationale**: The flaky `toBeHidden()` at `project-creation.spec.ts:37` uses this default. Other tests in the project explicitly set 10-15s timeouts for async operations. The 5s default is insufficient for CI environments.

## E2E Test Timeout Values (Existing Codebase)

- **Value**: 10,000-15,000ms explicit timeouts in peer E2E tests
- **Source**: Codebase search across `gui/e2e/*.spec.ts`
- **Data**: `scan.spec.ts` uses `timeout: 10000`; `accessibility.spec.ts` uses `timeout: 15_000`; `effect-workshop.spec.ts` uses mixed 5-15s
- **Rationale**: The project's established pattern is 10-15s for async operation assertions. BL-055 fix should use 10,000ms to match.

## configure_logging() Level Parameter Type

- **Value**: `int` (Python `logging` module constants)
- **Source**: `src/stoat_ferret/logging.py:15` — function signature
- **Data**: `def configure_logging(json_format: bool = True, level: int = logging.INFO) -> None:`
- **Rationale**: Settings provides `Literal["DEBUG", "INFO", ...]` (string). Conversion needed: `getattr(logging, settings.log_level)` → `int`.

## settings.log_level Type

- **Value**: `Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` (string)
- **Source**: `src/stoat_ferret/api/settings.py` — Settings class definition
- **Data**: `log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")`
- **Rationale**: Type mismatch with `configure_logging(level: int)` is confirmed. Standard conversion pattern: `getattr(logging, settings.log_level)`.

## Structlog Module Count

- **Value**: 9 modules
- **Source**: Codebase grep for `structlog.get_logger`
- **Data**: app.py, effects.py, ws.py, scan.py, thumbnail.py, manager.py, registry.py, queue.py, observable.py
- **Rationale**: BL-056 AC #4 says "all existing logger.info() calls across the 10 modules." Actual count is 9. The backlog description says 10 — minor discrepancy, does not affect implementation.

## DEFAULT_HEARTBEAT_INTERVAL

- **Value**: 30 (seconds)
- **Source**: `src/stoat_ferret/api/routers/ws.py:15`
- **Data**: `DEFAULT_HEARTBEAT_INTERVAL = 30` — matches `settings.ws_heartbeat_interval` default of 30
- **Rationale**: Values are already aligned. Wiring replaces the constant with the settings value, maintaining the same default behavior.

## create_tables_async() Duplication Count

- **Value**: 3 copies across test files with inconsistent DDL coverage
- **Source**: Codebase grep for `create_tables_async`
- **Data**: test_async_repository_contract.py (8 DDL), test_project_repository_contract.py (10 DDL), test_clip_repository_contract.py (12 DDL). Primary sync `create_tables()` executes 12 DDL statements.
- **Rationale**: Per LRN-035 (rule of three), extraction is justified. BL-058 adds a 4th consumer (app lifespan), making extraction necessary. The inconsistency (8 vs 10 vs 12 statements) is a latent bug risk.

## Unconsumed Settings Fields

- **Value**: 3 fields — `debug`, `log_level`, `ws_heartbeat_interval`
- **Source**: Full audit of Settings class vs codebase usage (grep for each field)
- **Data**: 6 of 9 fields consumed (database_path, api_host, api_port, thumbnail_dir, gui_static_path, allowed_scan_roots). 3 orphaned.
- **Rationale**: After BL-056 (wires log_level) and BL-062 (wires debug + ws_heartbeat_interval), all 9 fields will be consumed. BL-062 AC #3 satisfied.

## Historical Session Durations

- **Value**: Feature sessions range 60-760 seconds; exploration sessions 120-520 seconds
- **Source**: query_cli_sessions (session_list, since_days=60)
- **Data**: 20 recent sessions show durations from 57s (simple subagent) to 3512s (v007 retrospective). Typical feature implementation sessions: 120-500s. Source: query_cli_sessions
- **Rationale**: v008 features are wiring fixes (smaller than typical features). Expected session duration: 60-300s per feature.

## Tool Reliability Risks

- **Value**: WebFetch 34.9% error rate; deepwiki 15% error rate; Edit 8.7% error rate
- **Source**: query_cli_sessions (tool_usage, since_days=60)
- **Data**: Bash 16.7% errors (expected — test/build failures). WebFetch 34.9% (known fragile). Edit 8.7% (string matching failures). All MCP tools 0% errors. Source: query_cli_sessions
- **Rationale**: v008 features don't depend on WebFetch or deepwiki. Edit error rate is manageable. No tool reliability risks for v008 scope.

## Learning Verification Table

| Learning | Status | Evidence |
|----------|--------|----------|
| LRN-033 | VERIFIED | Flaky toBeHidden() assertion still present at `project-creation.spec.ts:37` |
| LRN-031 | VERIFIED | All 4 backlog items follow current-state/gap/impact format with testable ACs |
| LRN-016 | VERIFIED | All 5 AC-referenced functions/fields exist with correct names and locations |
| LRN-019 | VERIFIED | No schema creation in lifespan; DB startup still unwired |
| LRN-029 | VERIFIED | Both create_tables() and Alembic available; simpler path justified |
| LRN-035 | VERIFIED | 3 test files duplicate create_tables_async() with inconsistent DDL |
| LRN-015 | VERIFIED | E2E tests already run on ubuntu-latest only (single platform) |
