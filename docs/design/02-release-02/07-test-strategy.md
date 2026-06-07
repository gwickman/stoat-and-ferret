# Release 2 — Test Strategy (first-class citizen)

Testing is **not a closing phase** in Release 2. The full regression suite, **chatbot-driven testing**, and **browser-running UAT** are built alongside every capability, in the same version. No capability merges without (a) its automated tests, (b) at least one chatbot-driven scenario, (c) a UAT journey if it is GUI-facing, and (d) a traceability entry. The QC/compliance pass is what lets most acceptance criteria be machine-asserted.

This document extends — does not replace — the existing harness designs:
- [`../chatbot-driven-testing/`](../chatbot-driven-testing/README.md)
- [`../uat_test/`](../uat_test/00-index.md)
- [`../sample_project/`](../sample_project/README.md), [`../smoke_test/`](../smoke_test/readme.txt)

---

## The testing pyramid for Release 2

```
            ┌───────────────────────────────┐
            │  Tier 2 UAT (headed, human)   │  perceptual OCs (OC-3, audibility/legibility)
            ├───────────────────────────────┤
            │  Tier 1 UAT (headless browser)│  GUI journeys, every version closure
            ├───────────────────────────────┤
            │  Chatbot-driven scenarios     │  NL → API → QC assertions, per use case
            ├───────────────────────────────┤
            │  QC / compliance assertions   │  ← the new layer: OC-* as machine checks
            ├───────────────────────────────┤
            │  Contract tests (real FFmpeg) │  every generated filter/command runs
            ├───────────────────────────────┤
            │  Unit + property (Rust/Python)│  builders, keyframe compiler, parsers
            └───────────────────────────────┘
```

---

## 1. Unit & property tests

- **Keyframe→expression compiler** (Rust proptest): never panics; monotonic-time invariant; compiled value at each keyframe equals the keyframe value; bounded output.
- **QC measurement parsers** (Rust proptest): parse arbitrary/garbled FFmpeg stderr/JSON without panic; typed measurements within plausible ranges.
- Every new **effect builder**: deterministic output, sanitisation preserved, schema-valid params.
- Python: registry validation, delivery-profile validation, marker non-overlap, range-window math.

## 2. Contract tests (real FFmpeg)

Every new effect and the QC checks run against real FFmpeg on short fixtures (CI tier that has FFmpeg). A generated filter string that FFmpeg rejects fails the build. This is the Release 1 contract pattern extended to all Release 2 filters. Recording fakes (`RecordingFFmpegExecutor`) capture commands for fast unit-level verification where real FFmpeg is unavailable.

## 3. QC / compliance assertions — the bridge layer

The QC pass (Subsystem 2) is **both a product feature and the test oracle**. Each machine-verifiable outcome (OC-*) maps to a QC check id; tests assert on the QC report:

| OC | QC check id | Pass condition |
|----|-------------|----------------|
| OC-1 | `sections_ordered` | 4 ordered named regions |
| OC-2 | `unintended_silence` | no gaps in voice bus |
| OC-7 | `loop_seam` | boundary delta < threshold |
| OC-8 | `tone_presence` | energy at target freq, varies over time |
| OC-9 | `ducking` | bg level drops ≥ X dB under voice |
| OC-10 | `section_arc` | per-section LUFS ordering matches intent |
| OC-11 | `loudness_integrated` + `true_peak` | within ±0.5 LU; ≤ ceiling |
| OC-12 | `clipping` + `unintended_silence` | 0 clipped; no unintended silence |
| OC-13 | `av_sync` | offset within 1 frame |
| OC-16 | `chapters_present` | chapter count == section count |
| OC-17 | `decode_integrity` | null-decode reports no errors |

Tests that assert on these run against rendered fixtures produced from the seeded sample project — deterministic, FFmpeg-backed, no human in the loop.

## 4. Chatbot-driven testing

Each use case and capability use case (see [04-use-cases.md](04-use-cases.md)) gets a chatbot-driven scenario: the chatbot is given a natural-language production brief, drives the REST API to build the session, and the harness asserts the resulting QC report + API state.

Example scenario shape (UC-CAP-MASTER):
1. Brief: "Master this project to −16 LUFS, true-peak −1 dBTP, export WAV + MP3 + MP4 with chapters."
2. Chatbot: creates delivery profile, starts render with `run_qc`.
3. Harness asserts: QC `overall == pass`; loudness within tolerance; chapter count == markers; all outputs decode.
4. Negative path (A3): brief with an unreachable target → assert QC fails, project remains editable, re-master succeeds.

Scenarios live alongside the existing `chatbot-driven-testing/` catalog and are run in CI (mocked-LLM deterministic mode) and periodically against a live model.

## 5. Browser UAT (Playwright, two-tier)

Extends the existing UAT harness ([`../uat_test/`](../uat_test/00-index.md)). New **user journeys** added to the headless Tier-1 set that runs on **every version closure**:

| Journey | Covers |
|---------|--------|
| J-Automation | Draw a volume/pan automation curve; verify expr preview + rendered effect |
| J-Markers | Create the 4 session regions; verify chapters in export |
| J-Mastering | Configure delivery profile; export; read QC results panel (all green) |
| J-QC-Fail | Force a loudness failure; verify QC panel red + re-master flow |
| J-Reverse-Split | Razor a clip, reverse one segment, verify in preview |
| J-Grade | Apply a LUT; verify graded preview + consistency |

- **Tier 1 (headless):** automatic on version closure; structured JSON + markdown + screenshots; flags failures.
- **Tier 2 (headed):** human review for perceptual outcomes (OC-3 artifact-freeness, OC-4 pitch quality, OC-14 legibility) and before the release sign-off. These are the criteria the machine cannot assert.

## 6. Regression suite

- The full Release 1 suite (smoke, E2E, contract, parity, golden scenarios) stays green; Release 2 adds to it, never weakens coverage thresholds (Rust >90%, Python >80%).
- **Golden render fixtures:** a small set of rendered masters with known QC reports; regression detects drift in filter generation or QC measurement.
- **No-silent-regression rule:** any capped/sampled coverage in a test run is logged, not hidden.

---

## CI tiers (Release 2)

| Tier | Runs | Contents |
|------|------|----------|
| PR fast | every PR | unit + property + recording-fake contract + lint/type |
| PR full | every PR | + real-FFmpeg contract + QC-assertion tests + chatbot scenarios (mocked LLM) |
| Nightly | scheduled | + golden render/QC regression + chatbot scenarios (live LLM) |
| Version closure | per version | + Tier-1 headless UAT (all journeys) |
| Release sign-off | per release | + Tier-2 headed UAT (perceptual OCs) + UC-MEDIA-MPS-001 full acceptance |

---

## Definition of done (per capability)

A Release 2 capability is done when:
1. Unit + property tests pass (Rust/Python).
2. Contract test against real FFmpeg passes.
3. Its outcomes are asserted via the QC pass **or** explicitly marked HUMAN with a Tier-2 journey.
4. At least one chatbot-driven scenario drives it end-to-end.
5. If GUI-facing, a Tier-1 UAT journey covers it.
6. A row exists in [09-traceability-matrix.md](09-traceability-matrix.md) linking capability → use case → OC → test.
7. The regression suite is green.
