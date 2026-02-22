# Exploration: v008-retro-006-learn

Extracted 7 new learnings (LRN-040 through LRN-046) from v008 retrospective materials and identified 3 existing learnings reinforced by new evidence. Sources analyzed: 4 completion reports, 2 theme retrospectives, 1 version retrospective, session health findings (004b), and session analytics (30-day lookback).

## Artifacts Produced

| Path | Description |
|------|-------------|
| `comms/outbox/versions/retrospective/v008/006-learnings/README.md` | Summary with new learnings table, reinforced learnings, and filtered items |
| `comms/outbox/versions/retrospective/v008/006-learnings/learnings-detail.md` | Full content of all 7 learnings saved |
| `docs/auto-dev/LEARNINGS/LRN-040-*.md` through `LRN-046-*.md` | Individual learning content files |

## Key Themes

- **Idempotent startup patterns** (LRN-040): Guards for lifespan functions called multiple times
- **Static analysis as design feedback** (LRN-041): mypy catching invalid API assumptions
- **Theme planning strategies** (LRN-042, LRN-045): Grouping by modification point; isolating bug fixes
- **CI reliability** (LRN-043): Explicit E2E assertion timeouts for CI environments
- **Configuration completeness** (LRN-044): Settings consumer traceability
- **Version scoping** (LRN-046): Maintenance-focused versions with well-understood changes
