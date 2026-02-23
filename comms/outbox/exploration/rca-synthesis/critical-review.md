# Critical Review: RCA-by-RCA Assessment

## 1. rca-ffprobe-blocking — STRONG

**Evidence quality: Excellent.** The evidence trail traces the issue through v002 (sync creation), v003 (async caller introduced), v004 (research identified it, remediation skipped it), to user discovery. File paths, line numbers, and completion report quotes are specific and verifiable.

**Conclusion validity: Sound.** The root cause chain is accurate: no lint rule, no integration test, known issue not tracked as backlog. The v004 research finding at `codebase-patterns.md:100` that was not acted on is the strongest evidence of process failure.

**Recommendation critique:**

| # | Recommendation | Verdict | Notes |
|---|---------------|---------|-------|
| 1 | Add ASYNC ruff rules | **Weak** | RCA itself acknowledges these rules target trio/anyio, not raw asyncio. Would not have caught this specific bug. Low value. |
| 2 | Custom blocking-in-async lint check | **Strong** | Direct prevention. A grep-based CI check is simple and catches the exact pattern. |
| 3 | Event-loop responsiveness integration test | **Strong** | The test that would have caught this. But needs care — testing real subprocess blocking requires real files or simulated delays, not mocks. |
| 4 | Async safety in design review | **Moderate** | Good principle, but "add a checklist item" recommendations have a poor track record unless embedded in a template that's mechanically enforced. |
| 5 | Backlog items from research findings | **Strong** | The core process gap. v004 research documented the issue; no BL item was created. This is the most impactful recommendation across all 6 RCAs. |

**Missed alternative:** The RCA doesn't mention `asyncio.to_thread()` as the simplest fix for the actual bug — wrapping `subprocess.run()` in `asyncio.to_thread()` is a one-line change. The lint check would flag the issue; the fix is trivial.

## 2. rca-no-progress — STRONG

**Evidence quality: Excellent.** The evidence trail documents the gap across v004 (backend) and v005 (frontend) with specific file paths and line numbers. The false PASS on FR-2 in v004 completion report is particularly damning evidence.

**Conclusion validity: Sound.** The "schema without wiring" pattern is real and recurring (progress, WebSocket broadcasts BL-065). The cross-version tracing gap is well-identified.

**Recommendation critique:**

| # | Recommendation | Verdict | Notes |
|---|---------------|---------|-------|
| 1 | End-to-end wiring check in completion reports | **Strong** | Directly addresses the false PASS problem. But specifying "evidence that data flows end-to-end" is vague. Needs a concrete mechanism — e.g., a test that asserts progress > 0 during a running job. |
| 2 | Prior-version dependency verification in design | **Strong** | Addresses the cross-version gap. When v005 designed the frontend, it should have verified v004's progress actually worked. |
| 3 | Save learning about "schema without wiring" | **Strong** | This is the third instance. A learning is overdue. |
| 4 | Fix API spec examples | **Moderate** | Local fix. Showing `progress: 0.45` instead of `null` in the running example is correct but won't prevent future instances of the pattern. |

**Over-engineering concern:** Recommendation #2 (prior-version dependency verification) sounds good but is hard to operationalize. "Run a quick smoke test to verify each assumed behavior" during design phase requires a running system, which may not be practical. A more realistic version: the design phase should list cross-version behavioral assumptions and the implementation plan should include a verification test.

## 3. rca-no-cancellation — STRONG

**Evidence quality: Excellent.** The evidence trail traces cancellation through 6 design-doc locations, the explicit descoping at `requirements.md:32`, both retrospective acknowledgments, and the dead cancel button in ScanModal.tsx. Chronology is thorough and well-sourced.

**Conclusion validity: Sound.** The three-step failure chain (underspecified BL-027 → descoped without backlog → retrospective dead end) is clearly evidenced and correctly identified.

**Recommendation critique:**

| # | Recommendation | Verdict | Notes |
|---|---------------|---------|-------|
| R1 | Track descoped items as backlog | **Strong** | Core fix. Directly prevents the gap. The recommendation even specifies the file to modify (`007-document-drafts.md`). |
| R2 | Retrospective debt ingestion | **Strong** | Closes the feedback loop. Both retrospectives identified the gap but didn't create BL items. Adding to `003-backlog-verification.md` is the right location. |
| R3 | Design-doc traceability | **Moderate** | Useful but complex. Verifying that BL items cover all sub-items of design-doc milestones requires the agent to parse milestone definitions and map them to acceptance criteria. May be over-engineered for the payoff. |
| R4 | GUI-backend API validation | **Moderate** | Good principle. The dead cancel button is a clear UX problem. But "require acceptance criteria verifying backend endpoints exist" is a convention that depends on the design agent remembering to apply it. |
| R5 | Split Out of Scope sections | **Weak** | Cosmetic improvement. The distinction between "deferred" and "not applicable" is clear in context and doesn't need a template change. R1 (track descoped as backlog) is sufficient. |

**Inconsistency noted:** R1 says to add the step to `007-document-drafts.md`, but `007-document-drafts.md` is the document-creation step that runs after logical design. The descoping decision happens during requirements writing, which is also in `007-document-drafts.md` step 5. The recommendation is correctly placed.

## 4. rca-clip-management — MODERATE

**Evidence quality: Good.** The evidence trail is thorough but the root cause is weaker than the other strong RCAs. The clip CRUD gap is fundamentally a design phasing decision — Phase 1 was explicitly read-only, Phase 3 was interactive. The RCA correctly identifies this but then argues the phasing was "implicit" which is debatable given the wireframes clearly showed read-only tables.

**Conclusion validity: Partially sound.** The gap is real (backend CRUD existed since v003 with no GUI until BL-075 created 15 days later). But characterizing it as the same class of failure as the progress or cancellation gaps overstates the case. Those were features marked as delivered but non-functional. Clip CRUD was never claimed to be delivered.

**Recommendation critique:**

| # | Recommendation | Verdict | Notes |
|---|---------------|---------|-------|
| 1 | Wiring audit: add "uncovered endpoints" check | **Moderate** | Has value — systematically listing write endpoints without GUI surfaces would catch this pattern. But the v006-v007 audit already caught the transition API gap (same pattern), suggesting the process is self-correcting over time. |
| 2 | Version design: explicit deferral section | **Strong** | Overlaps with rca-no-cancellation R1. A single "deferred work" tracking convention addresses both RCAs. |
| 3 | Retrospective: "backend capabilities without GUI" check | **Weak** | Too specific. This is a subset of the general "wiring audit" concept. Adding a separate retrospective check for this one pattern is over-engineering. |
| 4 | Companion BL items for phased work | **Moderate** | Overlaps with the deferral tracking convention. If descoped items are tracked as backlog (rca-no-cancellation R1), this is redundant. |

**Simpler alternative:** The wiring audit methodology already exists and caught the transition API gap. Extending it to cover "absent wiring" (not just broken wiring) is the single change needed, rather than 4 separate recommendations.

## 5. rca-no-browse-button — WEAK

**Evidence quality: Good.** The evidence trail correctly traces the specification chain and demonstrates that the browse button was never specified.

**Conclusion validity: Overstated.** The RCA concludes this is a "process gap" but it's really a specification gap — nobody thought to include a folder picker in the design. This is fundamentally different from the progress/cancellation/ffprobe cases where features were designed, partially built, and then lost. A folder picker is a UX refinement that was never part of the vision.

**Recommendation critique:**

| # | Recommendation | Verdict | Notes |
|---|---------------|---------|-------|
| 1 | Modal/dialog wireframes in design docs | **Weak** | Reasonable for new projects but not actionable retroactively. The design docs exist and aren't being rewritten. |
| 2 | UX-specific acceptance criteria | **Weak** | "Specify the input mechanism, not just the outcome" is a good principle but impossible to enforce exhaustively. You can't anticipate every UX pattern a user might expect. |
| 3 | Standard UX patterns in implementation plans | **Weak** | Same issue — this is asking the design agent to think of things nobody thought of. |
| 4 | UX checklist for GUI themes | **Moderate** | The most actionable recommendation. A short checklist ("Does every user input have an appropriate input mechanism?") could be added to the IMPACT_ASSESSMENT.md for stoat-and-ferret. |
| 5 | UX gap detection in retrospectives | **Weak** | Retrospectives can't catch gaps that nobody has identified as gaps. |

**Bottom line:** The browse button is a feature request (BL-070, P2), not a process failure. The RCA's recommendations are mostly UX design principles rather than actionable process changes. The one useful outcome: if a UX checklist existed in IMPACT_ASSESSMENT.md, it might prompt the design agent to consider standard interaction patterns.

## 6. rca-no-env-example — WEAK

**Evidence quality: Good.** The evidence trail correctly documents that .env.example was never a deliverable across 9 versions.

**Conclusion validity: Overstated.** Like the browse button, this is something that was never specified, not something that was lost. The project has sensible defaults for all settings — a developer can run the application with zero configuration. The `.env.example` is a convenience artifact, not a critical gap. Calling it a "systematic blind spot in the design-to-implementation pipeline" elevates a minor DX improvement to a systemic failure.

**Recommendation critique:**

| # | Recommendation | Verdict | Notes |
|---|---------------|---------|-------|
| 1 | Create .env.example alongside Settings class | **Moderate** | Good practice for the future, but BL-071 already tracks this as a P2. |
| 2 | Developer onboarding in version design checklists | **Weak** | Over-engineering. This project has 1 developer. |
| 3 | Retrospective question for documentation gaps | **Weak** | Adding a retrospective question for every possible documentation artifact is unbounded. |
| 4 | Settings consumption and documentation lint | **Moderate** | A test that verifies .env.example covers all Settings fields has value — but only after BL-071 is implemented. |
| 5 | Distinguish "design exists" from "wired and documented" | **Moderate** | Good principle (overlaps with rca-no-progress "schema without wiring") but the documentation dimension adds little for a single-developer project. |

**Simpler alternative:** Add a single check to IMPACT_ASSESSMENT.md: "If this version adds Settings fields, verify .env.example is updated." That's the entire fix needed.
