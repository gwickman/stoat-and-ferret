# Descoping Timeline

When each descoping event happened, what the current process would have prevented, and what it wouldn't.

---

## Issue 1: Job Cancellation (rca-no-cancellation)

### When it happened

| Date | Event | Version |
|------|-------|---------|
| Pre-v001 | Design docs specify cancellation in 6 locations (roadmap, API spec, architecture, GUI wireframes, DB schema) | — |
| 2026-02-08 | BL-027 created with acceptance criteria covering async submission + polling. Cancellation not mentioned. | v004 planning |
| 2026-02-08 | v004 requirements.md for `002-async-scan-endpoint` lists "Scan cancellation — not required for initial implementation" under Out of Scope (line 32) | v004 design |
| 2026-02-09 | v004 Theme 03 implemented without cancellation. Theme retrospective notes gap as low-priority tech debt. No BL item created. | v004 execution |
| 2026-02-09 | v005 scan modal ships disabled Cancel button (ScanModal.tsx:186-190) | v005 execution |
| 2026-02-23 | BL-074 created for cancellation support | Manual discovery |

### Was it a committed backlog item that got descoped?

**No.** Cancellation was a design-doc requirement that never made it into BL-027's acceptance criteria. The anti-descoping rules protected BL-027 from being removed, but BL-027 was underspecified from the start. The Out of Scope entry in v004 requirements descoped a design-doc feature, not a backlog item.

### Would the current process have prevented it?

**No.** The current rules protect backlog items from being removed. They do not verify that backlog acceptance criteria fully cover design-doc specifications. BL-027 would still pass all checks — it's in PLAN.md, it's in the version, it's mapped to a feature. The fact that it omits cancellation is invisible to the current validation.

---

## Issue 2: Progress Reporting (rca-no-progress)

### When it happened

| Date | Event | Version |
|------|-------|---------|
| Pre-v001 | Design docs specify progress in architecture (DB schema), GUI wireframes, and roadmap | — |
| 2026-02-08 | BL-027 AC #2: "Job status queryable via GET endpoint **with progress information**" | v004 planning |
| 2026-02-09 | v004 Feature 002 completion report marks FR-2 PASS because `JobStatusResponse.progress` field exists (always returns null) | v004 execution |
| 2026-02-09 | v005 ScanModal polls for progress, renders bar — permanently stuck at 0% | v005 execution |
| 2026-02-23 | BL-073 created for progress reporting | Manual discovery |

### Was it a committed backlog item that got descoped?

**No.** BL-027 explicitly required progress. It was not descoped — it was falsely marked as delivered. The backlog item was in every version design as required. The failure was in verification (completion report), not in scope management.

### Would the current process have prevented it?

**Partially.** The anti-descoping rules ensured BL-027 stayed in scope. But the rules don't prevent a completion report from falsely passing a functional requirement. This is a completion-report verification gap (addressed by recommendation 1D), not a descoping gap.

---

## Issue 3: Clip Management Controls (rca-clip-management)

### When it happened

| Date | Event | Version |
|------|-------|---------|
| Pre-v001 | Design docs specify clip CRUD API. GUI wireframes show read-only Phase 1, interactive Phase 3. | — |
| 2026-02-08 | v003 Theme 04 implements full backend clip CRUD | v003 execution |
| 2026-02-08 | BL-035 created: "Project details view displays clip list with Rust-calculated timeline positions" (read-only) | v005 planning |
| 2026-02-09 | v005 delivers read-only ProjectDetails.tsx. 5/5 acceptance criteria pass. No BL for CRUD controls. | v005 execution |
| 2026-02-23 | BL-075 created for clip management controls | Manual discovery |

### Was it a committed backlog item that got descoped?

**No.** Clip CRUD controls were never a backlog item. BL-035 was always for read-only display. The design docs placed interactive controls in a later phase, but no backlog item was created for that phase.

### Would the current process have prevented it?

**No.** BL-035 was in PLAN.md, was in the version, was mapped to a feature, and passed all acceptance criteria. The rules protected BL-035 from removal. They cannot detect that a capability available in the backend has no corresponding GUI backlog item.

---

## v007-v009: No Backlog Item Descoping

### v007 (Effect Workshop GUI)

- 11 features, all with Out of Scope sections
- Out of Scope items: drag-and-drop, GPU acceleration, undo/redo, custom expressions, nested schemas — none were ever backlog items
- All 9 backlog items (BL-044 through BL-052) fully mapped to features
- VERSION_DESIGN.md Deferred Items section lists 4 items: preview thumbnails, SPA routing, UUID-based effect IDs, RJSF migration — none were backlog items for v007
- **No backlog item descoping detected**

### v008 (Application Startup Wiring)

- 4 features with Out of Scope sections
- Out of Scope items: Alembic migration, file-based logging, log rotation, settings validation changes — none were backlog items for v008
- All 4 backlog items (BL-055, BL-056, BL-058, BL-062) fully mapped
- **No backlog item descoping detected**

### v009 (Observability Pipeline + GUI Runtime Fixes)

- 6 features with Out of Scope sections
- Out of Scope items: HEALTH_STATUS broadcast (deferred — no trigger point), log aggregation, async AuditLogger — none were backlog items for v009
- All 6 backlog items (BL-057, BL-059, BL-060, BL-063, BL-064, BL-065) fully mapped
- One notable item: v009 `003-websocket-broadcasts` Out of Scope explicitly defers HEALTH_STATUS broadcast. This matches the pattern — a design-doc capability deferred without a backlog item. But it was never a committed backlog item for v009.
- **No backlog item descoping detected**

---

## Summary

| Issue | Backlog item descoped? | Current rules would prevent? | Actual gap |
|-------|----------------------|---------------------------|-----------|
| Cancellation | No — never in backlog | No | Design-doc feature not captured in backlog AC |
| Progress | No — BL-027 included it | Partially — kept in scope but false PASS | Completion report verification |
| Clip management | No — never in backlog | No | Backend capability without GUI backlog item |
| v007-v009 OOS items | No | N/A | Same pattern continues but with low-severity items |

**Conclusion:** The anti-descoping rules are working. No backlog item has been removed from a version scope since the rules were introduced. The failures stem from features that were never adequately captured in the backlog, not from backlog items being removed.
