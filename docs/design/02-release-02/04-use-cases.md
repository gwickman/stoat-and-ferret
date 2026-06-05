# Release 2 — Use Cases (testable)

Every Release 2 capability traces to a use case here, and every use case is written so its outcomes are **verifiable** — by the QC pass (auto), chatbot-driven testing, browser UAT, or (where unavoidable) human review. Verification method is tagged per acceptance criterion:

- **QC** — automated assertion from the QC/compliance pass (Subsystem 2)
- **API/Unit** — automated unit/contract test
- **CHAT** — chatbot-driven scenario (natural-language → API → assert)
- **UAT** — browser UAT journey (Playwright)
- **HUMAN** — perceptual; requires Tier 2 headed review

See [07-test-strategy.md](07-test-strategy.md) for how each method runs and [09-traceability-matrix.md](09-traceability-matrix.md) for the full matrix.

---

## UC-MEDIA-MPS-001 — Produce a mental-performance session (primary)

**Primary actor:** Operator (producer). **Level:** user goal.
**Goal:** author → edit → master → deliver a guided audio-visual mental-performance session (voice + ambience + entrainment tones + optional synchronized visual), structured Induction → Deepening → Suggestion → Emergence, delivered as a loudness-compliant master in all required formats.

**Preconditions:** source media available; section structure defined; delivery requirements (formats, loudness target, visual-required?) known.

### Main success scenario
1. Establish production with technical baseline + labelled sections → labelled Induction/Deepening/Suggestion/Emergence regions exist.
2. Ingest all source media → all material usable in the production.
3. Assemble best spoken material into one continuous narration → gap-free narration track.
4. Clean narration (noise, breaths, harsh/popping) → clear, artifact-free voice.
5. Adjust pacing + tonal character → soothing cadence, warm tone, no distortion.
6. Arrange/trim layers with smooth section transitions → aligned layers, seamless transitions.
7. Place voice in a spatial field → voice perceived in defined space, optionally drifting.
8. Layer continuous ambience + entrainment tones → seamless beds; tones present and varying.
9. Background recedes under voice → automatic ducking.
10. Shape overall level/tonal arc → intentional rise-and-fall per section.
11. (Optional) Synchronized visual track → calming imagery, paced cues, on-screen text.
12. Verify against reference + intent → balanced, consistent, defect-free.
13. Produce deliverables in all formats with embedded labelling → normalized, labelled, valid files.

### Acceptance criteria (verifiable outcomes)

| OC | Outcome | Verify | Maps to |
|----|---------|--------|---------|
| OC-1 | Four labelled sections in order: Induction, Deepening, Suggestion, Emergence | QC / API | R-P03 |
| OC-2 | Narration continuous — no unintended gaps/dropouts/audible edits | QC (gaps) + HUMAN (edit audibility) | R-A01, R-Q03 |
| OC-3 | No perceptible noise/breaths/clicks/sibilance/pops | HUMAN (+ `astats` flat-factor signal) | R-A01, R-A02 |
| OC-4 | Cadence slowed vs raw, no pitch distortion | QC (duration) + HUMAN (pitch quality) | R-A03 |
| OC-5 | Smooth transitions, no abrupt cuts/pops | API (xfade present) + HUMAN | R-E02 |
| OC-6 | Voice in perceptible spatial field; movement gradual | QC (phase correlation) | R-S01, R-S02 |
| OC-7 | Ambience loops seamlessly, no audible seam | QC (boundary compare) | R-S04, R-Q04 |
| OC-8 | Entrainment tones present and changing across session | QC (`aspectralstats`) | R-S05, R-Q05 |
| OC-9 | Background reduces under voice, recovers when voice pauses | QC (level analysis) | R-S06, R-Q06 |
| OC-10 | Intentional intensity arc (low at deepening, peak at suggestion, gentle at emergence) | QC (per-section LUFS ordering) | R-M01, R-Q07 |
| OC-11 | Final master meets loudness target, within true-peak ceiling | QC (`ebur128`) | R-M05, R-Q01 |
| OC-12 | No clipping/distortion/unintended silence anywhere | QC (`astats` + `silencedetect`) | R-Q02, R-Q03 |
| OC-13 | Visual track frame-accurately synchronized | QC (offset probe) | R-G01, R-Q09 |
| OC-14 | Visual transitions/motion smooth; text legible+timed; styling consistent | API (timing) + HUMAN (legibility) | R-G01, R-G03, R-V01 |
| OC-15 | Deliverables produced in every required format | QC / API | R-D01, R-D03 |
| OC-16 | Each deliverable carries embedded section labels + identifying metadata | QC (`ffprobe`) | R-D04, R-Q11 |
| OC-17 | All deliverables play correctly start-to-finish on a standard player | QC (null-decode) | R-Q10 |

**14 of 17 outcomes are fully machine-verifiable.** OC-3 is HUMAN-only; OC-2/4/5/14 have HUMAN sub-parts. This ratio is the justification for building the QC pass early.

### Alternate / exception flows
- **A1** narration segment unusable, no alt take → re-record/request source; OC-2 still holds.
- **A2** ambience won't loop seamlessly → choose alt bed / reshape loop boundary; OC-7 satisfied.
- **A3** master fails loudness/peak → re-shape levels, re-master; OC-11/12 satisfied on re-check (retained editable state).
- **A4** visual track not required → skip steps 11; OC-13/14 marked N/A; audio outcomes still apply.
- **A5** a delivery format fails to produce/play → correct export settings, re-produce; OC-15/17 satisfied on re-check.

**Postcondition on failure:** production retained in editable state; Operator addresses failing OC and re-verifies without restarting.

---

## UC-AV-001 — Author, edit & master a guided session (workflow view, secondary)

Same domain as UC-MEDIA-MPS-001 but expressed as the producer's **workflow** rather than outcomes. It exercises the same capabilities and is useful for chatbot-driven scenario authoring (the chatbot follows the workflow steps; the QC pass and API assertions verify the outcomes above).

**Workflow stages:** project setup & ingest → (voice already captured upstream) → multitrack editing & arrangement → spatial/immersive audio → sound-design layering → automation & dynamics → optional video/visual track → review, export & delivery.

> **Scope note:** stages requiring realtime capture (multi-take recording, punch-in/out, take comping) and DAW-style buses are **out of scope** (see roadmap). snf ingests a finished voice track; everything from arrangement → mastering → verified delivery is in scope.

---

## Capability use cases (focused, per-feature testable scenarios)

Small use cases that pin specific Release 2 capabilities to assertions. Each is a chatbot-driven scenario + unit/contract + (where GUI-facing) UAT.

### UC-CAP-REV — Reverse a clip
**Goal:** play a selected clip backwards (video + audio).
- **AC-REV-1** Reversed output has frames in reverse order vs source — API/Unit (frame-hash compare on a short fixture).
- **AC-REV-2** Reversed audio is the time-reverse of source — QC (correlation against reversed reference).
- **AC-REV-3** Effect rejects clips longer than the configured buffer limit with a structured error — API/Unit.
- **AC-REV-4** Operator can apply Reverse from the effect panel and see it in preview — UAT/CHAT.

### UC-CAP-VSPD — Variable-speed / time-remap
**Goal:** accelerate/decelerate a clip along a curve within a single clip.
- **AC-VSPD-1** Constant speed unchanged from Release 1 behaviour — API/Unit (regression).
- **AC-VSPD-2** A 2-segment speed curve yields measured output duration within tolerance of the integral — QC (duration).
- **AC-VSPD-3** Audio stays pitch-preserved across the curve — HUMAN + QC (spectral centroid stability).
- **AC-VSPD-4** Operator draws a speed curve and previews smooth ramp — UAT.

### UC-CAP-SPLIT — Clip split / razor + range-bound effect
**Goal:** cut a clip into segments and apply an effect to only one segment / frame range.
- **AC-SPLIT-1** Splitting a clip at t produces two clips with adjacent in/out points and identical total coverage — API/Unit.
- **AC-SPLIT-2** An effect applied to frames X–Y is active only within [X,Y] (verified via the generated `enable` expression and rendered probe) — API/Unit + QC.
- **AC-SPLIT-3** Operator razors a clip and applies an effect to one side — UAT/CHAT.

### UC-CAP-GRADE — Color grade / LUT
**Goal:** apply a consistent calming color palette via LUT.
- **AC-GRADE-1** Applying a 3D LUT transforms color per the LUT (sampled pixels match expected) — API/Unit.
- **AC-GRADE-2** Same LUT across multiple clips yields consistent styling — QC (per-clip color-stat consistency) + HUMAN.
- **AC-GRADE-3** Operator selects a LUT and sees graded preview — UAT.

### UC-CAP-MASTER — Loudness-compliant master + delivery profile
**Goal:** export a master that meets a loudness target and true-peak ceiling, in all profile formats, labelled.
- **AC-MASTER-1** Export against a delivery profile produces every declared output — QC/API.
- **AC-MASTER-2** Each audio output measures within ±0.5 LU of target and ≤ ceiling true-peak — QC (`ebur128`).
- **AC-MASTER-3** No clipping / unintended silence — QC.
- **AC-MASTER-4** Chapters/metadata embedded from markers — QC (`ffprobe`).
- **AC-MASTER-5** All outputs decode end-to-end — QC (null-decode).
- **AC-MASTER-6** A failing profile keeps the project editable and re-export re-verifies — CHAT (drive A3/A5).

### UC-CAP-TONE — Entrainment tone synthesis
**Goal:** generate an isochronic/binaural tone track with frequency automation.
- **AC-TONE-1** A generated tone clip has energy at the target frequency — QC (`aspectralstats`).
- **AC-TONE-2** Automated frequency sweep is reflected in the spectrum over time — QC.
- **AC-TONE-3** Binaural-beat mode produces the specified L/R frequency offset — QC.
- **AC-TONE-4** Operator adds a tone generator track and sets a frequency envelope — UAT/CHAT.

---

## How these use cases drive the release

- UC-MEDIA-MPS-001 is the **acceptance vehicle** for the whole release: when its 17 outcomes pass (14 auto + Tier-2 human for the rest), the release goal is met.
- The capability use cases are the **per-version vehicles**: each Release 2 version closes against the capability use cases it implements, all of which are chatbot- and (where relevant) UAT-driven.
