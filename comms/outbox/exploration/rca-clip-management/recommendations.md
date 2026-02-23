# Recommendations: Preventing Backend-GUI Wiring Gaps

Based on evidence from the clip management RCA and the broader pattern visible across wiring audits.

---

## Already Addressed

These gaps have been partially mitigated by existing mechanisms:

| Mitigation | Evidence | Remaining Gap |
|------------|----------|---------------|
| **Wiring audits** per version | Audits exist for v001-v002, v003-v004, v005, v006-v007 | Audits check broken wiring, not absent wiring for existing endpoints |
| **BL-075** tracks clip CRUD GUI | Created 2026-02-23, P1, open | Backlog item exists but 14 days after the gap was discoverable |
| **BL-066** tracks transition GUI | Created 2026-02-21, P3, tagged `wiring-gap` | Same pattern, separately discovered |
| **clip-management-gaps exploration** | Detailed gap analysis with recommendations | Identified the gap but characterized it as intentional phasing |

---

## Recommended Process Changes

### 1. Wiring Audit Methodology: Add "Uncovered Endpoints" Check

**Problem:** Current wiring audits check whether delivered code is correctly wired. They do not check whether backend endpoints have corresponding GUI surfaces.

**Change:** Add a step to the wiring audit that lists all write endpoints (POST, PATCH, DELETE) and checks whether any GUI component calls each one. Report uncovered endpoints as a separate category ("unwired" vs "broken").

**Evidence:** The v005 audit found 3 gaps but missed clip CRUD. The v006-v007 audit caught the transition API gap (same pattern) — showing the methodology is inconsistent.

**Scope:** auto-dev-mcp wiring audit prompt/process.

### 2. Version Design: Explicit Deferral Section

**Problem:** When a version delivers a read-only frontend for endpoints that support full CRUD, the gap is invisible unless someone manually compares the API spec to the GUI spec.

**Change:** Add a "Deferred Work" section to VERSION_DESIGN.md templates. When designing a version that delivers a subset of a capability (e.g., read-only clips when CRUD exists), explicitly list what is deferred and create backlog items for the deferred parts before execution begins.

**Evidence:** v005's VERSION_DESIGN.md has no deferral section. BL-035's acceptance criteria perfectly matched the Phase 1 scope, but nothing tracked the remaining CRUD controls.

**Scope:** auto-dev-mcp version design template.

### 3. Retrospective: "Backend Capabilities Without GUI" Check

**Problem:** Retrospectives compare delivered vs planned. They don't compare backend capabilities vs frontend capabilities.

**Change:** Add a retrospective check that lists backend write endpoints introduced or existing, and flags any without GUI controls. This catches the "backend is ready but frontend doesn't expose it" pattern.

**Evidence:** The v005 retrospective listed 11 technical debt items and 15 deliverables. None mentioned the clip CRUD gap. The v003 retrospective delivered full clip CRUD API but naturally didn't mention GUI (no GUI existed yet). No subsequent retrospective picked up the gap.

**Scope:** auto-dev-mcp retrospective process.

### 4. Backlog Hygiene: Companion Items for Phased Work

**Problem:** When a capability is split across phases (API in Phase 1, GUI in Phase 3), only the first phase's work gets a backlog item. The second phase's work relies on milestone definitions in design docs, which are not actively tracked.

**Change:** When a backlog item delivers a partial capability (e.g., read-only display for a CRUD-capable resource), create a companion backlog item for the remaining work at design time, tagged with the target phase. This makes deferred work visible in the backlog immediately.

**Evidence:** BL-035 (project manager) was created 2026-02-08. BL-075 (clip CRUD GUI) was not created until 2026-02-23 — 15 days later, and only after a separate exploration discovered the gap.

**Scope:** auto-dev-mcp version design process.

---

## Impact Assessment

The clip management gap is the most visible instance of a **systematic pattern**: backend capabilities delivered without corresponding GUI surfaces. Other instances:

| Gap | Backend Ready Since | GUI Backlog Created | Delay |
|-----|-------------------|-------------------|-------|
| Clip CRUD controls | v003 (2026-02-08) | BL-075 (2026-02-23) | 15 days |
| Transition GUI | v007 (2026-02-19) | BL-066 (2026-02-21) | 2 days |
| WebSocket broadcasts | v005 (2026-02-09) | Fixed in v009 | ~13 days |

The pattern suggests the process reliably delivers backend and frontend independently but lacks a systematic cross-check between them.
