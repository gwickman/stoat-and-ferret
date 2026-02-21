# Exploration: design-v008-004-research

Research and investigation for v008 (Startup Integrity & CI Stability) version design.

## What Was Produced

All outputs saved to `comms/outbox/versions/design/v008/004-research/`:

| Document | Description |
|----------|-------------|
| `README.md` | Research summary with questions, findings, unresolved items, and recommendations |
| `codebase-patterns.md` | Existing patterns: lifespan, settings, logging, DB schema, WS heartbeat, E2E tests |
| `external-research.md` | Playwright toBeHidden() best practices (DeepWiki), structlog patterns, SQLite startup |
| `evidence-log.md` | Concrete values with sources: timeouts, types, field counts, session analytics data |
| `impact-analysis.md` | Dependencies, breaking changes, test needs, documentation updates, shared files |

No `persistence-analysis.md` produced — no v008 features introduce or modify persistent state.

## Key Findings

1. **All AC references validated** — every function, field, and constant exists as described in backlog items
2. **7 learnings verified** — all conditions persist (none stale)
3. **BL-055 root cause**: Playwright default 5s timeout too short for CI; modal has no animations; fix is explicit timeout
4. **BL-056 type mismatch**: `configure_logging(level: int)` vs `settings.log_level` (string) — standard conversion needed
5. **BL-058 duplication**: 3 inconsistent async copies justify extraction per LRN-035
6. **BL-062 straightforward**: 2 wiring changes + 1 audit
7. **No tool reliability risks** for v008 scope (based on session analytics)
