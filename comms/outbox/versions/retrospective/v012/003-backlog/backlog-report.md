# v012 Backlog Verification Report

## Item-Level Detail

| Backlog Item | Title | Feature | Planned | Status Before | Action | Status After |
|--------------|-------|---------|---------|---------------|--------|--------------|
| BL-061 | Wire or remove execute_command() Rust-Python FFmpeg bridge | 001-execute-command-removal | Yes | open | completed | completed |
| BL-066 | Add transition support to Effect Workshop GUI | 001-transition-gui | Yes | open | completed | completed |
| BL-067 | Audit and trim unused PyO3 bindings from v001 (TimeRange ops, input sanitization) | 002-v001-bindings-trim | Yes | open | completed | completed |
| BL-068 | Audit and trim unused PyO3 bindings from v006 filter engine | 003-v006-bindings-trim | Yes | open | completed | completed |
| BL-079 | Fix API spec examples to show realistic progress values for running jobs | 002-api-spec-corrections | Yes | open | completed | completed |

## Cross-Referenced Items (Out-of-Scope References)

BL-069 (Update C4 architecture documentation) was referenced in the "Out of Scope" section of 4 feature requirements files (001-execute-command-removal, 002-v001-bindings-trim, 003-v006-bindings-trim, 001-transition-gui). This item is explicitly excluded from v012 in PLAN.md ("Excluded from versions: BL-069") and remains open as intended. No action taken.

## Orphaned Items

No orphaned items found. The only open backlog item (BL-069) does not reference v012 in its description or notes — it tracks C4 documentation drift from v009/v010/v011.

## Summary

- **Total items checked:** 6 (5 planned + 1 cross-referenced)
- **Items completed by this task:** 5 (BL-061, BL-066, BL-067, BL-068, BL-079)
- **Already complete:** 0
- **Still open (intentionally):** 1 (BL-069 — excluded from v012)
- **Unplanned items:** 0 (all items found in requirements.md were also in PLAN.md)
- **Issues:** None
