# RCA Synthesis: Critical Review and Remediation Plan

## Executive Summary

Six RCAs were reviewed covering: blocking ffprobe (rca-ffprobe-blocking), missing progress reporting (rca-no-progress), job cancellation omission (rca-no-cancellation), clip management GUI gaps (rca-clip-management), missing browse button (rca-no-browse-button), and missing .env.example (rca-no-env-example).

**Strong findings (4 of 6):** The ffprobe-blocking, no-progress, no-cancellation, and clip-management RCAs are well-evidenced and identify genuine systemic process gaps. Their evidence trails are thorough, tracing issues through design docs, backlog items, implementation, and retrospectives.

**Weak findings (2 of 6):** The browse-button and .env.example RCAs describe real gaps but overstate the process failure. Both are specification omissions — features that were never designed in the first place — rather than process breakdowns where designed features were lost.

## Cross-Cutting Patterns

Three systemic patterns emerge across the strong RCAs:

1. **Descoped/deferred work not tracked as backlog items.** Found in rca-no-cancellation (explicit descoping without BL item), rca-clip-management (implicit deferral via phasing), and rca-no-progress (backend stub without wiring). This is the single highest-impact process gap.

2. **Completion reports verify schema existence, not behavioral wiring.** Found in rca-no-progress (progress field existed but always null) and rca-no-cancellation (cancel button existed but disabled). The "schema without wiring" anti-pattern has occurred at least 3 times (progress, cancellation, WebSocket broadcasts BL-065).

3. **Retrospectives compare delivered vs. planned, not delivered vs. possible.** No retrospective across 9 versions flagged any of these gaps. Retrospectives confirm that acceptance criteria passed but don't ask whether the acceptance criteria were sufficient.

## Remediation Strategy

The recommendations cluster into three tiers:

**Tier 1 — High impact, low effort (do first):**
- Create IMPACT_ASSESSMENT.md with async-safety and .env.example checks
- Add "deferred work tracking" convention to version design process
- Save learnings about "schema without wiring" and "descoped without backlog"

**Tier 2 — Medium impact, medium effort:**
- Custom blocking-in-async lint check (CI script)
- Event-loop responsiveness integration test
- Wiring audit methodology expansion to cover "absent wiring"

**Tier 3 — Lower impact or already partially addressed:**
- UX specification checklists (nice-to-have but won't prevent novel omissions)
- API spec example fixes (local improvement, not systemic)
- ASYNC ruff rules (limited coverage for asyncio)

## What's Already Addressed

All concrete code bugs have backlog items: BL-072 (ffprobe, P0), BL-073 (progress, P1), BL-074 (cancellation, P1), BL-075 (clip CRUD, P1), BL-070 (browse button, P2), BL-071 (.env.example, P2). No process-level changes have been made yet.

## Output Files

- [critical-review.md](./critical-review.md) — Issue-by-issue critique of each RCA
- [remediation-plan.md](./remediation-plan.md) — Actionable plan grouped by target
- [process-analysis.md](./process-analysis.md) — How IMPACT_ASSESSMENT.md, VERSION_CLOSURE.md, and the design/retro scripts work
