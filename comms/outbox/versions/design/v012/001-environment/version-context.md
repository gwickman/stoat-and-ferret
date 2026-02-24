# Version Context — v012

## Version Description

**v012 — API Surface & Bindings Cleanup**

Goal: Reduce technical debt in the Rust-Python boundary and close remaining polish items.

Depends on: v011 deployed (confirmed complete 2026-02-24).

## Themes and Features

### Theme 1: rust-bindings-audit

| Feature | Description | Backlog |
|---------|-------------|---------|
| 001-execute-command-resolution | Decide wire vs remove for `execute_command()`, implement the decision | BL-061 (P2) |
| 002-v001-bindings-audit | Audit and trim unused v001 PyO3 bindings (TimeRange ops, sanitization) | BL-067 (P3) |
| 003-v006-bindings-audit | Audit and trim unused v006 PyO3 bindings (Expr, graph validation, composition) | BL-068 (P3) |

### Theme 2: workshop-and-docs-polish

| Feature | Description | Backlog |
|---------|-------------|---------|
| 001-transition-support | Wire transition effects into the Effect Workshop GUI | BL-066 (P3) |
| 002-api-spec-progress-examples | Update API spec examples with realistic progress values for running jobs | BL-079 (P3) |

## Referenced Backlog Items

IDs only (full details in Task 002):
- **BL-061** — execute_command resolution (P2, highest priority in v012)
- **BL-066** — Transition GUI wiring (P3)
- **BL-067** — v001 bindings audit (P3)
- **BL-068** — v006 bindings audit (P3)
- **BL-079** — API spec progress examples (P3)

## Dependencies and Ordering

- BL-061 should be implemented before BL-067/BL-068 — the `execute_command` decision may affect what counts as "unused" in the bindings audits
- BL-079 benefits from v010's progress reporting being complete (confirmed: v010 complete)
- No external investigation dependencies required

## Constraints and Assumptions

- v011 must be deployed before v012 starts (confirmed complete)
- The bindings audit work is primarily deletion/simplification — low risk
- BL-061 has moderate risk if the decision is "wire it" (requires new integration code); safe if "remove"
- All 5 backlog items are P2 or P3 — no P1 urgency

## Deferred Items to Be Aware Of

| Item | From | Status | Relevance to v012 |
|------|------|--------|-------------------|
| Phase 3: Composition Engine | v008 | Deferred to post-v010 | May interact with bindings cleanup — ensure audit doesn't remove bindings needed for future composition work |
| Drop-frame timecode | v001 | Deferred TBD | Low relevance — timeline math bindings unlikely to be trimmed |
| BL-069 (C4 documentation update) | Plan | Excluded from versions | Should be updated after v012 completes |

## Excluded Items

- **BL-069** — C4 documentation update (deferred, not stoat-and-ferret code change)
- **PR-003** — auto-dev-mcp product request (not stoat-and-ferret scope)
