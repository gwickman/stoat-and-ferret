# Exploration: design-v009-006-critical

Critical thinking and risk investigation for v009 design.

## What Was Produced

All outputs saved to `comms/outbox/versions/design/v009/006-critical-thinking/`:

- **README.md** — Summary with risk counts, resolutions, design changes, and confidence assessment
- **risk-assessment.md** — Detailed assessment of all 7 risks with investigation findings and resolutions
- **refined-logical-design.md** — Updated logical design incorporating risk investigation findings
- **investigation-log.md** — Detailed log of all 5 codebase/external investigations with evidence

## Key Findings

1. SPA catch-all route must replace (not coexist with) StaticFiles mount
2. AuditLogger needs separate sync SQLite connection
3. BL-064 scope increases to include frontend pagination UI
4. WebSocket scan broadcasts fire from job handler, not router endpoint
5. Test double injection pattern works correctly — no change needed
