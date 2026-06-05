# Release 2 — Traceability Matrix

Every capability links to a requirement, a use case, a verifiable outcome, and the test(s) that prove it. This is the artifact that enforces "every release testable as we build": a capability is not done until its row is complete (see [07-test-strategy.md](07-test-strategy.md) Definition of Done).

**Test method legend:** U=unit/property · C=contract (real FFmpeg) · QC=QC assertion · CH=chatbot scenario · UAT=browser journey · H=human (Tier 2).

---

## Outcome → capability → test (UC-MEDIA-MPS-001)

| OC | Requirement(s) | Backlog # | QC check / test | Methods |
|----|----------------|-----------|-----------------|---------|
| OC-1 | R-P03 | 2, 8 | `sections_ordered` | U, QC, CH |
| OC-2 | R-A01, R-Q03 | 5, 6 | `unintended_silence` | QC, H |
| OC-3 | R-A01, R-A02 | (repair) | `astats` signal + review | H |
| OC-4 | R-A03 | 24 | duration + spectral centroid | QC, H |
| OC-5 | R-E02 | (R1) | xfade present + review | U, H |
| OC-6 | R-S01, R-S02 | 15 | `av`/phase correlation | QC, UAT |
| OC-7 | R-S04, R-Q04 | 18 | `loop_seam` | QC, CH |
| OC-8 | R-S05, R-Q05 | 17 | `tone_presence` | QC, UAT |
| OC-9 | R-S06, R-Q06 | 19 | `ducking` | QC |
| OC-10 | R-M01, R-Q07 | 11, 9 | `section_arc` | QC |
| OC-11 | R-M05, R-Q01 | 14, 6 | `loudness_integrated`, `true_peak` | QC, CH |
| OC-12 | R-Q02, R-Q03 | 13, 6 | `clipping`, `unintended_silence` | QC |
| OC-13 | R-G01, R-Q09 | 31 | `av_sync` | QC, UAT |
| OC-14 | R-G01, R-G03, R-V01 | 26, 31 | timing + legibility review | U, H |
| OC-15 | R-D01, R-D03 | 7 | output enumeration | QC, API |
| OC-16 | R-D04, R-Q11 | 8 | `chapters_present` | QC |
| OC-17 | R-Q10 | 6 | `decode_integrity` | QC |

**Auto-coverage:** 14/17 outcomes machine-verified; OC-3 human-only; OC-2/4/5/14 human sub-parts (Tier-2 journeys).

---

## Capability use case → tests

| Use case | Requirement(s) | Backlog # | Acceptance criteria | Methods |
|----------|----------------|-----------|---------------------|---------|
| UC-CAP-REV (reverse) | R-E03 | 21 | AC-REV-1..4 | U, QC, UAT, CH |
| UC-CAP-VSPD (variable speed) | R-T01, R-T02 | 24 | AC-VSPD-1..4 | U, QC, H, UAT |
| UC-CAP-SPLIT (split + range gate) | R-E04, R-E05 | 22, 23 | AC-SPLIT-1..3 | U, QC, UAT, CH |
| UC-CAP-GRADE (LUT) | R-V01 | 26 | AC-GRADE-1..3 | U, QC, UAT, H |
| UC-CAP-MASTER (delivery profile) | R-D01, R-M05, R-Q01/02/10/11 | 7, 14 | AC-MASTER-1..6 | QC, CH, API |
| UC-CAP-TONE (tone synth) | R-S05 | 17 | AC-TONE-1..4 | QC, UAT, CH |

---

## Requirement → backlog → version (coverage check)

| Requirement | Backlog # | Version | Notes |
|-------------|-----------|---------|-------|
| R-X01 keyframe compiler | 1 | v073 | enabler, build first |
| R-P03 markers | 2 | v073 | |
| R-Q01…R-Q11 QC | 5, 6 | v074 | the test oracle |
| R-D01 delivery profiles | 7 | v074 | |
| R-D04 chapters/metadata | 8 | v074 | |
| R-M01 vol automation | 11 | v075 | needs R-X01 |
| R-M02 parametric EQ | 10 | v075 | |
| R-M03 multiband comp | 12 | v075 | |
| R-M04 limiter | 13 | v075 | |
| R-M05 LUFS normalize | 14 | v075 | |
| R-S01/02 pan + auto-pan | 15 | v076 | |
| R-S03 convolution reverb | 16 | v076 | |
| R-S05 tone synthesis | 17 | v076 | needs R-X01 |
| R-S04 loopable beds | 18 | v076 | |
| R-S06/07 ducking + sub | 19 | v076 | |
| R-V05 generators | 20, 30 | v076/v078 | generator-clip concept |
| R-E03 reverse | 21 | v077 | |
| R-E04 split/razor | 22 | v077 | |
| R-E05 range gating | 23 | v077 | |
| R-T02 variable speed | 24 | v077 | needs R-X01 |
| R-T03 framerate convert | 25 | v077 | |
| R-V01 color/LUT | 26 | v078 | |
| R-V02 blur/sharpen | 27 | v078 | keyframable → R-X01 |
| R-V03 keying + blend | 28 | v078 | |
| R-V04 optical distortion | 29 | v078 | |
| R-G01 keyframed opacity/scale | 31 | v078 | needs R-X01 |

**Deferred (no Release 2 backlog, tracked as out of scope):** R-A04 pitch/formant (candidate for v07x stretch), R-S08 Ambisonic, R-E06 ripple/grouping, R-E07 buses, R-V06 masking, R-G05 MOGRT, R-D05 A/B monitoring, plus all capture/comping. Listed in [01-roadmap.md](01-roadmap.md) "Out of scope."

> Note: R-A01 (noise reduction), R-A02 (de-ess/de-plosive), R-A03 (time-stretch) underpin OC-2/3/4 and should be scheduled in v075–v076 alongside mastering/sound-design (folded into the repair/voice items); add explicit backlog rows when those versions are designed in detail.

---

## How to use this matrix

- **Adding a capability:** add its requirement (03), a use case or AC (04), a backlog item with test ACs (08), and a row here. If any cell is empty, it is not done.
- **Closing a version:** every backlog item in that version has all its method columns satisfied and the regression suite is green.
- **Release sign-off:** all 17 OCs of UC-MEDIA-MPS-001 pass (14 auto + Tier-2 human), and every UC-CAP-* scenario is green.
