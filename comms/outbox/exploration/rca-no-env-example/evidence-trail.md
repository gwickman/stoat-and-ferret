# Evidence Trail: .env.example Gap

Chronological trace from design through implementation to retrospective.

## Phase 1: Design (Pre-v001)

### Configuration Architecture Specified

**docs/design/02-architecture.md:~1207-1249** -- Full `Settings(BaseSettings)` class with:
- `env_file = ".env"`, `env_prefix = "VIDEO_EDITOR_"` (note: prefix changed to `STOAT_` during implementation)
- 9 fields: database_url, ffmpeg_path, ffmpeg_timeout_seconds, media_roots, project_dir, rust_core_log_timing, max_concurrent_renders, log_level, metrics_enabled

**docs/design/04-technical-stack.md:~1173-1210** -- Identical Settings class definition.

**docs/design/07-quality-architecture.md:~1208** -- Identical Settings class, plus smoke test pattern using `os.environ.get("SMOKE_TEST_URL")`.

**docs/design/02-architecture.md:1426** -- "Configuration | Externalized via environment variables"

**docs/design/09-security-audit.md:~159-163** -- `ALLOWED_SCAN_ROOTS` setting documented; notes "Operator should configure in production."

**Gap identified:** Design docs specify the Settings class but never list `.env.example` as a deliverable. No design doc mentions developer onboarding documentation as a requirement.

### Developer Setup Scattered

**docs/design/03-prototype-design.md:~1067-1147** -- Developer setup steps (maturin develop, uv sync, pytest) but no mention of environment configuration.

**docs/design/04-technical-stack.md:~365-373** -- Development commands (build, test, run) without any `.env` setup step.

## Phase 2: Implementation (v001-v003)

### v001 -- No Configuration Layer
**comms/inbox/versions/execution/v001/VERSION_DESIGN.md** -- Foundation: Rust/PyO3 command builder. No external config dependencies.

**comms/outbox/versions/execution/v001/retrospective.md** -- No mention of configuration or developer setup.

### v002 -- External Dependencies Without Config
**comms/inbox/versions/execution/v002/VERSION_DESIGN.md** -- Introduced SQLite database, FFmpeg execution, structlog, alembic. No settings system.

**comms/outbox/versions/execution/v002/retrospective.md** -- Flags: "Add local Docker-based testing option" and "Document CI dependencies centrally." Neither addresses developer env config.

### v003 -- pydantic-settings Introduced (Critical Version)
**comms/inbox/versions/execution/v003/VERSION_DESIGN.md** -- Theme 02 (api-foundation) established externalized settings via pydantic-settings with `@lru_cache`.

**comms/outbox/versions/execution/v003/retrospective.md** -- Notes "Structured logging integration" as deferred debt. No mention of documenting env vars for developers.

**Actual implementation: `src/stoat_ferret/api/settings.py`** -- `Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_prefix="STOAT_", env_file=".env")`. 11 fields, all with defaults.

## Phase 3: Incremental Settings Growth (v004-v007)

### v004 -- Security Settings
**comms/outbox/versions/execution/v004/retrospective.md** -- References `ALLOWED_SCAN_ROOTS` and notes `Settings @lru_cache` prevents runtime config changes (accepted tradeoff). No env documentation mention.

### v005 -- Frontend + New Settings Fields
**comms/outbox/versions/execution/v005/retrospective.md** -- Flags `ws_heartbeat_interval` as "wiring should be verified." No env documentation mention.

**comms/outbox/versions/design/v005/002-backlog/retrospective-insights.md** -- "Earlier audits would have caught [startup wiring gaps] sooner." Prescient about v008, but still no documentation mention.

### v006-v007 -- No New Settings
**comms/outbox/versions/execution/v007/retrospective.md** -- Critical discovery: "Missing wiring audit before feature development. The startup wiring gaps (BL-056, BL-058, BL-062) existed since v002/v003." Focus is on code wiring, not developer documentation.

## Phase 4: Wiring Fix-Up (v008-v009)

### v008 -- All Settings Finally Wired
**comms/outbox/versions/execution/v008/retrospective.md** -- BL-056 (logging), BL-062 (debug, heartbeat) wired. Recommends "Settings consumption lint." **Still no mention of `.env.example` or developer-facing documentation.**

### v009 -- Observability Wired
**comms/outbox/versions/execution/v009/retrospective.md** -- BL-057, BL-059, BL-060 wired. C4 documentation regeneration failed. **No mention of `.env.example`.**

## Phase 5: Discovery (2026-02-23)

### BL-071 Created
**Backlog item BL-071** -- "Add .env.example file for environment configuration template" -- Status: OPEN, Priority: P2, Tags: devex/documentation/onboarding/user-feedback. Created 2026-02-23. Not assigned to any version.

## Pattern Summary

The evidence shows a clear pattern:
1. **Design phase** specified the configuration mechanism but not the documentation artifact
2. **v003** implemented the Settings class; no `.env.example` was created alongside it
3. **v004-v007** added/modified settings fields; no version's acceptance criteria included env documentation
4. **v008** wired orphaned settings and recommended a "settings consumption lint" -- the closest anyone came to addressing the gap, but focused on code verification, not developer documentation
5. **9 retrospectives** examined code quality, wiring gaps, CI stability, and process improvements -- none examined developer onboarding or configuration documentation
6. The gap was identified externally, not by the development process
