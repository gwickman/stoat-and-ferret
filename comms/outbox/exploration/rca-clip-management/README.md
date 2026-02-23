# RCA: Clip Management Controls Omitted from GUI

## Summary

The ProjectDetails page displays clips in a read-only table. The backend has full clip CRUD (`POST`, `PATCH`, `DELETE` on `/api/v1/projects/{id}/clips`) — implemented in v003, tested, and operational since v004. The GUI has no Add, Edit, or Delete buttons for clips.

## Root Cause Classification: **Implicit Deferral Without Tracking**

This is neither a pure oversight nor an explicit deferral. It is a **process gap** where work was deferred by design-document phasing but never tracked as deferred work in the backlog or retrospectives.

## Evidence Summary

1. **Design docs split clip GUI across phases.** The roadmap (01-roadmap.md, M1.12) specifies "project details view with clip list" for Phase 1, while clip selection/properties are Phase 3 (M3.1 line 576 of 08-gui-architecture.md). No milestone ever specifies "Add/Edit/Delete clip buttons" for the ProjectDetails page — it falls into a gap between Phase 1's read-only display and Phase 3's full timeline canvas.

2. **Backlog item BL-035 never specified clip CRUD.** The v005 backlog item for the project manager (BL-035, completed 2026-02-09) specifies "Project details view displays clip list with Rust-calculated timeline positions" — read-only by acceptance criteria. No companion backlog item existed for clip management controls until BL-075 was created on 2026-02-23.

3. **Retrospectives never flagged the gap.** The v005 theme 03 retrospective lists 15 deliverables and 5 technical debt items. Clip management controls appear in none of them. The v005 version retrospective lists 11 technical debt items — none about clip CRUD.

4. **Wiring audits caught adjacent issues but missed this one.** The v005 wiring audit found 3 gaps (WebSocket broadcasts, pagination total, SPA routing) but did not flag the absence of clip management controls. The v006-v007 wiring audit caught the identical pattern for transitions (Gap 4: "Transition API has no GUI") but clip CRUD was already an established gap by then.

5. **The existing clip-management-gaps exploration (pre-dating this RCA) characterized it as "intentional phasing"** — which is partially correct but misses the tracking failure. The phasing was implicit in milestone definitions, not an explicit decision with a tracked deferral.

## Process Gaps Identified

| Gap | Description | Impact |
|-----|-------------|--------|
| **No deferral tracking** | When Phase 1 delivered read-only clips, no backlog item was created for the remaining CRUD controls | Work invisible until manual discovery |
| **Acceptance criteria scope** | BL-035 acceptance criteria matched the Phase 1 scope exactly but didn't reference the full API capability | Easy to mark "complete" without noticing the gap |
| **Retrospective blind spot** | Retrospectives compared delivered vs planned, not delivered vs possible | Backend capabilities without GUI counterparts went unnoticed |
| **Wiring audit gap** | v005 wiring audit focused on broken/degraded wiring, not absent wiring for existing endpoints | Pattern not in the audit methodology |

## Already Addressed

- **BL-075** created (2026-02-23) to track clip management controls — P1, open
- **BL-066** created (2026-02-21) to track transition GUI — P3, open, tagged `wiring-gap`
- **Wiring audits** now run per-version and have caught similar patterns (v006-v007 audit Gap 4)
- **clip-management-gaps exploration** completed with gap analysis and recommendations

## Recommendations

See [recommendations.md](./recommendations.md) for specific process changes.
See [evidence-trail.md](./evidence-trail.md) for the full chronological trace.
