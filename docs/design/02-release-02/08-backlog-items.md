# Release 2 — Backlog Items

## Sizing rules

Consistent with Release 1: Documentation-only = Small; single focused code change = Small; new feature with tests = Medium; complex cross-cutting feature = Large.

**Testing-first rule:** every functional item's acceptance criteria include its tests (unit/contract/QC/chatbot/UAT). Items are not "done" without them (see [07-test-strategy.md](07-test-strategy.md) Definition of Done).

---

## Theme 0 — Enablers (v073)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|---------------------|
| 1 | Keyframe→expression compiler (Rust + PyO3) | L | `compile_automation(Automation) -> String` with hold/linear/exponential/ease-in-out curves; PyO3 binding; shared `Automation`/`Keyframe` schema. | Compiles nested `if(between(t,…))` expr; value at each keyframe equals kf value; proptest (no panic, monotonic time, bounded); PyO3 callable; contract test renders a clip and QC measures the curve |
| 2 | Markers / regions model + API + persistence | M | Ordered, named, typed regions on project; CRUD endpoints; persisted+versioned; non-overlap validation for `section`. | CRUD works; section regions non-overlapping+ordered; persists with project; unit tests; chatbot scenario creates the 4 session regions |
| 3 | Automation envelope param plumbing | M | Allow effect params to accept `{automation:{…}}` in place of scalars; wire through registry/validation; surface compiled expr in `filter_preview`. | Volume accepts envelope; `filter_preview` shows compiled expr; schema validation; unit tests |
| 4 | Test scaffolding for Release 2 | M | Golden render/QC fixtures from sample project; QC-assertion test helper; chatbot scenario runner hooks; new UAT journey skeleton. | Golden fixtures produce stable QC reports; helper asserts on QC report; UAT skeleton runs headless in CI |

## Theme 1 — Verify & deliver (v074)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|---------------------|
| 5 | QC measurement parsers (Rust + PyO3) | M | Typed parsers for `ebur128`/`loudnorm` JSON, `astats`/`volumedetect`, `silencedetect`, `aspectralstats`, `blackdetect`/`freezedetect` output. | Parses real + garbled output without panic (proptest); typed measurements; PyO3 callable |
| 6 | QCService + `/qc` endpoints | L | Orchestrates analysis passes, compares to targets/profile, emits `QCReport`; `POST /qc/run`, report GET, `render/{job}/qc`; `qc.*` WS events. | All 11 checks run; report matches schema; targets from profile or explicit assertions; WS events emitted; contract tests on fixtures |
| 7 | Delivery profiles (model + API + export gate) | L | `DeliveryProfile` CRUD; render accepts `delivery_profile`+`run_qc`; produces all outputs; QC gate fails deliverable on assertion failure. | Profile CRUD; export produces every output; QC gate enforces targets; failure retains editable state; chatbot UC-CAP-MASTER passes incl. A3/A5 |
| 8 | Chapter/metadata embedding from markers | S | Export embeds section labels + identifying metadata via `ffmetadata`. | `ffprobe` shows chapters == section count + metadata; QC `chapters_present` asserts |
| 9 | QC-as-test layer + OC mapping | M | Map OC-* to QC check ids; assertion helpers; wire into PR-full CI tier. | OC→check table covered by tests; CI runs QC assertions on golden fixtures |

## Theme 2 — Mastering (v075)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|---------------------|
| 10 | Parametric EQ effect (+ automation) | M | `parametric_eq` via `anequalizer`; multi-band structured param; band gain accepts automation. | Multi-band EQ renders; automation on band gain; contract test; unit |
| 11 | Volume/level automation curves | S | `volume` with automation envelope (uses #1/#3). | Envelope compiles; QC measures intended curve; UAT J-Automation |
| 12 | Multiband compression effect | M | `multiband_compressor` via `mcompand`. | Renders; contract test; params schema-valid |
| 13 | Mastering limiter effect | S | `limiter` via `alimiter`. | True-peak limited (QC verifies ceiling); contract test |
| 14 | LUFS normalization (two-pass) | M | `loudness_normalize` via two-pass `loudnorm`; integrate with delivery profile target. | Output within ±0.5 LU of target; true-peak ≤ ceiling (QC); contract test |

## Theme 3 — Immersive sound design (v076)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|---------------------|
| 15 | Pan + automated pan | M | `pan`/`auto_pan`; automation envelope for position. | Spatial field (QC phase correlation); gradual movement; UAT |
| 16 | Convolution reverb + IR pack | M | `convolution_reverb` via `afir`; ship small IR asset set. | Renders with IR; contract test; schema selects IR |
| 17 | Tone synthesis (isochronic/binaural beats) | M | `tone_generator` source clip; frequency automation; binaural L/R offset. | Energy at target freq (QC); sweep reflected over time; binaural offset correct; UAT UC-CAP-TONE |
| 18 | Loopable beds with seamless loop points | M | `aloop` + boundary crossfade; loop-point authoring. | Loop seam below threshold (QC `loop_seam`); chatbot A2 path |
| 19 | Sub-bass layer + formalised sidechain ducking | S | `sub_layer`; `sidechain_duck` registry effect. | Ducking measurable (QC `ducking`); sub layer renders |
| 20 | Generator/source-clip concept | M | Support clips with no source file (tone/noise/gradient generators). | Generator clips place on timeline; render; unit tests |

## Theme 4 — Editing & time (v077)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|---------------------|
| 21 | Reverse clip effect | S | `reverse`+`areverse`; enforce buffer-length limit with structured error. | Frames/audio reversed (unit/QC); over-limit rejected; UAT J-Reverse-Split |
| 22 | Clip split / razor op | M | `POST .../split` produces two adjacent clips; total coverage preserved. | Split correctness (unit); preview reflects; chatbot UC-CAP-SPLIT |
| 23 | Range-bound effect gating | S | Optional `window` on any effect → `enable='between(t,a,b)'`. | Effect active only in window (QC probe); preview shows enable clause |
| 24 | Variable-speed / time-remap | L | Segmented speed curve (or PTS-integral); audio pitch-preserved. | Output duration ≈ integral (QC); constant-speed regression intact; UAT |
| 25 | Frame-rate conversion | M | `framerate_convert` via `minterpolate`/`framerate`. | Output fps correct; interpolation modes; contract test |

## Theme 5 — Video FX (v078)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|---------------------|
| 26 | Color grading / LUT | M | `color_lut` via `lut3d`/`haldclut`; LUT picker. | Pixels transformed per LUT (unit); consistency (QC); UAT J-Grade |
| 27 | Blur / sharpen (keyframable) | M | `blur` (gaussian/directional), `sharpen`; radius accepts automation. | Renders; keyframable radius; contract test |
| 28 | Keying + blend modes | M | `chroma_key`/`color_key`; `blend` (~30 modes) into layer system. | Key + blend render; integrates z-index layers; contract test |
| 29 | Optical distortion | S | `lens_distortion`, `chromatic_aberration`. | Renders; contract test; schema-valid |
| 30 | Procedural generators | S | `noise_generator`, `gradient_generator` (uses #20). | Generator clips render; unit tests |
| 31 | Keyframed opacity / scale | S | Opacity/scale via overlay/scale + automation. | Smooth zoom/crossfade; QC offset/timing; UAT |

## Theme T — Testing (woven through every version)

| # | Title | Size | Description | Acceptance Criteria |
|---|-------|------|-------------|---------------------|
| 32 | Chatbot scenarios for each use case | M | UC-MEDIA-MPS-001 + all UC-CAP-* scenarios in the chatbot catalog. | Scenarios run in CI (mocked LLM) + nightly (live); assert QC reports |
| 33 | UAT journeys J-Automation…J-Grade | M | Six new headless Tier-1 journeys (see 07). | All run on version closure; screenshot evidence; flag failures for Tier 2 |
| 34 | Golden render/QC regression | M | Golden masters + known QC reports; drift detection. | Regression fails on filter/QC drift; thresholds held |
| 35 | UC-MEDIA-MPS-001 full acceptance harness | M | End-to-end acceptance producing the session and asserting OC-1…17 (14 auto + Tier-2 for the rest). | ≥14 OCs auto-pass; Tier-2 checklist for OC-3/4/5/14 |

---

## Version mapping summary

| Version | Theme(s) | Items |
|---------|----------|-------|
| v073 | 0 + T | 1–4, (32–33 scaffolding) |
| v074 | 1 + T | 5–9, 34 |
| v075 | 2 + T | 10–14 |
| v076 | 3 + T | 15–20 |
| v077 | 4 + T | 21–25 |
| v078 | 5 + T | 26–31, 35 (full acceptance) |

Totals: **35 items** (~6 S-heavy themes). Estimated split ~10 Small / ~17 Medium / ~8 Large. Each version closes only with its tests, chatbot scenarios, UAT journeys, and traceability rows complete and the regression suite green.
