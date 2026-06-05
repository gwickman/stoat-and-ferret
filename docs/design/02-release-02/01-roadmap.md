# Release 2 — Roadmap

**Project:** stoat-and-ferret — AI-driven video editor (hybrid Python/Rust)
**Release goal:** From "applies effects and renders" to "produces and **proves** a finished, loudness-compliant master," with testing (regression + chatbot-driven + browser UAT) as a first-class citizen built alongside every capability.

---

## Executive summary

Release 2 expands the production surface — primarily audio mastering, immersive sound design, an automation/keyframing layer, and a small set of editing/time primitives — and introduces an **automated quality-control (QC) / compliance verification** capability. The QC pass turns the release's acceptance criteria into pass/fail machine assertions (loudness, true-peak, clipping, silence/gaps, loop-seam, A/V sync, decode integrity, embedded metadata). Because most outcomes are machine-verifiable, the release is testable end-to-end as it is built.

The release is organised into **capability waves** with a clear dependency spine. Testing is not a wave that follows — it is a cross-cutting workstream (Wave T) with deliverables in every version.

---

## Dependency spine

```
Wave 0  Keyframe→Expression Compiler ── Timeline Markers/Regions
            │                                  │
            ▼                                  ▼
Wave 2  Automation curves (vol/EQ/pan)   Wave 1  QC/Compliance pass ── Delivery profiles
            │                                  │            │
            ▼                                  ▼            ▼
Wave 3  Auto-pan, tone-freq sweeps     (verifies every wave's outputs as ACs)
Wave 4  Variable-speed/time-remap
Wave 5  Keyframed opacity/scale
```

- **Build Wave 0 first.** The keyframe→expression compiler converts a large set of "engine-ready" capabilities to done at once (automation, variable speed, auto-pan, tone sweeps, keyframed video). Markers/regions feed both section-aware automation and embedded chapters.
- **Build Wave 1 (QC pass) second.** It is independent of Wave 0, cheap (a handful of FFmpeg analysis filters + ffprobe + a null-decode pass), and it is what makes every other capability *testable* rather than merely present. The QC assertions become the acceptance criteria for the rest of the release.
- Reverse, clip split/razor, and range-bound effect gating (Wave 4) are independent and can land in parallel.

---

## Capability waves

### Wave 0 — Enablers
- [ ] **Keyframe→expression compiler** (Rust pure function): automation nodes (time,value,curve) → FFmpeg `expr` strings (`if(between(t,…))` ramps; linear/exponential/bezier-ease). Reused by volume, EQ, pan, blur radius, tone frequency, opacity, scale.
- [ ] **Timeline markers / regions**: named, ordered regions (e.g. Induction→Deepening→Suggestion→Emergence) that drive section-aware automation and export as chapters/metadata.

### Wave 1 — Verify & deliver (testing-enabling)
- [ ] **QC / compliance verification pass** (post-render measurement → assertions): integrated LUFS + true-peak (`ebur128`/`loudnorm` JSON), clipping/peak (`astats`/`volumedetect`), unintended silence/gaps (`silencedetect`), loop-seam check, tone presence (`aspectralstats`), ducking verification (level analysis), video defects (`blackdetect`/`freezedetect`), A/V sync, decode integrity (`ffmpeg -v error -f null -`), embedded-metadata check (`ffprobe`).
- [ ] **Delivery profiles**: a profile binds format set + codec + loudness target + true-peak ceiling + metadata/chapters; export validates output against the profile and emits a QC report.

### Wave 2 — Mastering
- [ ] Parametric EQ (multi-band, `anequalizer`) + EQ automation
- [ ] Per-track volume/level automation curves
- [ ] Multiband compression (`mcompand`)
- [ ] Mastering limiter (`alimiter`)
- [ ] LUFS normalization + true-peak ceiling (two-pass `loudnorm`)

### Wave 3 — Immersive sound design
- [ ] Stereo/binaural panning (`pan` / `sofalizer`) + automated pan (LFO/keyframed)
- [ ] Convolution reverb with IR asset pack (`afir`)
- [ ] Tone synthesis: isochronic tones / binaural beats with frequency automation (`sine`/`aevalsrc` + keyframe compiler)
- [ ] Loopable ambience beds with seamless loop points (`aloop` + boundary crossfade)
- [ ] Sub-bass grounding layer
- [ ] Sidechain ducking — *carried from R1*, formalised as a registry effect

### Wave 4 — Editing & time
- [ ] **Reverse** clip (video `reverse` + audio `areverse`; whole-segment buffering constraint documented)
- [ ] **Clip split / razor** (segment a clip; each segment carries independent effects/speed/reverse)
- [ ] **Range-bound effect gating** (apply any effect to frames X–Y of a clip; generalise existing `enable` expression)
- [ ] Variable-speed / time-remapping curves (segmented or PTS-integral)
- [ ] Frame-rate conversion (optical-flow / blend interpolation, `minterpolate`)

### Wave 5 — Video FX
- [ ] Color grading / LUTs (`lut3d`/`haldclut`)
- [ ] Blur / sharpen (gaussian/directional, keyframable radius)
- [ ] Keying + blend modes (`chromakey`/`blend`)
- [ ] Optical distortion (lens/barrel, chromatic aberration)
- [ ] Procedural generators (perlin/cellular/gradient/noise — introduces generator/source-clip concept)
- [ ] Keyframed opacity/scale (slow zoom/crossfade)

### Wave T — Testing (cross-cutting, first-class)
Runs through every wave. See [07-test-strategy.md](07-test-strategy.md).
- [ ] Unit + property tests (Rust proptest, Python) for every new builder/compiler
- [ ] Contract tests against real FFmpeg for every generated filter/command
- [ ] **QC-assertion test layer** mapping use-case outcomes (OC-*) to automated checks
- [ ] **Chatbot-driven testing** scenarios for each new capability and use case
- [ ] **Browser UAT** journeys (headless Tier 1 on every version closure; headed Tier 2 for sign-off) extended with the new GUI surfaces
- [ ] **Regression suite** kept green: no capability merges without its tests and a traceability entry

---

## Out of scope (deferred to Release 3+)

These sit outside snf's non-realtime render paradigm or require large new subsystems/GUI work. Named here so the boundary is explicit, not forgotten:

- **Recording / capture, multi-take, punch-in/out, take comping** — realtime capture belongs upstream (a DAW). snf ingests a finished voice track.
- **Bus / submix / nested-sequence mixing model** — render-graph generalisation.
- **Vector bezier masking & feathering** — needs a mask-authoring layer + GUI.
- **Ambisonic / HRTF surround delivery** — specialised spatial encode/decode.
- **Motion-graphics templates (MOGRT)** — template system.
- **Live A/B monitoring / reference-track compare** — interactive monitoring, preview-domain.

---

## Version mapping (suggested)

| Version | Wave(s) | Focus |
|---------|---------|-------|
| v073 | 0 + T | Keyframe compiler, markers/regions, test scaffolding |
| v074 | 1 + T | QC/compliance pass, delivery profiles, QC-as-test layer |
| v075 | 2 + T | Mastering chain + automation curves |
| v076 | 3 + T | Immersive sound design + tone synthesis |
| v077 | 4 + T | Reverse, split/razor, range-gating, time-remap |
| v078 | 5 + T | Video FX + keyframed visuals |

Each version closes only when its capabilities, their tests (unit/contract/chatbot/UAT), and their traceability entries are complete and the regression suite is green.

---

## Success gates

| Gate | Criterion |
|------|-----------|
| Functional | Both use cases (UC-AV-001, UC-MEDIA-MPS-001) producible end-to-end via API |
| Verifiable | ≥14 of the 17 mental-performance outcomes (OC-1…17) auto-verified by the QC pass |
| Quality | Rust >90% / Python >80% coverage maintained; every new effect has contract tests against real FFmpeg |
| Testing-first | Every capability ships with chatbot-driven scenario(s) and (where GUI-facing) a UAT journey, in the same version |
| Regression | Full suite green at every version closure; Tier 1 UAT passes headless |
| Delivery | A delivery profile produces a loudness-compliant master that passes the QC pass and plays end-to-end on a standard player |
