# Implementation Plan: env-example

## Overview

Create `.env.example` in the project root documenting all 11 Settings fields with `STOAT_` prefix, grouped by category. Update three documentation files to reference it and fix the 2-variable gap in configuration docs.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `.env.example` | Create | Environment configuration template with all 11 Settings fields |
| `docs/setup/02_development-setup.md` | Modify | Add .env.example reference in setup steps |
| `docs/manual/01_getting-started.md` | Modify | Add .env.example reference |
| `docs/setup/04_configuration.md` | Modify | Add missing log_backup_count and log_max_bytes variables |

## Test Files

None — manual verification only.

## Implementation Stages

### Stage 1: Create .env.example

1. Create `.env.example` in project root with all 11 Settings fields:
   - **Database:** `STOAT_DATABASE_PATH=data/stoat.db`
   - **API Server:** `STOAT_API_HOST=127.0.0.1`, `STOAT_API_PORT=8000`
   - **Logging:** `STOAT_LOG_LEVEL=INFO`, `STOAT_LOG_BACKUP_COUNT=5`, `STOAT_LOG_MAX_BYTES=10485760`
   - **Debug:** `STOAT_DEBUG=false`
   - **Frontend:** `STOAT_GUI_STATIC_PATH=gui/dist`, `STOAT_THUMBNAIL_DIR=data/thumbnails`
   - **WebSocket:** `STOAT_WS_HEARTBEAT_INTERVAL=30`
   - **Security:** `STOAT_ALLOWED_SCAN_ROOTS=` (empty = all paths allowed)
   - Each variable preceded by a comment explaining purpose and acceptable values

**Verification:**
```bash
# Verify file exists and has all 11 variables
grep -c "^STOAT_" .env.example  # Should output 11
```

### Stage 2: Update documentation

1. Modify `docs/setup/02_development-setup.md`:
   - Add `cp .env.example .env` step in the setup instructions
2. Modify `docs/manual/01_getting-started.md`:
   - Add reference to `.env.example` for configuration
3. Modify `docs/setup/04_configuration.md`:
   - Add entries for `STOAT_LOG_BACKUP_COUNT` and `STOAT_LOG_MAX_BYTES`

**Verification:**
```bash
# Verify docs reference .env.example
grep -l ".env.example" docs/setup/02_development-setup.md docs/manual/01_getting-started.md
# Verify configuration docs completeness
grep -c "STOAT_" docs/setup/04_configuration.md  # Should cover all 11
```

## Test Infrastructure Updates

None — no automated tests for this feature.

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Risks

- Missing a Settings field — mitigated by cross-referencing against `settings.py` field inventory (11 fields documented in research)
- See `comms/outbox/versions/design/v011/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat: add .env.example with all Settings fields documented (BL-071)
```
