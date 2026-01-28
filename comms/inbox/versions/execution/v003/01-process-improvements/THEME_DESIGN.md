# Theme 01: process-improvements

## Overview

Address technical debt and CI improvements from v002 retrospective. Feature 1 (async-repository) is a critical prerequisite for Theme 2 and must execute first in the version.

## Context

v002 retrospective identified:
- Synchronous SQLite incompatible with FastAPI async handlers
- Alembic migrations not verified for reversibility in CI
- CI runs full matrix even for docs-only commits (wastes ~45 min)

Explorations completed:
- `aiosqlite-migration`: Confirmed API compatibility, patterns documented
- `alembic-verification`: Existing migrations are reversible, CI step defined
- `ci-path-filters`: dorny/paths-filter approach documented

## Architecture Decisions

### AD-001: Dual Repository Pattern
Keep both sync and async repository implementations:
- `VideoRepository` (sync) - For CLI tools, scripts, migrations
- `AsyncVideoRepository` (async) - For FastAPI endpoints

### AD-002: Protocol Mirroring
AsyncVideoRepository mirrors VideoRepository method-for-method, just with async/await.

### AD-003: CI Job Structure
Three-job structure for path filtering:
1. `changes` - Detect what changed
2. `test` - Conditional on code changes
3. `ci-status` - Always runs, satisfies required checks

## Backlog Items

| ID | Title | Priority | Feature |
|----|-------|----------|---------|
| BL-013 | Add async repository implementation for FastAPI | P2 | 001 |
| BL-015 | Add migration verification to CI | P2 | 002 |
| BL-017 | Optimize CI to skip heavy steps for docs-only commits | P2 | 003 |

## Dependencies
- v002 VideoRepository (for pattern reference)
- v002 Alembic migrations (for verification)

## Execution Order
1. **001-async-repository** - CRITICAL: Must complete before Theme 2
2. 002-migration-ci-verification - Independent
3. 003-ci-path-filters - Independent

## Evidence Sources

| Claim | Source |
|-------|--------|
| aiosqlite API mirrors sqlite3 | `comms/outbox/exploration/aiosqlite-migration/api-comparison.md` |
| Contract test pattern with pytest-asyncio | `comms/outbox/exploration/aiosqlite-migration/contract-test-strategy.md` |
| Existing migrations reversible | `comms/outbox/exploration/alembic-verification/current-state.md` |
| Alembic verification commands | `comms/outbox/exploration/alembic-verification/verification-commands.md` |
| dorny/paths-filter pattern | `comms/outbox/exploration/ci-path-filters/conditional-jobs.md` |
| CI job structure (changes → test → ci-status) | `comms/outbox/exploration/ci-path-filters/ci-yml-changes.md` |

## Success Criteria
- AsyncVideoRepository passes same contract tests as sync version
- CI fails if migration not reversible
- Docs-only commits skip test matrix (save ~44 min)