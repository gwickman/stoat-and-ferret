# Exploration: design-v010-004-research

Research and investigation for v010 version design, covering all 5 backlog items (BL-072, BL-073, BL-074, BL-077, BL-078).

## What Was Produced

All artifacts saved to `comms/outbox/versions/design/v010/004-research/`:

| File | Description |
|------|-------------|
| README.md | Research summary, findings, recommendations |
| codebase-patterns.md | Current implementation details with file paths and code snippets |
| external-research.md | asyncio patterns, Ruff ASYNC rules, cancellation patterns |
| evidence-log.md | Concrete values, learning verification table, session analytics |
| impact-analysis.md | Dependencies, breaking changes, test needs, doc updates |

No `persistence-analysis.md` — no features introduce persistent state (progress and cancellation are in-memory on `_AsyncJobEntry`).

## Key Findings

1. **Ruff ASYNC221 replaces custom grep script** — BL-077 reduces from ~20-line script to 1-line config change
2. **Frontend already reads progress** — ScanModal renders progress bar from `status.progress`, only backend population missing
3. **Schema already has progress field** — `JobStatusResponse.progress` exists but is never populated
4. **`asyncio.create_subprocess_exec()`** is the right approach for BL-072 (native async, no thread overhead)
5. **`asyncio.Event`** is the right cancellation mechanism for BL-074 (lightweight, stdlib, awaitable)
6. **0 new create_app() kwargs** — all v010 changes are internal to existing components
7. **All 12 learnings verified** — conditions still present in codebase
8. **health.py:96** will be flagged by ASYNC rules — needs `asyncio.to_thread()` conversion
