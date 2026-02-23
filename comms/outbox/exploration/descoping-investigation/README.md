# Descoping Investigation: Is Recommendation 1A Addressing a Current Gap or a Historical One?

## Answer

**Recommendation 1A is addressing a real current gap, but it is misframed.** The anti-descoping rules already prevent backlog items from being dropped during design. The actual gap is different: Out of Scope sections in requirements.md routinely list items derived from design-doc specifications without creating backlog items to track them. Recommendation 1A as stated ("track descoped items as backlog") risks normalizing backlog-level descoping when the current rules forbid it entirely.

## Evidence Summary

### The anti-descoping rules are strong and were present from the start

Seven of nine design task prompts contain explicit anti-descoping language: "ALL backlog items from PLAN.md are MANDATORY — no deferrals, no descoping." These rules were introduced on 2026-02-08 in commit `e241a73` — the same commit that created the design prompt structure. **Every version from v004 onwards was designed under these rules.**

### The three RCA failures were NOT backlog-item descoping

None of the three failures involved a backlog item being removed from a version's scope:

1. **Cancellation** (rca-no-cancellation): Specified in 6 design-doc locations. Never added to the backlog. BL-027's acceptance criteria omitted it. The anti-descoping rules couldn't protect it because it was never a backlog item.

2. **Progress reporting** (rca-no-progress): BL-027 AC #2 said "with progress information." It was marked PASS because the schema field existed, even though it always returned null. This was incomplete delivery of a backlog item, not descoping.

3. **Clip management** (rca-clip-management): Design docs placed clip CRUD in Phase 3. BL-035 specified read-only display. Full CRUD was never a backlog item. The anti-descoping rules couldn't protect what was never in the backlog.

### v007-v009 show the rules working as intended

All Out of Scope items in v007-v009 requirements are capabilities that were never backlog items (drag-and-drop, GPU acceleration, undo/redo, etc.). No backlog item was dropped from any of these versions. The anti-descoping rules are effective for their intended purpose.

## What Should Actually Be Done

The recommendation should be **modified** (not adopted as stated). See [revised-recommendation.md](./revised-recommendation.md) for the specific proposal. The core insight: the gap is not "descoped items aren't tracked" — it's that the design process doesn't ensure design-doc specifications make it into the backlog with complete acceptance criteria before versioning begins.
