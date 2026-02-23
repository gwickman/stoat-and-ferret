# Revised Recommendation

## Original Recommendation 1A

> **Track Descoped Items as Backlog During Design** — When a feature's requirements.md lists an "Out of Scope" item that corresponds to a design-doc specification or a prior backlog item, the executing agent should create a `deferred` backlog item.

Target: `007-document-drafts.md` Step 5 (draft requirements.md)

## Problem with 1A as Stated

1. **Normalizes descoping.** The current rules say "no deferrals, no descoping" seven times across seven task prompts. Adding language about how to track descoped items implies that descoping is acceptable if tracked. This weakens the anti-descoping stance without justification — no backlog item has actually been descoped since the rules existed.

2. **Addresses the wrong layer.** The three RCA failures happened because design-doc features never made it into the backlog as items with proper acceptance criteria. Adding tracking at the requirements.md Out of Scope stage is too late — the damage is done by the time a feature's Out of Scope section is being written.

3. **Out of Scope sections are normal and necessary.** Every version from v007-v009 has Out of Scope sections listing things like "drag-and-drop effect application" and "GPU-accelerated transitions." These are healthy scope boundaries, not descoping failures. Requiring backlog items for all of them would create noise.

## Revised Recommendation

**Do not modify the design scripts to add "track descoped items" language.**

Instead, address each distinct failure mode with a targeted fix:

### Fix A: Backlog Quality Gate During Design (Task 002)

**What:** In Task 002 (Backlog Analysis), add a step that cross-references each backlog item's acceptance criteria against the design-doc specifications it claims to implement. Flag any backlog item whose AC covers less than the full design-doc scope.

**Why:** This catches the BL-027 problem — where the backlog item existed but was underspecified relative to the design docs. It catches the BL-035 problem — where read-only display was specified but the design docs included interactive controls.

**Where:** `002-backlog-analysis.md`, new Step 2e after the existing quality assessments:

> **2e. Design-Doc Coverage Check**
> For each backlog item, identify the design-doc sections it addresses (roadmap milestones, API spec endpoints, GUI wireframe features). Verify that the acceptance criteria cover ALL design-doc sub-items. If any design-doc sub-item is not covered by an AC, flag it and either:
> (a) Expand the backlog item's AC to cover it (using update_backlog_item), or
> (b) Verify a separate backlog item exists for the uncovered sub-item.

**Impact:** Would have caught all three RCA failures at design time — cancellation missing from BL-027, progress not testable in BL-027, and clip CRUD not in any backlog item.

### Fix B: Out of Scope Classification (Task 007)

**What:** In Task 007 (Document Drafts) Step 5, add a classification requirement for Out of Scope items: "boundary" (never intended for this version — no action needed) vs. "deferred design-doc feature" (a capability from the design docs that is being pushed to a future version — verify a backlog item exists or create one).

**Why:** This distinguishes healthy scope boundaries ("GPU-accelerated transitions") from actual deferrals of designed capabilities ("scan cancellation"). It does not normalize backlog-item descoping — it only applies to items in Out of Scope sections.

**Where:** `007-document-drafts.md`, addition to Step 5 requirements.md drafting:

> For each Out of Scope item, classify it as either:
> - **Boundary:** Not specified in design docs for any phase. No tracking needed.
> - **Deferred:** Specified in design docs but not deliverable in this version. Verify a backlog item exists for this capability. If not, note that one should be created post-design.

**Impact:** Would have caught the cancellation descoping (design-doc feature listed as Out of Scope without BL item) and could have flagged clip CRUD (backend capability without GUI backlog item).

### Do NOT modify the anti-descoping rules

The existing mandatory-scope language should remain exactly as is. It is working: no backlog item has been dropped from any version since v004. Weakening or qualifying this language would create risk without benefit.

## Recommendation for 1B (Retrospective Debt Ingestion)

**Still valid.** This is a separate issue from the design-phase gap. v004 retrospectives identified cancellation as tech debt but created no backlog items. Adding a retrospective step that converts tech-debt items to backlog items is orthogonal to the design-phase fix and should proceed as described in the synthesis.

## Recommendation for 1D (End-to-End Wiring in Completion Reports)

**Still valid.** The progress reporting false PASS is a completion-report verification failure. This is complementary to Fix A: Fix A catches underspecified AC at design time; 1D catches false PASSes at execution time.

## Summary

| Original | Verdict | Replacement |
|----------|---------|------------|
| 1A: Track descoped items as backlog | **Modified** | Fix A (backlog quality gate in Task 002) + Fix B (Out of Scope classification in Task 007) |
| 1B: Retrospective debt ingestion | **Keep as-is** | No change needed |
| 1C: Wiring audit expansion | **Keep as-is** | No change needed |
| 1D: End-to-end wiring in completion reports | **Keep as-is** | No change needed |
