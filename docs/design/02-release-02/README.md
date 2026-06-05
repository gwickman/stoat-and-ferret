# Release 2 — Sound Design, Mastering & Verified Delivery

**Status:** Initial design. Open for refinement.
**Builds on:** [Release 1](../01-release-01/README.md) (closed, ~v001–v072).
**Target versions:** v073 onward.

## What Release 2 is

Release 1 made stoat-and-ferret able to *apply effects and render video*. Release 2 makes it able to **produce and prove a finished, broadcast-quality master** — primarily by expanding the audio/sound-design/mastering surface, adding an automation (keyframing) layer, and introducing an automated **quality-control / compliance verification** capability so that every deliverable can be machine-checked against its acceptance criteria.

Two things define this release:

1. **Capability expansion** driven by two concrete production use cases (a guided audio-visual mental-performance session). These exercise multitrack mastering, immersive/spatial sound design, entrainment-tone synthesis, automation curves, loudness-compliant delivery, and an optional synchronized visual track.
2. **Testing as a first-class citizen.** The full regression suite, **chatbot-driven testing**, and **browser-running UAT** are not a closing phase — they are built alongside every capability. Every requirement traces to a use case, a verifiable outcome (acceptance criterion), and an automated test (unit / chatbot / UAT). Most acceptance criteria are designed to be *machine-verifiable* via the new QC pass.

## Design philosophy carried forward

- **Hybrid Python/Rust:** new compute-bound logic (keyframe→expression compilation, filter-graph generation, QC measurement parsing) lands in Rust pure functions exposed via PyO3; Python orchestrates, validates, and serves.
- **Effect-registry pattern:** new effects are builders + JSON-schema-validated registry entries with AI hints, consistent with Release 1.
- **Outcome-first requirements:** acceptance criteria are written as tool-independent, verifiable end results (see the use cases), so they double as test assertions.

## Document inventory

Read in this order:

| # | File | Description |
|---|------|-------------|
| — | [README.md](README.md) | This overview |
| 1 | [01-roadmap.md](01-roadmap.md) | Scope, capability waves, dependency spine, in/out of scope, version mapping, success gates |
| 2 | [02-architecture.md](02-architecture.md) | New subsystems (keyframe→expression compiler, QC/verification pass, delivery profiles, markers/section model) and how they slot into the Release 1 architecture |
| 3 | [03-capabilities-and-requirements.md](03-capabilities-and-requirements.md) | The consolidated requirements register with status and FFmpeg mechanism for every capability |
| 4 | [04-use-cases.md](04-use-cases.md) | The production use cases (UC-AV-001, UC-MEDIA-MPS-001) plus capability use cases, each with testable acceptance criteria and verification method |
| 5 | [05-api-specification.md](05-api-specification.md) | New and changed REST endpoints and WebSocket events |
| 6 | [06-gui-integration.md](06-gui-integration.md) | GUI surfaces: automation lanes, QC results panel, delivery profiles, markers/regions |
| 7 | [07-test-strategy.md](07-test-strategy.md) | **First-class testing:** regression suite, chatbot-driven testing, browser UAT, QC-as-test, OC→assertion mapping, CI tiers |
| 8 | [08-backlog-items.md](08-backlog-items.md) | Concrete backlog items with sizing, acceptance criteria, theme grouping, version mapping |
| 9 | [09-traceability-matrix.md](09-traceability-matrix.md) | Capability → use case → outcome (OC) → test traceability |

## Capability waves (summary)

| Wave | Theme | Headline |
|------|-------|----------|
| 0 | Enablers | Keyframe→expression compiler; timeline markers/regions |
| 1 | Verify & deliver | QC/compliance pass; delivery profiles |
| 2 | Mastering | Parametric EQ, multiband compression, limiter, LUFS normalization, automation curves |
| 3 | Sound design | Stereo/binaural pan, auto-pan, convolution reverb, tone synthesis, loopable beds, sub layer |
| 4 | Editing & time | Reverse, clip split/razor, range-bound effect gating, variable-speed/time-remap, frame-rate interpolation |
| 5 | Video FX | Color grading/LUT, blur/sharpen, keying + blend modes, optical distortion, procedural generators, keyframed opacity/scale |

Testing (Wave T) runs across **all** waves — see [07-test-strategy.md](07-test-strategy.md).
